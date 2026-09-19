"""Explicit DMX Power Manager, isolated from receive-only monitoring.

Power Manager is the only Show Network subsystem allowed to transmit DMX. It is
opt-in, protected by the secondary security gate, and never starts an output
until a user explicitly runs a configured button. DMX Monitor itself remains
receive-only.
"""
from __future__ import annotations

import asyncio
import json
import socket
import struct
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

ENABLED = True


class PowerOutput(StrEnum):
    SACN = "sacn"
    ARTNET = "artnet"
    ENTTEC = "enttec"


@dataclass(frozen=True, slots=True)
class PowerOutputConfig:
    output: PowerOutput
    universe: int = 1
    host: str = ""  # sACN: blank = standard multicast; Art-Net: required destination
    port: int | None = None
    enttec_device: str = ""
    priority: int = 100
    source_name: str = "Show Network Power Manager"

    def __post_init__(self) -> None:
        if not 1 <= int(self.universe) <= 63999:
            raise ValueError("universe must be 1..63999")
        if not 1 <= int(self.priority) <= 200:
            raise ValueError("sACN priority must be 1..200")
        if self.port is not None and not 1 <= int(self.port) <= 65535:
            raise ValueError("port must be 1..65535")
        if self.output is PowerOutput.ARTNET and not self.host.strip():
            raise ValueError("host is required for Art-Net output")
        if self.output is PowerOutput.ENTTEC and not self.enttec_device.strip():
            raise ValueError("enttec_device is required for ENTTEC output")


@dataclass(frozen=True, slots=True)
class PowerChannel:
    channel: int
    name: str = ""
    on_value: int = 255
    off_value: int = 0
    on_delay_s: float = 0.0
    off_delay_s: float = 0.0

    def __post_init__(self) -> None:
        if not 1 <= int(self.channel) <= 512:
            raise ValueError("DMX channel must be 1..512")
        if not 0 <= int(self.on_value) <= 255 or not 0 <= int(self.off_value) <= 255:
            raise ValueError("DMX values must be 0..255")
        if float(self.on_delay_s) < 0 or float(self.off_delay_s) < 0:
            raise ValueError("delays cannot be negative")


@dataclass(frozen=True, slots=True)
class PowerSequence:
    universe: int
    channels: tuple[PowerChannel, ...] = field(default_factory=tuple)
    output: PowerOutputConfig | None = None
    enabled: bool = False

    def __post_init__(self) -> None:
        if not 1 <= int(self.universe) <= 63999:
            raise ValueError("universe must be 1..63999")
        if len({c.channel for c in self.channels}) != len(self.channels):
            raise ValueError("duplicate DMX channel")
        if self.output is not None and self.output.universe != self.universe:
            raise ValueError("output universe must match sequence universe")

    @property
    def active(self) -> bool:
        return ENABLED and self.enabled


@dataclass(slots=True)
class PowerButton:
    button_id: str
    name: str
    icon: str = "mdi:power"
    output: PowerOutputConfig = field(default_factory=lambda: PowerOutputConfig(PowerOutput.SACN, 1))
    channels: list[PowerChannel] = field(default_factory=list)
    enabled: bool = True
    confirm: bool = True
    state: str = "off"
    last_error: str | None = None
    last_run: float | None = None

    def public(self) -> dict[str, Any]:
        return {
            "button_id": self.button_id, "name": self.name, "icon": self.icon,
            "output": {**asdict(self.output), "output": self.output.output.value},
            "channels": [asdict(c) for c in self.channels], "enabled": self.enabled,
            "confirm": self.confirm, "state": self.state, "last_error": self.last_error,
            "last_run": self.last_run,
            "state_evidence": "commanded_dmx_output_not_physical_feedback",
        }


def available_outputs() -> tuple[PowerOutput, ...]:
    return tuple(PowerOutput)


def _sacn_group(universe: int) -> str:
    return f"239.255.{(int(universe) >> 8) & 0xff}.{int(universe) & 0xff}"


def build_sacn_frame(universe: int, values: bytes, *, sequence: int = 0,
                     priority: int = 100, source_name: str = "Show Network Power Manager",
                     cid: bytes | None = None) -> bytes:
    """Build one standards-shaped E1.31 data packet for 512 slots."""
    values = bytes(values[:512]).ljust(512, b"\0")
    cid = (cid or uuid.uuid4().bytes)[:16].ljust(16, b"\0")
    source = source_name.encode("utf-8", "replace")[:63].ljust(64, b"\0")
    prop_count = len(values) + 1
    dmp = bytearray()
    dmp += struct.pack(">H", 0x7000 | (10 + prop_count))
    dmp += b"\x02\xa1\x00\x00\x00\x01" + struct.pack(">H", prop_count) + b"\x00" + values
    framing = bytearray()
    framing += struct.pack(">H", 0x7000 | (77 + len(dmp)))
    framing += struct.pack(">I", 0x00000002) + source + bytes([priority & 0xff])
    framing += b"\x00\x00" + bytes([sequence & 0xff, 0]) + struct.pack(">H", int(universe)) + dmp
    root = bytearray()
    root += b"\x00\x10\x00\x00ASC-E1.17\x00\x00\x00"
    root += struct.pack(">H", 0x7000 | (22 + len(framing)))
    root += struct.pack(">I", 0x00000004) + cid + framing
    return bytes(root)


def build_artnet_frame(universe: int, values: bytes, *, sequence: int = 0) -> bytes:
    values = bytes(values[:512]).ljust(512, b"\0")
    # ArtDmx: ID, OpCode little-endian, ProtVer big-endian, sequence, physical,
    # 15-bit Port-Address little-endian, length big-endian.
    return (b"Art-Net\x00" + struct.pack("<H", 0x5000) + struct.pack(">H", 14) +
            bytes([sequence & 0xff, 0]) + struct.pack("<H", int(universe) & 0x7fff) +
            struct.pack(">H", len(values)) + values)


def build_enttec_frame(values: bytes) -> bytes:
    payload = b"\x00" + bytes(values[:512]).ljust(512, b"\0")
    n = len(payload)
    return bytes((0x7E, 6, n & 0xff, (n >> 8) & 0xff)) + payload + bytes((0xE7,))


class PowerOutputPipeline:
    """Bounded latest-value output buffer; retained for compatibility/tests."""
    def __init__(self, sender, interval_s: float = 0.05) -> None:
        self.sender = sender; self.interval_s = max(0.02, float(interval_s))
        self._latest: bytes | None = None; self._task = None; self._stopping = False
        self.received = 0; self.coalesced = 0; self.sent = 0; self.errors = 0

    def push_nowait(self, frame: bytes) -> None:
        if self._stopping: return
        frame = bytes(frame[:512]).ljust(512, b"\0"); self.received += 1
        if self._latest is not None: self.coalesced += 1
        self._latest = frame
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._worker(), name="show-network-power-output")

    async def _worker(self) -> None:
        while self._latest is not None and not self._stopping:
            frame = self._latest; self._latest = None; result = None
            try:
                result = self.sender(frame)
                if asyncio.iscoroutine(result): await result
                self.sent += 1
            except asyncio.CancelledError:
                if asyncio.iscoroutine(result): result.close()
                raise
            except Exception: self.errors += 1
            if self._latest is not None and not self._stopping: await asyncio.sleep(self.interval_s)

    async def async_stop(self) -> None:
        self._stopping = True; self._latest = None; task = self._task; self._task = None
        if task and not task.done(): task.cancel(); await asyncio.gather(task, return_exceptions=True)

    def snapshot(self) -> dict[str, int]:
        return {"received": self.received, "coalesced": self.coalesced, "sent": self.sent, "errors": self.errors}


class PowerManager:
    """Persistent multi-button sequencer with an explicit active-output boundary."""
    def __init__(self, storage_path: str | Path, *, repeat_hz: float = 10.0) -> None:
        self.path = Path(storage_path)
        self.buttons: dict[str, PowerButton] = {}
        self.repeat_interval = 1.0 / max(1.0, min(float(repeat_hz), 40.0))
        self._frames: dict[str, bytearray] = {}
        self._configs: dict[str, PowerOutputConfig] = {}
        self._sequences: dict[str, int] = {}
        self._cid = uuid.uuid4().bytes
        self._repeat_task: asyncio.Task | None = None
        self._run_tasks: dict[str, asyncio.Task] = {}
        self._serials: dict[str, Any] = {}
        self.sent = 0; self.errors = 0; self.last_error: str | None = None
        # NOTE (audit fix): self.load() used to run here, meaning every
        # coordinator construction did blocking synchronous file I/O
        # directly on Home Assistant's event loop -- confirmed in
        # production logs. Deferred to runtime/setup.py's
        # hass.async_add_executor_job(coordinator.power_manager.load) call,
        # matching the pattern already correctly used for
        # fixture_control/dmx_scene_bank.

    @staticmethod
    def _output_key(cfg: PowerOutputConfig) -> str:
        return f"{cfg.output.value}|{cfg.universe}|{cfg.host}|{cfg.port or ''}|{cfg.enttec_device}"

    def load(self) -> None:
        try: raw = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []
        except (OSError, ValueError, TypeError): raw = []
        for item in raw if isinstance(raw, list) else []:
            try: self.upsert_from_dict(item, persist=False)
            except (ValueError, TypeError, KeyError): continue

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([b.public() for b in self.buttons.values()], indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def upsert_from_dict(self, data: dict[str, Any], *, persist: bool = True) -> PowerButton:
        bid = str(data.get("button_id") or f"power_{uuid.uuid4().hex[:10]}")
        name = str(data.get("name") or "Power").strip()
        if not name: raise ValueError("button name is required")
        out = data.get("output") or {}
        cfg = PowerOutputConfig(
            output=PowerOutput(str(out.get("output", "sacn")).lower()), universe=int(out.get("universe", 1)),
            host=str(out.get("host", "") or ""), port=(int(out["port"]) if out.get("port") not in (None, "") else None),
            enttec_device=str(out.get("enttec_device", "") or ""), priority=int(out.get("priority", 100)),
            source_name=str(out.get("source_name", "Show Network Power Manager")),
        )
        channels = [PowerChannel(
            channel=int(c["channel"]), name=str(c.get("name", "")), on_value=int(c.get("on_value", 255)),
            off_value=int(c.get("off_value", 0)), on_delay_s=float(c.get("on_delay_s", 0)),
            off_delay_s=float(c.get("off_delay_s", 0)),
        ) for c in (data.get("channels") or [])]
        if len({c.channel for c in channels}) != len(channels): raise ValueError("duplicate DMX channel")
        existing = self.buttons.get(bid)
        button = PowerButton(bid, name, str(data.get("icon") or "mdi:power"), cfg, channels,
                             bool(data.get("enabled", True)), bool(data.get("confirm", True)),
                             existing.state if existing else "off", existing.last_error if existing else None,
                             existing.last_run if existing else None)
        self.buttons[bid] = button
        key = self._output_key(cfg); self._configs[key] = cfg; self._frames.setdefault(key, bytearray(512))
        if persist: self.save()
        return button

    def remove(self, button_id: str) -> None:
        task = self._run_tasks.pop(button_id, None)
        if task and not task.done(): task.cancel()
        self.buttons.pop(button_id, None); self.save()

    async def start(self) -> None:
        if self._repeat_task is None or self._repeat_task.done():
            self._repeat_task = asyncio.create_task(self._repeat_worker(), name="show-network-power-maintain")

    async def cancel_transitions(self, reason: str = "sequence cancelled") -> None:
        """Cancel active transitions but keep the last transmitted frame alive.

        This deliberately does not zero DMX. A security timeout must prevent
        future steps, not cause an automatic power cut.
        """
        tasks = [t for t in self._run_tasks.values() if not t.done()]
        for button_id, task in list(self._run_tasks.items()):
            if not task.done():
                button = self.buttons.get(button_id)
                if button:
                    button.last_error = reason
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self) -> None:
        tasks = list(self._run_tasks.values()); self._run_tasks.clear()
        for t in tasks:
            if not t.done(): t.cancel()
        if tasks: await asyncio.gather(*tasks, return_exceptions=True)
        if self._repeat_task:
            self._repeat_task.cancel(); await asyncio.gather(self._repeat_task, return_exceptions=True); self._repeat_task = None
        serials=list(self._serials.values());self._serials.clear()
        for ser in serials:
            try: await asyncio.to_thread(ser.close)
            except Exception: pass

    async def run(self, button_id: str, turn_on: bool, *, guard=None) -> None:
        button = self.buttons.get(button_id)
        if not button: raise ValueError(f"Unknown Power Manager button: {button_id}")
        if not button.enabled: raise ValueError("Power Manager button is disabled")
        old = self._run_tasks.get(button_id)
        if old and not old.done(): old.cancel(); await asyncio.gather(old, return_exceptions=True)
        task = asyncio.create_task(self._run_sequence(button, bool(turn_on), guard=guard), name=f"show-network-power-{button_id}")
        self._run_tasks[button_id] = task
        await task

    async def _run_sequence(self, button: PowerButton, turn_on: bool, *, guard=None) -> None:
        button.state = "turning_on" if turn_on else "turning_off"; button.last_error = None
        key = self._output_key(button.output); frame = self._frames.setdefault(key, bytearray(512)); self._configs[key] = button.output
        channels = list(button.channels)
        # OFF intentionally uses the reverse order by default: useful for staged
        # room power-down while still allowing per-channel off_delay_s.
        if not turn_on: channels.reverse()
        try:
            for ch in channels:
                # Security is re-checked before and after every wait. Expiry or an
                # explicit lock therefore cannot let a queued sequence continue.
                if guard is not None:
                    guard()
                delay = ch.on_delay_s if turn_on else ch.off_delay_s
                if delay:
                    await asyncio.sleep(delay)
                if guard is not None:
                    guard()
                frame[ch.channel - 1] = ch.on_value if turn_on else ch.off_value
                await self._send(button.output, bytes(frame))
            button.state = "on" if turn_on else "off"; button.last_run = time.time()
        except PermissionError as err:
            button.state = "interrupted"
            button.last_error = str(err)
            button.last_run = time.time()
            self.last_error = button.last_error
            raise
        except asyncio.CancelledError:
            button.state = "interrupted"
            button.last_error = button.last_error or "sequence cancelled"
            button.last_run = time.time()
            raise
        except Exception as err:
            button.state = "error"; button.last_error = f"{type(err).__name__}: {err}"; self.last_error = button.last_error; self.errors += 1
            raise

    async def _repeat_worker(self) -> None:
        while True:
            await asyncio.sleep(self.repeat_interval)
            for key, frame in list(self._frames.items()):
                cfg = self._configs.get(key)
                if cfg is None: continue
                # Maintain only outputs used by a button that is ON/transitioning.
                active = any(self._output_key(b.output) == key and b.state in {"on", "turning_on", "turning_off", "interrupted"} for b in self.buttons.values())
                if active:
                    try: await self._send(cfg, bytes(frame))
                    except Exception as err:
                        self.errors += 1; self.last_error = f"{type(err).__name__}: {err}"

    async def _send(self, cfg: PowerOutputConfig, values: bytes) -> None:
        key = self._output_key(cfg); seq = (self._sequences.get(key, 0) + 1) & 0xff; self._sequences[key] = seq
        if cfg.output is PowerOutput.SACN:
            packet = build_sacn_frame(cfg.universe, values, sequence=seq, priority=cfg.priority, source_name=cfg.source_name, cid=self._cid)
            target = cfg.host.strip() or _sacn_group(cfg.universe); port = cfg.port or 5568
            await asyncio.to_thread(self._udp_send, packet, target, port)
        elif cfg.output is PowerOutput.ARTNET:
            packet = build_artnet_frame(cfg.universe, values, sequence=seq)
            await asyncio.to_thread(self._udp_send, packet, cfg.host.strip(), cfg.port or 6454, True)
        else:
            await self._enttec_send(cfg.enttec_device, build_enttec_frame(values))
        self.sent += 1

    @staticmethod
    def _udp_send(packet: bytes, host: str, port: int, broadcast: bool = False) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            if broadcast: sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (host, int(port)))

    async def _enttec_send(self, device: str, packet: bytes) -> None:
        try: import serial
        except ImportError as err: raise RuntimeError("pyserial is required for ENTTEC output") from err
        ser=self._serials.get(device)
        if ser is None or not getattr(ser,"is_open",False):
            ser=await asyncio.to_thread(serial.Serial,device,57600,timeout=0.2)
            self._serials[device]=ser
        await asyncio.to_thread(ser.write,packet)
        await asyncio.to_thread(ser.flush)

    def snapshot(self) -> dict[str, Any]:
        return {
            "power_manager_enabled": ENABLED,
            "power_manager_buttons": [b.public() for b in self.buttons.values()],
            "power_manager_button_count": len(self.buttons),
            "power_manager_active": sum(1 for b in self.buttons.values() if b.state in {"on", "turning_on", "turning_off", "interrupted"}),
            "power_manager_sent": self.sent, "power_manager_errors": self.errors,
            "power_manager_last_error": self.last_error,
            "power_manager_outputs": [x.value for x in PowerOutput],
            "power_manager_note": "Active DMX output; explicit user action and Show Network security unlock required",
        }

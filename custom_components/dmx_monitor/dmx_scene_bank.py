"""Persistent single-universe DMX scene bank for Home Assistant.

The bank intentionally owns exactly one output universe/transport at a time.
Up to 19 full 512-channel scenes can be stored. Recalling a scene selects one
frame which is then repeated while the bank safety gate is armed.
"""
from __future__ import annotations
import logging

import asyncio
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import socket
import time
import uuid
from typing import Any

from .power_manager import build_artnet_frame, build_enttec_frame, build_sacn_frame, _sacn_group

MAX_SCENES = 19


@dataclass
class DmxScene:
    scene_id: str
    name: str
    values: list[int]
    updated_at: float

    def public(self) -> dict[str, Any]:
        return {"scene_id": self.scene_id, "name": self.name, "updated_at": self.updated_at,
                "active_channels": sum(1 for value in self.values if value)}


@dataclass
class DmxSceneOutput:
    protocol: str = "sacn"
    universe: int = 1
    host: str = ""
    port: int | None = None
    priority: int = 100
    enttec_device: str = ""
    external_hold_s: float = 1.5

    def validate(self) -> None:
        self.protocol = str(self.protocol).lower().strip()
        if self.protocol not in {"sacn", "artnet", "enttec"}:
            raise ValueError("protocol must be sacn, artnet or enttec")
        if not 1 <= int(self.universe) <= 63999:
            raise ValueError("universe out of range")
        if not 1 <= int(self.priority) <= 200:
            raise ValueError("sACN priority out of range")
        if self.protocol == "artnet" and not str(self.host).strip():
            raise ValueError("Art-Net output requires an explicit destination host")
        if self.protocol == "enttec" and not str(self.enttec_device).strip():
            raise ValueError("ENTTEC output requires enttec_device")
        if self.port is not None and not 1 <= int(self.port) <= 65535:
            raise ValueError("port out of range")
        if not 0.25 <= float(self.external_hold_s) <= 10.0:
            raise ValueError("external_hold_s must be between 0.25 and 10 seconds")


class DmxSceneBank:
    def __init__(self, path: str | Path, *, repeat_hz: float = 10.0) -> None:
        self.path = Path(path)
        self.scenes: dict[str, DmxScene] = {}
        self.output = DmxSceneOutput()
        self.enabled = False  # Never persisted as armed.
        self.active_scene_id: str | None = None
        self.current_frame = bytes(512)
        self.repeat_interval = 1.0 / max(1.0, min(float(repeat_hz), 40.0))
        self._task: asyncio.Task | None = None
        self._cid = uuid.uuid4().bytes
        self._sequence = 0
        self._serials: dict[str, Any] = {}
        self.sent = 0
        self.errors = 0
        self.last_error: str | None = None
        self.last_send: float | None = None
        self._local_sources: set[str] = {"127.0.0.1", "::1"}
        self.external_active_until: float = 0.0
        self.external_source: str | None = None
        self.external_protocol: str | None = None
        self.external_last_seen: float | None = None

    @staticmethod
    def _normalize_values(values: Any) -> list[int]:
        if isinstance(values, (bytes, bytearray)):
            vals = list(values)
        elif isinstance(values, list):
            vals = values
        else:
            raise ValueError("values must be a list or bytes")
        if len(vals) > 512:
            raise ValueError("DMX scene cannot exceed 512 channels")
        out: list[int] = []
        for value in vals:
            iv = int(value)
            if not 0 <= iv <= 255:
                raise ValueError("DMX values must be 0..255")
            out.append(iv)
        out.extend([0] * (512 - len(out)))
        return out

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        except (OSError, ValueError, TypeError):
            raw = {}
        self.scenes.clear()
        if isinstance(raw, dict):
            output = raw.get("output") or {}
            if isinstance(output, dict):
                try:
                    cfg = DmxSceneOutput(**{k: output[k] for k in DmxSceneOutput.__dataclass_fields__ if k in output})
                    cfg.validate()
                    self.output = cfg
                except Exception:
                    self.output = DmxSceneOutput()
            rows = raw.get("scenes") or []
            if isinstance(rows, list):
                for item in rows[:MAX_SCENES]:
                    try:
                        scene = DmxScene(
                            scene_id=str(item["scene_id"]).strip(),
                            name=str(item.get("name") or item["scene_id"]),
                            values=self._normalize_values(item.get("values") or []),
                            updated_at=float(item.get("updated_at") or 0.0),
                        )
                        if scene.scene_id:
                            self.scenes[scene.scene_id] = scene
                    except Exception:
                        continue
        self.enabled = False
        self.active_scene_id = None
        self.current_frame = bytes(512)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "output": asdict(self.output),
            "scenes": [asdict(scene) for scene in self.scenes.values()],
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def configure_output(self, data: dict[str, Any]) -> None:
        cfg = DmxSceneOutput(
            protocol=str(data.get("protocol", self.output.protocol)),
            universe=int(data.get("universe", self.output.universe)),
            host=str(data.get("host", self.output.host) or ""),
            port=(int(data["port"]) if data.get("port") not in (None, "") else None),
            priority=int(data.get("priority", self.output.priority)),
            enttec_device=str(data.get("enttec_device", self.output.enttec_device) or ""),
            external_hold_s=float(data.get("external_hold_s", self.output.external_hold_s)),
        )
        cfg.validate()
        self.output = cfg
        self.save()

    def upsert_scene(self, scene_id: str, name: str, values: Any) -> DmxScene:
        scene_id = str(scene_id).strip()
        if not scene_id:
            raise ValueError("scene_id is required")
        if scene_id not in self.scenes and len(self.scenes) >= MAX_SCENES:
            raise ValueError(f"A maximum of {MAX_SCENES} DMX scenes is allowed")
        scene = DmxScene(scene_id, str(name or scene_id), self._normalize_values(values), time.time())
        self.scenes[scene_id] = scene
        self.save()
        return scene

    def delete_scene(self, scene_id: str) -> None:
        sid = str(scene_id)
        self.scenes.pop(sid, None)
        if self.active_scene_id == sid:
            self.active_scene_id = None
            self.current_frame = bytes(512)
        self.save()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if not self.enabled:
            self.active_scene_id = None

    def set_local_sources(self, sources: list[str] | set[str] | tuple[str, ...]) -> None:
        """Declare addresses owned by Home Assistant so looped-back TX is ignored."""
        self._local_sources = {"127.0.0.1", "::1"}
        self._local_sources.update(str(x).strip() for x in sources if str(x).strip())

    def observe_input(self, protocol: str, universe: int, source: str | None) -> bool:
        """Suspend this output while an external source owns the selected universe.

        This is intentionally a *temporary inhibit*, not a disable: the selected
        HA scene stays active and resumes automatically once the incoming signal
        has been absent for external_hold_s.
        """
        if int(universe) != int(self.output.universe):
            return False
        src = str(source or "").strip()
        if src and src in self._local_sources:
            return False
        now = time.monotonic()
        self.external_active_until = max(self.external_active_until, now + float(self.output.external_hold_s))
        self.external_source = src or "unknown"
        self.external_protocol = str(protocol or "unknown").upper()
        self.external_last_seen = time.time()
        return True

    def external_active(self) -> bool:
        return time.monotonic() < self.external_active_until

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._repeat_worker(), name="show-network-dmx-scene-bank")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        self._task = None
        serials, self._serials = self._serials, {}
        for ser in serials.values():
            try:
                await asyncio.to_thread(ser.close)
            except Exception:
                logging.getLogger(__name__).debug('Non-fatal error in %s', __name__, exc_info=True)
        self.enabled = False
        self.active_scene_id = None

    async def recall(self, scene_id: str) -> None:
        if not self.enabled:
            raise PermissionError("DMX scene output is not armed")
        scene = self.scenes.get(str(scene_id))
        if scene is None:
            raise ValueError(f"Unknown DMX scene: {scene_id}")
        self.active_scene_id = scene.scene_id
        self.current_frame = bytes(scene.values)
        if not self.external_active():
            await self._send(self.current_frame)

    async def _repeat_worker(self) -> None:
        while True:
            await asyncio.sleep(self.repeat_interval)
            if not self.enabled or self.active_scene_id is None or self.external_active():
                continue
            try:
                await self._send(self.current_frame)
            except Exception as err:
                self.errors += 1
                self.last_error = f"{type(err).__name__}: {err}"

    async def _send(self, values: bytes) -> None:
        self.output.validate()
        self._sequence = (self._sequence + 1) & 0xFF
        cfg = self.output
        if cfg.protocol == "sacn":
            packet = build_sacn_frame(cfg.universe, values, sequence=self._sequence,
                                      priority=cfg.priority, source_name="Show Network DMX Scenes", cid=self._cid)
            await asyncio.to_thread(self._udp_send, packet, cfg.host.strip() or _sacn_group(cfg.universe), cfg.port or 5568, False)
        elif cfg.protocol == "artnet":
            packet = build_artnet_frame(cfg.universe, values, sequence=self._sequence)
            await asyncio.to_thread(self._udp_send, packet, cfg.host.strip(), cfg.port or 6454, True)
        else:
            await self._enttec_send(cfg.enttec_device, build_enttec_frame(values))
        self.sent += 1
        self.last_send = time.time()
        self.last_error = None

    @staticmethod
    def _udp_send(packet: bytes, host: str, port: int, broadcast: bool) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            if broadcast:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (host, int(port)))

    async def _enttec_send(self, device: str, packet: bytes) -> None:
        try:
            import serial
        except ImportError as err:
            raise RuntimeError("pyserial is required for ENTTEC output") from err
        ser = self._serials.get(device)
        if ser is None or not getattr(ser, "is_open", False):
            ser = await asyncio.to_thread(serial.Serial, device, 57600, timeout=0.2)
            self._serials[device] = ser
        await asyncio.to_thread(ser.write, packet)
        await asyncio.to_thread(ser.flush)

    def snapshot(self) -> dict[str, Any]:
        return {
            "dmx_scene_bank_enabled": self.enabled,
            "dmx_scene_bank_limit": MAX_SCENES,
            "dmx_scene_bank_count": len(self.scenes),
            "dmx_scene_bank_scenes": [scene.public() for scene in self.scenes.values()],
            "dmx_scene_bank_output": asdict(self.output),
            "dmx_scene_bank_active": self.active_scene_id,
            "dmx_scene_bank_external_override": self.external_active(),
            "dmx_scene_bank_external_source": self.external_source,
            "dmx_scene_bank_external_protocol": self.external_protocol,
            "dmx_scene_bank_external_last_seen": self.external_last_seen,
            "dmx_scene_bank_resume_delay_s": self.output.external_hold_s,
            "dmx_scene_bank_sent": self.sent,
            "dmx_scene_bank_errors": self.errors,
            "dmx_scene_bank_last_error": self.last_error,
            "dmx_scene_bank_last_send": self.last_send,
            "dmx_scene_bank_note": "Maximum 19 scenes; exactly one output universe/transport is configured for this mode.",
        }

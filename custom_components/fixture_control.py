"""Persistent GDTF fixture patch and guarded fixed-state DMX output."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, asdict, field
import json
from pathlib import Path
import socket
import time
import uuid
from typing import Any

from .gdtf import GDTFFixture, GDTFMode, parse_gdtf
from .power_manager import build_sacn_frame, build_artnet_frame, _sacn_group


@dataclass
class FixturePatch:
    patch_id: str
    name: str
    gdtf_file: str
    mode: str
    universe: int
    address: int
    protocol: str = "sacn"
    host: str = ""
    priority: int = 100
    values: dict[str, float] = field(default_factory=dict)
    rdm_uid: str | None = None

    def public(self) -> dict[str, Any]:
        return asdict(self)


class FixtureControlEngine:
    def __init__(self, config_dir: str | Path, *, repeat_hz: float = 10.0):
        self.config_dir = Path(config_dir)
        self.library_dir = self.config_dir / "show_network_gdtf_library"
        self.inbox_dir = self.config_dir / "show_network_gdtf_inbox"
        self.store_path = self.config_dir / "show_network_fixture_patches.json"
        self.library_dir.mkdir(parents=True, exist_ok=True)
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.fixtures: dict[str, GDTFFixture] = {}
        self.patches: dict[str, FixturePatch] = {}
        self.control_enabled = False
        self.repeat_interval = 1.0 / max(1.0, min(float(repeat_hz), 40.0))
        self._task: asyncio.Task | None = None
        self._cid = uuid.uuid4().bytes
        self._sequences: dict[tuple[str, int, str], int] = {}
        self._frames: dict[tuple[str, int, str, int], bytearray] = {}
        self.sent = 0
        self.errors = 0
        self.last_error: str | None = None
        self.last_send: float | None = None

    def load(self) -> None:
        self.fixtures.clear()
        for path in sorted(self.library_dir.glob("*.gdtf")):
            try:
                fx = parse_gdtf(path)
                self.fixtures[path.name] = fx
            except Exception:
                continue
        try:
            raw = json.loads(self.store_path.read_text(encoding="utf-8")) if self.store_path.exists() else []
        except (OSError, ValueError, TypeError):
            raw = []
        self.patches.clear()
        for item in raw if isinstance(raw, list) else []:
            try:
                patch = FixturePatch(**item)
                self._validate_patch(patch)
                self.patches[patch.patch_id] = patch
            except Exception:
                continue

    def save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.store_path.with_suffix(".tmp")
        tmp.write_text(json.dumps([p.public() for p in self.patches.values()], ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.store_path)

    def import_gdtf(self, filename: str) -> dict[str, Any]:
        src = (self.inbox_dir / Path(filename).name).resolve()
        inbox = self.inbox_dir.resolve()
        if src.parent != inbox or not src.exists() or src.suffix.lower() != ".gdtf":
            raise ValueError("GDTF file must exist in /config/show_network_gdtf_inbox and end in .gdtf")
        fixture = parse_gdtf(src)
        safe_name = f"{fixture.source_sha256[:16]}_{Path(filename).name}"
        dst = self.library_dir / safe_name
        if not dst.exists():
            dst.write_bytes(src.read_bytes())
        self.fixtures[safe_name] = fixture
        return {"file": safe_name, "fixture": fixture.snapshot()}

    def _fixture_mode(self, patch: FixturePatch) -> tuple[GDTFFixture, GDTFMode]:
        fixture = self.fixtures.get(patch.gdtf_file)
        if fixture is None:
            raise ValueError(f"Unknown imported GDTF file: {patch.gdtf_file}")
        return fixture, fixture.mode(patch.mode)

    def _validate_patch(self, patch: FixturePatch) -> None:
        if not patch.patch_id.strip():
            raise ValueError("patch_id is required")
        if patch.protocol not in {"sacn", "artnet"}:
            raise ValueError("protocol must be sacn or artnet")
        if not 1 <= int(patch.universe) <= 63999:
            raise ValueError("universe out of range")
        if not 1 <= int(patch.address) <= 512:
            raise ValueError("address out of range")
        if not 1 <= int(patch.priority) <= 200:
            raise ValueError("sACN priority out of range")
        if patch.protocol == "artnet" and not patch.host.strip():
            raise ValueError("Art-Net output requires an explicit destination host")
        _, mode = self._fixture_mode(patch)
        if patch.address + mode.footprint - 1 > 512:
            raise ValueError("fixture footprint exceeds DMX universe")

    def upsert_patch(self, data: dict[str, Any]) -> FixturePatch:
        patch_id = str(data.get("patch_id") or "").strip()
        old = self.patches.get(patch_id)
        values = dict(old.values) if old else {}
        values.update({str(k): float(v) for k, v in dict(data.get("values") or {}).items()})
        patch = FixturePatch(
            patch_id=patch_id,
            name=str(data.get("name") or patch_id),
            gdtf_file=str(data.get("gdtf_file") or ""),
            mode=str(data.get("mode") or ""),
            universe=int(data.get("universe", 1)),
            address=int(data.get("address", 1)),
            protocol=str(data.get("protocol", "sacn")).lower(),
            host=str(data.get("host") or ""),
            priority=int(data.get("priority", 100)),
            values=values,
            rdm_uid=(str(data.get("rdm_uid") or (old.rdm_uid if old else "")).lower() or None),
        )
        self._validate_patch(patch)
        self.patches[patch_id] = patch
        self.save()
        return patch

    def remove_patch(self, patch_id: str) -> None:
        self.patches.pop(str(patch_id), None)
        self.save()
        self._rebuild_frames()

    def attributes(self, patch_id: str) -> dict[str, dict[str, Any]]:
        patch = self.patches[str(patch_id)]
        _, mode = self._fixture_mode(patch)
        out: dict[str, dict[str, Any]] = {}
        for ch in mode.channels:
            item = out.setdefault(ch.attribute, {"min": ch.physical_min, "max": ch.physical_max, "channels": []})
            item["min"] = min(float(item["min"]), ch.physical_min)
            item["max"] = max(float(item["max"]), ch.physical_max)
            item["channels"].append(list(ch.offsets))
        return out

    def set_control_enabled(self, enabled: bool) -> None:
        self.control_enabled = bool(enabled)

    def set_attribute(self, patch_id: str, attribute: str, value: float) -> None:
        if not self.control_enabled:
            raise PermissionError("Fixture control is not armed")
        patch = self.patches.get(str(patch_id))
        if patch is None:
            raise ValueError(f"Unknown fixture patch: {patch_id}")
        attrs = self.attributes(patch.patch_id)
        if attribute not in attrs:
            raise ValueError(f"Unknown fixture attribute: {attribute}")
        lo, hi = float(attrs[attribute]["min"]), float(attrs[attribute]["max"])
        value = max(min(float(value), max(lo, hi)), min(lo, hi))
        patch.values[str(attribute)] = value
        self.save()
        self._apply_patch(patch)

    def _key(self, patch: FixturePatch) -> tuple[str, int, str, int]:
        return (patch.protocol, patch.universe, patch.host.strip(), patch.priority)

    def _apply_patch(self, patch: FixturePatch) -> None:
        _, mode = self._fixture_mode(patch)
        key = self._key(patch)
        frame = self._frames.setdefault(key, bytearray(512))
        for ch in mode.channels:
            if ch.attribute not in patch.values:
                continue
            encoded = ch.encode(float(patch.values[ch.attribute]))
            width = len(ch.offsets)
            raw = encoded.to_bytes(width, "big", signed=False)
            for idx, offset in enumerate(ch.offsets):
                absolute = patch.address + offset - 2
                if 0 <= absolute < 512:
                    frame[absolute] = raw[idx]

    def _rebuild_frames(self) -> None:
        self._frames.clear()
        for patch in self.patches.values():
            self._apply_patch(patch)

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._repeat_worker(), name="show-network-fixture-output")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    async def _repeat_worker(self) -> None:
        while True:
            await asyncio.sleep(self.repeat_interval)
            if not self.control_enabled:
                continue
            for key, frame in list(self._frames.items()):
                try:
                    await self._send(key, bytes(frame))
                except Exception as err:
                    self.errors += 1
                    self.last_error = f"{type(err).__name__}: {err}"

    async def send_now(self, patch_id: str) -> None:
        if not self.control_enabled:
            raise PermissionError("Fixture control is not armed")
        patch = self.patches[str(patch_id)]
        self._apply_patch(patch)
        key = self._key(patch)
        await self._send(key, bytes(self._frames[key]))

    async def _send(self, key: tuple[str, int, str, int], frame: bytes) -> None:
        protocol, universe, host, priority = key
        skey = (protocol, universe, host)
        seq = (self._sequences.get(skey, 0) + 1) & 0xFF
        self._sequences[skey] = seq
        if protocol == "sacn":
            packet = build_sacn_frame(universe, frame, sequence=seq, priority=priority, source_name="Show Network GDTF", cid=self._cid)
            target, port = host or _sacn_group(universe), 5568
        else:
            packet = build_artnet_frame(universe, frame, sequence=seq)
            target, port = host, 6454
        await asyncio.to_thread(self._udp_send, packet, target, port, protocol == "artnet")
        self.sent += 1
        self.last_send = time.time()

    @staticmethod
    def _udp_send(packet: bytes, host: str, port: int, broadcast: bool = False) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            if broadcast:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (host, int(port)))

    def snapshot(self) -> dict[str, Any]:
        return {
            "gdtf_library_count": len(self.fixtures),
            "gdtf_patch_count": len(self.patches),
            "gdtf_library": [
                {"file": filename, **fixture.snapshot()} for filename, fixture in sorted(self.fixtures.items())
            ],
            "gdtf_fixture_patches": [
                {**patch.public(), "attributes": self.attributes(patch.patch_id)} for patch in self.patches.values()
            ],
            "gdtf_control_enabled": self.control_enabled,
            "gdtf_output_sent": self.sent,
            "gdtf_output_errors": self.errors,
            "gdtf_output_last_error": self.last_error,
            "gdtf_output_last_send": self.last_send,
            "gdtf_note": "GDTF describes fixture DMX control only; it is not telemetry.",
        }

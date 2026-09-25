"""Minimal, safe GDTF 1.2 fixture parser for fixed-state DMX control.

GDTF is used only as a fixture definition here: DMX modes, channel offsets,
attributes and physical/channel-function ranges.  It is deliberately not used
as telemetry and no network activity is performed by this module.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Any


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(node: ET.Element, name: str):
    return [x for x in list(node) if _local(x.tag) == name]


def _desc(node: ET.Element, name: str):
    return [x for x in node.iter() if _local(x.tag) == name]


def _float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _dmx_token(value: str | None) -> tuple[int, int]:
    """Return (integer value, encoded byte width) from GDTF DMXValue syntax."""
    text = str(value or "0/1").strip()
    m = re.match(r"^\s*(\d+)\s*(?:/\s*(\d+))?", text)
    if not m:
        return 0, 1
    raw = int(m.group(1)); width = max(1, min(int(m.group(2) or 1), 4))
    return raw, width


def _scale_dmx(raw: int, src_width: int, dst_width: int) -> int:
    src_max = (1 << (8 * src_width)) - 1
    dst_max = (1 << (8 * dst_width)) - 1
    if src_max <= 0:
        return 0
    return max(0, min(dst_max, round(max(0, min(raw, src_max)) * dst_max / src_max)))


@dataclass(frozen=True)
class GDTFRange:
    dmx_from: int
    dmx_to: int
    physical_from: float
    physical_to: float

    def encode(self, value: float) -> int:
        lo, hi = self.physical_from, self.physical_to
        if hi == lo:
            return self.dmx_from
        t = (float(value) - lo) / (hi - lo)
        t = max(0.0, min(1.0, t))
        return round(self.dmx_from + t * (self.dmx_to - self.dmx_from))

    def contains(self, value: float) -> bool:
        lo, hi = sorted((self.physical_from, self.physical_to))
        return lo <= value <= hi


@dataclass(frozen=True)
class GDTFChannel:
    offsets: tuple[int, ...]
    attribute: str
    ranges: tuple[GDTFRange, ...]
    default_dmx: int = 0

    @property
    def width(self) -> int:
        return len(self.offsets)

    @property
    def physical_min(self) -> float:
        vals = [x for r in self.ranges for x in (r.physical_from, r.physical_to)]
        return min(vals) if vals else 0.0

    @property
    def physical_max(self) -> float:
        vals = [x for r in self.ranges for x in (r.physical_from, r.physical_to)]
        return max(vals) if vals else 100.0

    def encode(self, value: float) -> int:
        if not self.ranges:
            t = max(0.0, min(1.0, float(value) / 100.0))
            return round(t * ((1 << (8 * self.width)) - 1))
        selected = next((r for r in self.ranges if r.contains(value)), None)
        if selected is None:
            # Choose the nearest physical range rather than silently wrapping.
            selected = min(self.ranges, key=lambda r: min(abs(value-r.physical_from), abs(value-r.physical_to)))
        return selected.encode(value)


@dataclass(frozen=True)
class GDTFMode:
    name: str
    channels: tuple[GDTFChannel, ...]

    @property
    def footprint(self) -> int:
        return max((max(c.offsets) for c in self.channels if c.offsets), default=0)


@dataclass(frozen=True)
class GDTFFixture:
    fixture_id: str
    name: str
    manufacturer: str
    description: str
    gdtf_version: str
    modes: tuple[GDTFMode, ...]
    source_sha256: str

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    def mode(self, name: str) -> GDTFMode:
        for mode in self.modes:
            if mode.name == name:
                return mode
        raise ValueError(f"Unknown GDTF DMX mode: {name}")


def parse_gdtf(path: str | Path) -> GDTFFixture:
    path = Path(path)
    blob = path.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    with zipfile.ZipFile(path, "r") as zf:
        names = {n.lower(): n for n in zf.namelist()}
        desc_name = names.get("description.xml")
        if not desc_name:
            raise ValueError("GDTF archive has no description.xml")
        xml_blob = zf.read(desc_name)
    root = ET.fromstring(xml_blob)
    fixture_nodes = _desc(root, "FixtureType")
    if not fixture_nodes:
        raise ValueError("GDTF description has no FixtureType")
    fx = fixture_nodes[0]
    manufacturer = str(fx.attrib.get("Manufacturer") or "").strip()
    name = str(fx.attrib.get("Name") or fx.attrib.get("ShortName") or path.stem).strip()
    description = str(fx.attrib.get("Description") or "").strip()
    fixture_id = str(fx.attrib.get("FixtureTypeID") or digest[:32]).strip()
    version = str(root.attrib.get("DataVersion") or root.attrib.get("Version") or "1.2")

    modes: list[GDTFMode] = []
    for mode_node in _desc(fx, "DMXMode"):
        mode_name = str(mode_node.attrib.get("Name") or "Mode").strip()
        channels_parent = next(iter(_children(mode_node, "DMXChannels")), None)
        if channels_parent is None:
            continue
        channels: list[GDTFChannel] = []
        for dmx_ch in _children(channels_parent, "DMXChannel"):
            offset_text = str(dmx_ch.attrib.get("Offset") or "").strip()
            if not offset_text or offset_text.lower() == "none":
                continue
            try:
                offsets = tuple(int(x.strip()) for x in offset_text.split(",") if x.strip())
            except ValueError:
                continue
            if not offsets or any(x < 1 or x > 512 for x in offsets):
                continue
            width = len(offsets)
            logical = next(iter(_children(dmx_ch, "LogicalChannel")), None)
            if logical is None:
                continue
            functions_parent = next(iter(_children(logical, "ChannelFunctions")), None)
            functions = _children(functions_parent, "ChannelFunction") if functions_parent is not None else []
            attribute = str(logical.attrib.get("Attribute") or "").strip()
            if functions and functions[0].attrib.get("Attribute"):
                attribute = str(functions[0].attrib.get("Attribute") or attribute).strip()
            if not attribute:
                attribute = str(dmx_ch.attrib.get("Geometry") or f"Channel{offsets[0]}")

            default_raw, default_width = _dmx_token(dmx_ch.attrib.get("Default"))
            default_dmx = _scale_dmx(default_raw, default_width, width)
            starts: list[tuple[int, ET.Element]] = []
            for fn in functions:
                raw, raw_width = _dmx_token(fn.attrib.get("DMXFrom"))
                starts.append((_scale_dmx(raw, raw_width, width), fn))
            starts.sort(key=lambda x: x[0])
            max_dmx = (1 << (8 * width)) - 1
            ranges: list[GDTFRange] = []
            for idx, (start, fn) in enumerate(starts):
                end = starts[idx + 1][0] - 1 if idx + 1 < len(starts) else max_dmx
                pfrom = _float(fn.attrib.get("PhysicalFrom"), 0.0)
                pto = _float(fn.attrib.get("PhysicalTo"), 100.0)
                ranges.append(GDTFRange(start, max(start, end), pfrom, pto))
            channels.append(GDTFChannel(offsets, attribute, tuple(ranges), default_dmx))
        modes.append(GDTFMode(mode_name, tuple(channels)))
    if not modes:
        raise ValueError("GDTF fixture has no usable DMX mode")
    return GDTFFixture(fixture_id, name, manufacturer, description, version, tuple(modes), digest)

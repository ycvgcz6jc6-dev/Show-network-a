"""Tests for gdtf.py's GDTF 1.2 parser, using a minimal, hand-built
fixture that follows the real GDTF XML schema (GDTF/FixtureType/
DMXModes/DMXMode/DMXChannels/DMXChannel/LogicalChannel/ChannelFunctions/
ChannelFunction), rather than testing against unverified assumptions.
No test previously existed for this module.

Fixture covers the two trickiest code paths: multi-byte (16-bit) DMX
value scaling, and building physical-value ranges from multiple
ChannelFunctions on one LogicalChannel (Pan: -270..0 on one function,
0..270 on the next, split at DMXFrom).
"""
from __future__ import annotations

import os
import zipfile

import pytest

from custom_components.dmx_monitor.gdtf import parse_gdtf, GDTFRange, GDTFChannel

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
MINIMAL_GDTF = os.path.join(FIXTURES, "gdtf_minimal_spec.gdtf")


def test_fixture_identity_fields():
    fx = parse_gdtf(MINIMAL_GDTF)
    assert fx.name == "TestFixture"
    assert fx.manufacturer == "TestCo"
    assert fx.gdtf_version == "1.2"
    assert len(fx.source_sha256) == 64  # sha256 hex digest


def test_single_byte_dimmer_channel():
    fx = parse_gdtf(MINIMAL_GDTF)
    mode = fx.modes[0]
    dimmer = next(c for c in mode.channels if c.attribute == "Dimmer")
    assert dimmer.offsets == (1,)
    assert dimmer.width == 1
    assert dimmer.default_dmx == 0
    assert dimmer.physical_min == 0.0
    assert dimmer.physical_max == 1.0


def test_dimmer_mid_value_scales_to_8_bit_midpoint():
    fx = parse_gdtf(MINIMAL_GDTF)
    dimmer = next(c for c in fx.modes[0].channels if c.attribute == "Dimmer")
    assert dimmer.encode(0.5) == 128
    assert dimmer.encode(0.0) == 0
    assert dimmer.encode(1.0) == 255


def test_two_byte_pan_channel_offsets_and_width():
    fx = parse_gdtf(MINIMAL_GDTF)
    pan = next(c for c in fx.modes[0].channels if c.attribute == "Pan")
    assert pan.offsets == (2, 3)
    assert pan.width == 2
    assert pan.physical_min == -270.0
    assert pan.physical_max == 270.0


def test_pan_default_already_matching_width_is_not_rescaled():
    """Default="32768/2" is already declared at the channel's own 2-byte
    width -- must come through unchanged, not rescaled again."""
    fx = parse_gdtf(MINIMAL_GDTF)
    pan = next(c for c in fx.modes[0].channels if c.attribute == "Pan")
    assert pan.default_dmx == 32768


def test_pan_negative_range_encodes_correctly_at_16_bit():
    fx = parse_gdtf(MINIMAL_GDTF)
    pan = next(c for c in fx.modes[0].channels if c.attribute == "Pan")
    # -135 is the midpoint of the -270..0 function (DMX 0..32767)
    assert pan.encode(-135) == 16384
    assert pan.encode(-270) == 0


def test_pan_positive_range_encodes_correctly_at_16_bit():
    fx = parse_gdtf(MINIMAL_GDTF)
    pan = next(c for c in fx.modes[0].channels if c.attribute == "Pan")
    # 135 is the midpoint of the 0..270 function (DMX 32768..65535)
    assert pan.encode(135) == 49152
    assert pan.encode(270) == 65535


def test_mode_footprint_matches_highest_offset():
    fx = parse_gdtf(MINIMAL_GDTF)
    mode = fx.modes[0]
    assert mode.footprint == 3  # Pan's offset (2,3) -> highest is 3


def test_unknown_mode_name_raises():
    fx = parse_gdtf(MINIMAL_GDTF)
    with pytest.raises(ValueError):
        fx.mode("DoesNotExist")


def test_archive_without_description_xml_raises(tmp_path):
    bad = tmp_path / "empty.gdtf"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("readme.txt", "not a fixture")
    with pytest.raises(ValueError, match="description.xml"):
        parse_gdtf(bad)


def test_fixture_with_no_dmx_modes_raises(tmp_path):
    xml = b"""<?xml version="1.0"?><GDTF DataVersion="1.2">
    <FixtureType Name="Empty" Manufacturer="X"><DMXModes></DMXModes></FixtureType></GDTF>"""
    bad = tmp_path / "no_modes.gdtf"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("description.xml", xml)
    with pytest.raises(ValueError, match="no usable DMX mode"):
        parse_gdtf(bad)


# --- GDTFRange.encode / contains, tested directly (not through a file) ---

def test_range_encode_clamps_outside_physical_bounds():
    r = GDTFRange(dmx_from=0, dmx_to=255, physical_from=0.0, physical_to=100.0)
    assert r.encode(-50) == 0     # clamped below range
    assert r.encode(150) == 255   # clamped above range


def test_range_contains_handles_reversed_physical_bounds():
    """Some GDTF functions declare PhysicalFrom > PhysicalTo (inverted
    axis); contains() must still work regardless of declaration order."""
    r = GDTFRange(dmx_from=0, dmx_to=255, physical_from=100.0, physical_to=0.0)
    assert r.contains(50) is True
    assert r.contains(150) is False


def test_channel_falls_back_to_nearest_range_outside_all_ranges():
    """A physical value outside every declared range must snap to the
    nearest range's boundary rather than silently wrapping or crashing."""
    ch = GDTFChannel(
        offsets=(1,), attribute="Zoom",
        ranges=(
            GDTFRange(0, 127, 10.0, 20.0),
            GDTFRange(128, 255, 20.0, 30.0),
        ),
    )
    # 5.0 is below both ranges -- nearest is the first range's low end.
    assert ch.encode(5.0) == 0
    # 35.0 is above both ranges -- nearest is the second range's high end.
    assert ch.encode(35.0) == 255


def test_channel_with_no_ranges_falls_back_to_percent_scaling():
    ch = GDTFChannel(offsets=(1,), attribute="Generic", ranges=())
    assert ch.encode(50.0) == 128  # 50% of 255, rounded
    assert ch.encode(0.0) == 0
    assert ch.encode(100.0) == 255

"""Tests for etc_cem3.py's HTML parsing, grounded in real pages captured
from an actual CEM3 rack (Rack #2, "grada salle A 2") via the user's own
browser (Safari .webarchive export of http://10.2.2.3/index.asp and
.../setup.html), not synthetic/hand-written HTML.

Two real bugs were found and fixed by running the existing parser
against this real capture, before any test existed for this module at
all:
  1. rack_name: regex required whitespace directly after "CEM3", but the
     real page's HTML has none (the visual gap is CSS-only,
     `<span class="header_title">ETC CEM3</span>grada salle A 2 (Rack #2)`)
     -- rack_name silently came back None.
  2. errors: the "AF .+" fault pattern also matched the Software Versions
     table's own row labels ("AF Card 1".."AF Card 4"), producing four
     false-positive hardware faults on every single poll, alongside the
     one real error the device actually reports ("No Data DMX port A").
"""
from __future__ import annotations

import os

from custom_components.dmx_monitor.etc_cem3 import parse_cem3_system_html

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _load(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


def test_real_system_page_rack_name():
    """Bug 1 regression: the real page has zero whitespace between
    '</span>ETC CEM3</span>' and the rack name in the flattened text."""
    result = parse_cem3_system_html(_load("cem3_index_real.html"))
    assert result["rack_name"] == "grada salle A 2"
    assert result["rack_number"] == 2


def test_real_system_page_software_versions():
    result = parse_cem3_system_html(_load("cem3_index_real.html"))
    assert result["software_version"] == "1.7.4.9.0.105"


def test_real_system_page_three_phase_power():
    result = parse_cem3_system_html(_load("cem3_index_real.html"))
    assert result["phase_x_voltage_v"] == 240.0
    assert result["phase_y_voltage_v"] == 237.0
    assert result["phase_z_voltage_v"] == 230.0
    assert result["line_frequency_hz"] == 50.0


def test_real_system_page_errors_no_false_positives_from_af_card_versions():
    """Bug 2 regression: 'AF Card 1'..'AF Card 4' are Software Versions
    table row labels on this real page (three populated with a firmware
    version, one -- AF Card 4 -- blank, meaning that slot has no card
    installed), not faults. Only the one real, device-reported error
    line must come through."""
    result = parse_cem3_system_html(_load("cem3_index_real.html"))
    assert result["errors"] == ["No Data DMX port A"]
    assert "AF Card 1" not in result["errors"]
    assert "AF Card 2" not in result["errors"]
    assert "AF Card 3" not in result["errors"]
    assert "AF Card 4" not in result["errors"]


def test_real_system_page_nav_links():
    result = parse_cem3_system_html(_load("cem3_index_real.html"))
    link_labels = [label for label, _href in result["links"]]
    assert link_labels == ["System", "Dimmers", "Set Levels", "Setup", "Presets", "Files"]


def test_genuine_af_fault_with_extra_wording_is_still_caught():
    """The fix must not blanket-exclude everything starting with 'AF ' --
    only the exact 'AF Card <1-4>' shape proven (from the real page) to
    be a version-table label. A line with additional fault wording after
    the card number must still be flagged, preserving the original
    pattern's intent for a genuine fault this project has not personally
    observed but should not stop catching."""
    html = """<html><body><div id="content_header">
    <span class="header_title">ETC CEM3</span>Test Rack (Rack #1)</div>
    <div id="errors_section"><p>AF Card 2 Communication Fault<br></p></div>
    </body></html>"""
    result = parse_cem3_system_html(html)
    assert any("AF Card 2 Communication Fault" in e for e in result["errors"])


def test_bare_af_card_number_still_excluded_regardless_of_surrounding_whitespace():
    html = """<html><body><table><tr><th>AF Card 1</th><td>3.1.2.0.0.1</td></tr></table></body></html>"""
    result = parse_cem3_system_html(html)
    assert result["errors"] == []


# --- Circuit Setup page (setup.html) ------------------------------------

from custom_components.dmx_monitor.etc_cem3 import parse_cem3_circuit_setup_html


def test_real_setup_page_total_circuit_count():
    """The real captured page patches exactly 72 circuits (Space 1,
    Circuit 97 through 168, Lug 1 through 72)."""
    result = parse_cem3_circuit_setup_html(_load("cem3_setup_real.html"))
    assert result["circuit_setup_total"] == 72


def test_real_setup_page_module_part_numbers():
    """Three genuine ETC dimmer module part numbers appear on this real
    rack -- confirms the module column is read correctly, not guessed."""
    result = parse_cem3_circuit_setup_html(_load("cem3_setup_real.html"))
    assert result["circuit_setup_modules"] == ["ED15N", "ETD15AFR", "ETD25AFR"]


def test_real_setup_page_first_and_last_circuit_exact_values():
    result = parse_cem3_circuit_setup_html(_load("cem3_setup_real.html"))
    circuits = result["circuits"]
    assert circuits[0] == {
        "space": 1, "circuit": 97, "lug": 1, "module": "ETD15AFR",
        "firing_mode": "Normal", "control_mode": "Switched", "curve": "Custom1",
    }
    assert circuits[-1] == {
        "space": 1, "circuit": 168, "lug": 72, "module": "ED15N",
        "firing_mode": "Normal", "control_mode": "Dimmable", "curve": "ModSquare",
    }


def test_real_setup_page_control_modes_and_curves_read_from_selected_option():
    """Verifies the parser reads the <select>'s "selected" option's value
    attribute specifically -- not just the first <option> listed, which
    would silently be wrong (the first listed option is "Dimmable" for
    every row regardless of what's actually configured)."""
    result = parse_cem3_circuit_setup_html(_load("cem3_setup_real.html"))
    modes = {c["control_mode"] for c in result["circuits"]}
    curves = {c["curve"] for c in result["circuits"]}
    assert modes == {"Dimmable", "Switched"}
    assert curves == {"Custom1", "ModSquare"}


def test_setup_html_row_missing_a_column_is_skipped_not_guessed():
    html = '<table id="dimmer_table"><tbody><tr><td>1</td><td>1</td><td>1</td></tr></tbody></table>'
    result = parse_cem3_circuit_setup_html(html)
    assert result["circuit_setup_total"] == 0


def test_setup_html_oversized_body_rejected():
    import pytest
    huge = "<html>" + ("x" * (3 * 1024 * 1024))
    with pytest.raises(ValueError):
        parse_cem3_circuit_setup_html(huge)

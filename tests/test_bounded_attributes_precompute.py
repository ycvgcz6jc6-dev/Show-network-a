"""Performance fix (block 8, Observabilité): the extra_state_attributes
fix already applied for protocol_rx_diagnostics (a confirmed
~0.6s-per-update sensor: its property ran a full json.dumps()-based
bound_attributes() call on every single HA state read, not once per
actual data update) was only ever wired up for that one measured key.
Six other sensors (show_network_health, device_model, show_network_doctor,
show_snapshot, incident_center, pre_show) plus etc_cem3 exposed the same
shape of risk -- a potentially large nested dict recomputed on every
read -- without ever having been individually flagged as slow. Extended
the same precompute-once-per-cycle pattern to all of them, batched into
a single executor round trip.

These tests verify the sensor-side contract directly (a precomputed
"<key>_bounded" value in coordinator.data is returned as-is, without
recomputing bound_attributes on the raw key) using a minimal fake
coordinator -- not the full coordinator cycle, which is covered by the
existing suite's regression tests for each individual check
(doctor/pre_show/health_engine/etc).
"""
from __future__ import annotations

from custom_components.dmx_monitor.sensor import ShowNetworkSensor


class _FakeCoordinator:
    def __init__(self, data: dict):
        self.data = data


def _sensor(data: dict, key: str) -> ShowNetworkSensor:
    return ShowNetworkSensor(_FakeCoordinator(data), key, key)


def test_precomputed_bounded_value_is_returned_as_is():
    """The whole point of the fix: when the coordinator has already
    computed the bounded form, the sensor must use it directly rather
    than recomputing bound_attributes() on the raw dict."""
    precomputed = {"overall": "ok", "_marker": "this exact object came from the coordinator"}
    data = {"show_network_health": {"overall": "ok"}, "show_network_health_bounded": precomputed}
    assert _sensor(data, "show_network_health").extra_state_attributes == precomputed


def test_falls_back_to_direct_computation_when_not_yet_precomputed():
    """Defensive fallback for the very first refresh cycle (or any state
    where the bounded key genuinely isn't present yet) -- must still
    return correct data, just without the precompute benefit that cycle."""
    data = {"show_network_health": {"overall": "warning", "checks_total": 3}}
    result = _sensor(data, "show_network_health").extra_state_attributes
    assert result["overall"] == "warning"
    assert result["checks_total"] == 3


def test_device_model_sensor_reads_device_model_bounded_key():
    """show_network_devices reads from the *device_model* coordinator
    key (different name from its own sensor key) -- the precomputed key
    must match the *source* key's name (device_model_bounded), not the
    sensor's own key (show_network_devices_bounded, which does not
    exist)."""
    precomputed = {"count": 5, "_marker": "precomputed"}
    data = {"device_model": {"count": 5}, "device_model_bounded": precomputed}
    assert _sensor(data, "show_network_devices").extra_state_attributes == precomputed


def test_all_seven_extended_keys_use_their_precomputed_form():
    mapping = {
        "show_network_health": "show_network_health",
        "show_network_devices": "device_model",
        "show_network_doctor": "show_network_doctor",
        "show_snapshot": "show_snapshot",
        "incident_center": "incident_center",
        "pre_show": "pre_show",
        "protocol_rx_diagnostics": "protocol_rx_diagnostics",
    }
    for sensor_key, source_key in mapping.items():
        precomputed = {"_marker": f"precomputed-{source_key}"}
        data = {source_key: {"raw": True}, f"{source_key}_bounded": precomputed}
        result = _sensor(data, sensor_key).extra_state_attributes
        assert result == precomputed, f"{sensor_key} did not use its precomputed {source_key}_bounded value"


def test_etc_cem3_rack_sensor_uses_precomputed_bounded_value():
    precomputed = {"racks": [], "_marker": "precomputed"}
    data = {"etc_cem3": {"racks": []}, "etc_cem3_bounded": precomputed}
    result = _sensor(data, "etc_cem3_racks_total").extra_state_attributes
    assert result == precomputed


def test_device_inventory_keeps_interface_field_for_the_discovery_panel_filter():
    """Regression test for a real user report ('toujours pas possible de
    choisir les cartes dans réseaux pour regarder par carte'): the
    per-NIC filter dropdown in the discovery panel (ShowNetworkDiscovery,
    interfaceOf(r) => r.interface) reads this exact field from
    device_inventory's own rows -- it was trimmed away entirely, so the
    filter always had nothing to offer. Field confirmed to genuinely
    exist on DeviceInventory itself (device_inventory.py) before this
    fix; it just never survived sensor.py's field allowlist."""
    data = {"device_inventory": [
        {"unique_id": "a", "display_name": "GigaCore", "interface": "enp10s0"},
    ]}
    result = _sensor(data, "device_inventory").extra_state_attributes
    assert result["devices"][0]["interface"] == "enp10s0"

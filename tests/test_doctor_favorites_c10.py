"""Phase C10 (rapport maître, S100): "Les favoris deviennent le périmètre
privilégié de Doctor/Incident/History, sans limiter la découverte
globale." monitor_mode ('monitor' = starred as a favorite via the
inventory's own toggle) used to be stored and displayed but never read
anywhere -- this is the first behavioral use of it: a dedicated Doctor
check.
"""
from __future__ import annotations

from time import time

from custom_components.dmx_monitor.doctor import ShowNetworkDoctor


def _minimal_data(devices=None, routes=None):
    """Just enough of a coordinator snapshot for Doctor.run() to not
    crash on the *other* checks -- this module intentionally only reads
    facts already present in the snapshot, so every section needs a
    reasonable (possibly empty) value to iterate over."""
    return {
        "network_interfaces": [],
        "dmx_universes": [],
        "topology": {},
        "device_model": {"devices": devices or [], "conflicts": [], "count": len(devices or [])},
        "switch_telemetry": [],
        "protocol_rx_diagnostics": {"ptp": {}},
        "host_metrics": {},
        "show_network_health": {},
        "archive": {},
        "network_routes": routes or [],
    }


def _favorite_device(id_="mac:001122334455", name="Luminex GigaCore", ip="10.4.1.3", last_seen=None):
    return {
        "id": id_, "name": name, "ip": ip,
        "last_seen": last_seen if last_seen is not None else time(),
        "monitor_mode": "monitor",
    }


def test_no_favorites_gives_info_status_and_does_not_restrict_other_checks():
    result = ShowNetworkDoctor().run(_minimal_data(devices=[
        {"id": "mac:aa", "name": "Non favori", "ip": "10.4.1.9", "last_seen": time(), "monitor_mode": "auto"},
    ]))
    fav_check = next(c for c in result["checks"] if c["id"] == "favorites")
    assert fav_check["status"] == "info"
    assert fav_check["evidence"]["favorites_total"] == 0
    # The other checks (identity, interfaces, ...) must still be present --
    # favorites getting attention must never shrink the global scope.
    assert any(c["id"] == "identity" for c in result["checks"])
    assert any(c["id"] == "interfaces" for c in result["checks"])


def test_fresh_reachable_favorite_is_ok():
    fav = _favorite_device()
    data = _minimal_data(
        devices=[fav],
        routes=[{"target": "10.4.1.3", "reachable": True, "interface": "enp10s0", "via": "same_subnet"}],
    )
    result = ShowNetworkDoctor().run(data)
    fav_check = next(c for c in result["checks"] if c["id"] == "favorites")
    assert fav_check["status"] == "ok"
    assert fav_check["evidence"]["favorites_total"] == 1
    assert fav_check["evidence"]["stale"] == []
    assert fav_check["evidence"]["unreachable"] == []


def test_stale_favorite_is_warning():
    old = time() - 600  # 10 minutes ago, past the 300s staleness threshold
    fav = _favorite_device(last_seen=old)
    data = _minimal_data(devices=[fav])  # no matching route entry at all
    result = ShowNetworkDoctor().run(data)
    fav_check = next(c for c in result["checks"] if c["id"] == "favorites")
    assert fav_check["status"] == "warning"
    assert len(fav_check["evidence"]["stale"]) == 1
    assert fav_check["evidence"]["stale"][0]["name"] == "Luminex GigaCore"


def test_unreachable_favorite_is_error_and_outranks_staleness():
    old = time() - 600
    fav = _favorite_device(last_seen=old)
    data = _minimal_data(
        devices=[fav],
        routes=[{"target": "10.4.1.3", "reachable": False, "reason": "no_matching_subnet_and_no_default_route"}],
    )
    result = ShowNetworkDoctor().run(data)
    fav_check = next(c for c in result["checks"] if c["id"] == "favorites")
    assert fav_check["status"] == "error", "an unreachable favorite must outrank a merely stale one"
    assert len(fav_check["evidence"]["unreachable"]) == 1
    assert len(fav_check["evidence"]["stale"]) == 1  # still reported, both facts kept

    # And a real, unreachable favorite must be able to push the whole
    # Doctor run's overall verdict to "error" -- that's what "privileged
    # scope" has to actually mean, not just a cosmetic label.
    assert result["overall"] == "error"


def test_favorite_check_does_not_affect_non_favorite_devices():
    healthy_favorite = _favorite_device(id_="mac:aa", ip="10.4.1.3")
    stale_non_favorite = {
        "id": "mac:bb", "name": "Pas favori, silencieux depuis longtemps",
        "ip": "10.4.1.99", "last_seen": time() - 9999, "monitor_mode": "auto",
    }
    data = _minimal_data(
        devices=[healthy_favorite, stale_non_favorite],
        routes=[{"target": "10.4.1.3", "reachable": True, "interface": "enp10s0", "via": "same_subnet"}],
    )
    result = ShowNetworkDoctor().run(data)
    fav_check = next(c for c in result["checks"] if c["id"] == "favorites")
    assert fav_check["status"] == "ok", "a stale non-favorite must not affect the favorites check"
    assert fav_check["evidence"]["favorites_total"] == 1

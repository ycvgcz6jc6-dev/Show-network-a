from types import SimpleNamespace
from custom_components.dmx_monitor.device_inventory import DeviceInventory
from custom_components.dmx_monitor.web_proxy_security import (
    is_proxy_eligible_device_ip, validate_port, validated_redirect,
)


def coord(inv):
    return SimpleNamespace(inventory=inv)


def test_manual_only_ip_is_not_proxy_authorization():
    inv = DeviceInventory()
    inv.upsert(unique_id="manual-ip:10.2.1.50:any", ip="10.2.1.50", sources={"operator"},
               evidence=[{"field":"ip","value":"10.2.1.50","source":"operator_manual_target","confidence":1.0}])
    assert not is_proxy_eligible_device_ip(coord(inv), "10.2.1.50")


def test_observed_ip_is_proxy_eligible_even_if_operator_also_marked_it():
    inv = DeviceInventory()
    inv.upsert(unique_id="candidate:10.2.1.50", ip="10.2.1.50", sources={"operator", "mdns"},
               evidence=[{"field":"ip","value":"10.2.1.50","source":"mdns","confidence":0.8}])
    assert is_proxy_eligible_device_ip(coord(inv), "10.2.1.50")


def test_unsafe_special_ips_rejected():
    inv = DeviceInventory()
    for ip in ("127.0.0.1", "0.0.0.0", "224.0.0.1"):
        inv.upsert(unique_id=f"x:{ip}", ip=ip, sources={"mdns"})
        assert not is_proxy_eligible_device_ip(coord(inv), ip)


def test_redirect_must_stay_on_exact_ip():
    base = "http://10.2.1.50:80/index.html"
    assert validated_redirect(base, "/status", "10.2.1.50") == "http://10.2.1.50:80/status"
    assert validated_redirect(base, "http://10.2.1.50:8080/status", "10.2.1.50") is not None
    assert validated_redirect(base, "http://10.2.1.51/admin", "10.2.1.50") is None
    assert validated_redirect(base, "http://localhost/admin", "10.2.1.50") is None
    assert validated_redirect(base, "file:///etc/passwd", "10.2.1.50") is None


def test_port_bounds():
    assert validate_port(None, 80) == 80
    assert validate_port("443", 80) == 443
    for bad in ("0", "65536", "nope"):
        try:
            validate_port(bad, 80)
        except ValueError:
            pass
        else:
            raise AssertionError(bad)

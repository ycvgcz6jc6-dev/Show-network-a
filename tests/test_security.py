from pathlib import Path
from custom_components.dmx_monitor.security import SecurityManager


def test_security_password_roundtrip(tmp_path: Path):
    s = SecurityManager(str(tmp_path))
    assert not s.state.configured
    s.set_password("correct-horse")
    assert s.state.configured
    assert s.verify("correct-horse")
    assert not s.verify("wrong-password")
    s.unlock("correct-horse")
    assert s.state.unlocked
    s.lock()
    assert not s.state.unlocked


def test_ip_allowlist_supports_ip_and_cidr():
    from custom_components.dmx_monitor.security import ip_allowed, normalize_ip_allowlist
    allow = normalize_ip_allowlist(["192.168.10.0/24", "10.0.0.5"])
    assert ip_allowed("192.168.10.22", allow)
    assert ip_allowed("10.0.0.5", allow)
    assert not ip_allowed("10.0.0.6", allow)

"""Safety and secondary control gate for Show Network.

Home Assistant authentication remains the primary access control. This module
adds an optional, local, second factor for *active* Show Network operations
such as OSC OUT and projector/light control. Passwords are never stored in
clear text.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
import hmac
import json
import os
import time
import ipaddress

SENSITIVE_KEYS = {"password", "passwd", "token", "api_key", "apikey", "secret", "community", "snmp_community", "authorization", "cookie"}
REDACTED = "<redacted>"


def redact(data: Any) -> Any:
    if isinstance(data, dict):
        return {str(k): REDACTED if str(k).lower() in SENSITIVE_KEYS or any(s in str(k).lower() for s in ("password", "token", "secret", "community")) else redact(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [redact(v) for v in data]
    return data


def normalize_ip_allowlist(values: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    """Validate IP/CIDR entries for remote-control source filtering."""
    out: list[str] = []
    for value in values or ():
        text = str(value).strip()
        if not text:
            continue
        try:
            out.append(str(ipaddress.ip_network(text, strict=False)))
        except ValueError:
            try:
                out.append(str(ipaddress.ip_address(text)))
            except ValueError as err:
                raise ValueError(f"Invalid IP/CIDR allowlist entry: {text}") from err
    return tuple(dict.fromkeys(out))


def ip_allowed(source: str, allowlist: tuple[str, ...] | list[str] | None) -> bool:
    """Return True when source is permitted; an unset filter preserves local compatibility."""
    if not allowlist:
        return True
    try:
        address = ipaddress.ip_address(source)
    except ValueError:
        return False
    networks = normalize_ip_allowlist(tuple(allowlist or ()))
    return any(address in ipaddress.ip_network(item, strict=False) for item in networks)


def validate_archive_limits(retention_days: int, max_bytes: int) -> tuple[int, int]:
    return max(1, min(int(retention_days), 3650)), max(64 * 1024, min(int(max_bytes), 100 * 1024 * 1024))


def active_discovery_allowed(options: dict[str, Any]) -> bool:
    return bool(options.get("active_discovery", False))


@dataclass
class SecurityState:
    configured: bool = False
    unlocked_until: float = 0.0

    @property
    def unlocked(self) -> bool:
        return self.configured and time.monotonic() < self.unlocked_until


class SecurityManager:
    """Salted PBKDF2 password gate for active operations."""
    def __init__(self, path: str, unlock_seconds: int = 1800, autoload: bool = True) -> None:
        base = Path(path)
        self.path = base if base.suffix == ".json" else base / "show_network_security.json"
        self.unlock_seconds = max(60, min(int(unlock_seconds), 86400))
        self.state = SecurityState()
        self._salt = ""
        self._digest = ""
        self._failed_attempts = 0
        self._locked_until = 0.0
        if autoload:
            self.load()

    def load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
            self._salt = str(data.get("salt", ""))
            self._digest = str(data.get("digest", ""))
            self.state.configured = bool(self._salt and self._digest)
        except (OSError, ValueError, TypeError):
            self._salt = self._digest = ""
            self.state.configured = False

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"algorithm": "pbkdf2_sha256", "iterations": 310000, "salt": self._salt, "digest": self._digest}, indent=2), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(self.path)

    def set_password(self, password: str) -> None:
        if not isinstance(password, str) or len(password) < 8:
            raise ValueError("Password must contain at least 8 characters")
        self._salt = os.urandom(16).hex()
        self._failed_attempts = 0
        self._locked_until = 0.0
        self._digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(self._salt), 310000).hex()
        self.state.configured = True
        self.state.unlocked_until = 0.0
        self._save()

    def verify(self, password: str) -> bool:
        if not self.state.configured or time.monotonic() < self._locked_until:
            return False
        try:
            candidate = hashlib.pbkdf2_hmac("sha256", str(password).encode(), bytes.fromhex(self._salt), 310000).hex()
        except (TypeError, ValueError):
            candidate = ""
        ok = hmac.compare_digest(candidate, self._digest)
        if ok:
            self._failed_attempts = 0
            return True
        self._failed_attempts += 1
        if self._failed_attempts >= 5:
            self._locked_until = time.monotonic() + 30
            self._failed_attempts = 0
        return False

    def unlock(self, password: str) -> None:
        if not self.verify(password):
            raise PermissionError("Invalid Show Network password")
        self.state.unlocked_until = time.monotonic() + self.unlock_seconds

    def lock(self) -> None:
        self.state.unlocked_until = 0.0

    def require_unlocked(self) -> None:
        if not self.state.configured:
            raise PermissionError("Active control is locked: configure a Show Network password first")
        if not self.state.unlocked:
            raise PermissionError("Active control is locked")

    def snapshot(self) -> dict[str, Any]:
        remaining = max(0, int(self.state.unlocked_until - time.monotonic())) if self.state.unlocked else 0
        return {"configured": self.state.configured, "unlocked": self.state.unlocked, "unlock_remaining_s": remaining}

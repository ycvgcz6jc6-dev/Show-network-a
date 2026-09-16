"""Central safety gate for Show Network active/control features.

This module is intentionally small and dependency-free. It provides:

- ``SecurityManager``: an explicit arm/disarm gate for any feature that can
  affect real equipment (HA light/scene actions, OSC/MIDI output, DMX scene
  bank output, etc.). It is *never* auto-armed from persisted state: every
  Home Assistant restart starts locked, and something (a service call from
  the frontend or automation) must explicitly unlock it again. This matches
  the project's stated policy that an active output must never be assumed
  to be safely re-armed after a restart.
- ``ip_allowed`` / ``normalize_ip_allowlist``: a conservative IP allowlist
  used by modules that open an *active* outbound connection (AES70/OCA) or
  that accept control input from the network (OSC receiver). An empty/None
  allowlist means "no restriction configured" and allows any source; this
  mirrors the fact that none of these features currently expose a dedicated
  allowlist option in config_flow.py, so the safe default must not silently
  break existing behaviour.
- ``redact``: a recursive, JSON-safe redaction helper used before writing
  diagnostics bundles or archive/journal entries to disk.
- ``validate_archive_limits``: defensive clamping of retention/size settings
  for the event archive, mirroring the bounds already enforced in the
  config flow (1-3650 days, 256000-100000000 bytes).
"""
from __future__ import annotations

import ipaddress
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

_LOGGER = logging.getLogger(__name__)

# Mirrors the bounds already enforced in config_flow.py for
# CONF_ARCHIVE_RETENTION_DAYS / CONF_ARCHIVE_MAX_BYTES. Kept here too so the
# archive is defended even if it is ever constructed outside the config flow
# (tests, migrations, manual calls).
_MIN_RETENTION_DAYS = 1
_MAX_RETENTION_DAYS = 3650
_MIN_ARCHIVE_BYTES = 256_000
_MAX_ARCHIVE_BYTES = 100 * 1024 * 1024

# Case-insensitive key fragments that are always considered sensitive when
# found in any dict about to be persisted or exported. This is intentionally
# a fragment match (not an exact key match) so variants like
# "gigacore_community", "snmp_community", "wifi_password" are all caught,
# while ordinary identifiers such as "key" (used pervasively as a plain
# record id elsewhere in this codebase, e.g. AudioAmplifierInventory.key)
# are deliberately *not* included to avoid destroying normal diagnostics
# data with false-positive redaction.
_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "community",
    "credential",
    "api_key",
    "apikey",
    "authorization",
    "auth_token",
    "access_token",
    "client_secret",
    "private_key",
    "pin_code",
    "passphrase",
)

REDACTED_PLACEHOLDER = "***REDACTED***"


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

def _is_sensitive_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    return any(fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS)


def redact(data: Any) -> Any:
    """Return a deep copy of ``data`` with sensitive values masked.

    Only dict keys are inspected for sensitivity; the function recurses into
    dicts, lists and tuples. Any other JSON-safe scalar (str/int/float/bool/
    None) is passed through unchanged. Callers are expected to have already
    made ``data`` JSON-safe (bytes, dataclasses, sets, etc. converted) before
    calling this function; ``redact`` does not attempt that conversion
    itself so it stays a pure, side-effect-free masking step.
    """
    if isinstance(data, dict):
        out: dict[Any, Any] = {}
        for key, value in data.items():
            if _is_sensitive_key(key) and value not in (None, "", {}, []):
                out[key] = REDACTED_PLACEHOLDER
            else:
                out[key] = redact(value)
        return out
    if isinstance(data, list):
        return [redact(item) for item in data]
    if isinstance(data, tuple):
        return tuple(redact(item) for item in data)
    return data


# ---------------------------------------------------------------------------
# IP allowlist
# ---------------------------------------------------------------------------

def normalize_ip_allowlist(raw: Any) -> tuple:
    """Normalize a user-supplied allowlist into a tuple of ip_network objects.

    Accepts None, a single string (comma/whitespace separated), or an
    iterable of strings. Each entry may be a bare address ("10.0.0.5") or a
    CIDR ("10.0.0.0/24"). Invalid entries are logged and skipped rather than
    raising, consistent with the rest of this codebase's "never crash on a
    bad config value" style. An empty/None input returns an empty tuple,
    which ``ip_allowed`` treats as "no restriction configured".
    """
    if raw is None:
        return ()
    if isinstance(raw, str):
        candidates: Iterable[str] = raw.replace(",", " ").split()
    else:
        try:
            candidates = list(raw)
        except TypeError:
            return ()
    networks = []
    for item in candidates:
        text = str(item).strip()
        if not text:
            continue
        try:
            networks.append(ipaddress.ip_network(text, strict=False))
        except ValueError:
            _LOGGER.warning("Ignoring invalid IP allowlist entry: %r", text)
    return tuple(networks)


def ip_allowed(ip: str, allowlist: tuple) -> bool:
    """Return True if ``ip`` is permitted by ``allowlist``.

    An empty allowlist (the default when no restriction has been configured)
    always allows. This keeps existing receive-only behaviour unchanged for
    modules that have no dedicated allowlist option in config_flow.py today,
    while still letting an explicit allowlist restrict an active/outbound
    module such as the AES70 controller.
    """
    if not allowlist:
        return True
    try:
        addr = ipaddress.ip_address(str(ip))
    except ValueError:
        return False
    return any(addr in network for network in allowlist)


# ---------------------------------------------------------------------------
# Archive limits
# ---------------------------------------------------------------------------

def validate_archive_limits(retention_days: int, max_bytes: int) -> tuple[int, int]:
    """Clamp archive retention/size settings to safe, documented bounds.

    Mirrors the voluptuous bounds already enforced in config_flow.py
    (1-3650 days, 256000-100000000 bytes) so the archive is defended even if
    constructed with a value that bypassed the config flow (defaults,
    migrations, direct instantiation).
    """
    try:
        days = int(retention_days)
    except (TypeError, ValueError):
        days = _MIN_RETENTION_DAYS
    try:
        size = int(max_bytes)
    except (TypeError, ValueError):
        size = _MIN_ARCHIVE_BYTES

    clamped_days = min(max(days, _MIN_RETENTION_DAYS), _MAX_RETENTION_DAYS)
    clamped_size = min(max(size, _MIN_ARCHIVE_BYTES), _MAX_ARCHIVE_BYTES)

    if clamped_days != days:
        _LOGGER.warning("Archive retention_days %s out of bounds, clamped to %s", days, clamped_days)
    if clamped_size != size:
        _LOGGER.warning("Archive max_bytes %s out of bounds, clamped to %s", size, clamped_size)

    return clamped_days, clamped_size


# ---------------------------------------------------------------------------
# SecurityManager
# ---------------------------------------------------------------------------

class SecurityLockedError(PermissionError):
    """Raised by SecurityManager.require_unlocked() while the gate is locked."""


@dataclass
class _SecurityState:
    locked: bool = True
    reason: str | None = None
    changed_at: float = field(default_factory=time.time)
    changed_by: str | None = None


class SecurityManager:
    """Explicit arm/disarm gate for active/control features.

    The gate always starts locked, regardless of ``autoload`` or of any
    audit history on disk. ``autoload`` only controls whether a small audit
    log of past lock/unlock events is read back for display purposes (the
    "history" the UI can show); it never re-arms the gate itself. This is a
    deliberate safety property, not an oversight: a Show Network restart
    must never silently resume driving real equipment.
    """

    def __init__(self, config_path: str, *, autoload: bool = False, log_name: str = "show_network_security_log.jsonl") -> None:
        self._config_dir = Path(config_path)
        self._log_path = self._config_dir / log_name
        self._state = _SecurityState(locked=True)
        self._history: list[dict[str, Any]] = []
        if autoload:
            self._load_history()

    # -- history -----------------------------------------------------------
    def _load_history(self) -> None:
        try:
            if not self._log_path.exists():
                return
            lines = self._log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            _LOGGER.debug("Could not read security audit log", exc_info=True)
            return
        history = []
        for line in lines[-200:]:
            line = line.strip()
            if not line:
                continue
            try:
                history.append(json.loads(line))
            except ValueError:
                continue
        self._history = history

    def _append_history(self, entry: dict[str, Any]) -> None:
        self._history.append(entry)
        self._history = self._history[-200:]
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            _LOGGER.debug("Could not append to security audit log", exc_info=True)

    # -- gate ----------------------------------------------------------------
    @property
    def locked(self) -> bool:
        return self._state.locked

    def require_unlocked(self) -> None:
        """Raise SecurityLockedError if the gate is currently locked."""
        if self._state.locked:
            raise SecurityLockedError(
                "Show Network active outputs are locked. Call the unlock "
                "service before enabling light sync, OSC/MIDI output, or "
                "any other control feature."
            )

    def unlock(self, *, reason: str | None = None, by: str | None = None) -> None:
        self._state = _SecurityState(locked=False, reason=reason, changed_by=by)
        self._append_history({"ts": self._state.changed_at, "action": "unlock", "reason": reason, "by": by})

    def lock(self, *, reason: str | None = None, by: str | None = None) -> None:
        self._state = _SecurityState(locked=True, reason=reason, changed_by=by)
        self._append_history({"ts": self._state.changed_at, "action": "lock", "reason": reason, "by": by})

    def snapshot(self) -> dict[str, Any]:
        return {
            "locked": self._state.locked,
            "reason": self._state.reason,
            "changed_at": self._state.changed_at,
            "changed_by": self._state.changed_by,
            "recent_events": list(self._history[-20:]),
            "policy": "never_autoarmed_on_restart",
        }

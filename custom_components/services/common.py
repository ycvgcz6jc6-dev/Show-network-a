"""Shared Home Assistant service helpers."""
from __future__ import annotations
from typing import Awaitable, Callable
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
DOMAIN = "dmx_monitor"

def coordinator_for_call(hass: HomeAssistant, call):
    """Resolve a coordinator without assuming the first configured entry."""
    entry_id = call.data.get("entry_id")
    entries = hass.data.get(DOMAIN, {})
    if entry_id:
        item = entries.get(str(entry_id))
        if item and item.get("coordinator"):
            return item["coordinator"]
        raise ValueError(f"Unknown config entry: {entry_id}")
    coordinators = [item.get("coordinator") for item in entries.values() if item.get("coordinator")]
    if len(coordinators) == 1:
        return coordinators[0]
    raise ValueError("entry_id is required when multiple DMX Monitor entries are configured")


# Exceptions the domain layer (security.py, ha_builder.py, qlcplus_bridge.py,
# ...) already raises with a clear, human-readable message describing
# exactly what went wrong and why -- e.g. "Active control is locked" or
# "QLC+ is not configured (see Show Network options)". Home Assistant's
# service-call frontend only shows that message to the user for
# HomeAssistantError (and its ServiceValidationError subclass); any other
# exception type is collapsed to a generic "Unknown error" toast. That
# mismatch is exactly what the audit observed: four different locked-state
# rejections (OSC/MIDI/Show Control/config restore) and the QLC+
# not-configured case all showed the same uninformative "Unknown error",
# even though the real cause was already spelled out in the raised message.
#
# Programming bugs (AttributeError, TypeError, KeyError from an actual code
# defect) are deliberately left unwrapped so they keep surfacing as real
# errors/tracebacks in the log instead of being repackaged as a misleading
# validation message.
_USER_FACING_EXCEPTIONS = (PermissionError, ValueError, RuntimeError, LookupError)


def guarded(handler: Callable[[ServiceCall], Awaitable[None]]) -> Callable[[ServiceCall], Awaitable[None]]:
    """Wrap a service handler so its own error messages reach the user.

    Use on every handler passed to hass.services.async_register: wraps
    handler(call) and re-raises any of _USER_FACING_EXCEPTIONS as a
    ServiceValidationError carrying the same message, which Home
    Assistant's frontend displays instead of "Unknown error".
    """
    async def _guarded(call: ServiceCall):
        try:
            return await handler(call)
        except _USER_FACING_EXCEPTIONS as err:
            raise ServiceValidationError(str(err)) from err
    return _guarded

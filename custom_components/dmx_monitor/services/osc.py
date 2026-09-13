"""Show Network osc service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN
from ..osc_output import OSCTarget
from ..osc_profiles import PROFILES

async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "set_osc_output_enabled"):
        async def _set_osc_output_enabled(call):
            c = coordinator_for_call(hass, call)
            c.set_osc_output_enabled(bool(call.data["enabled"]))
        async def _create_osc_target(call):
            c = coordinator_for_call(hass, call)
            target = OSCTarget(str(call.data["target_id"]), str(call.data.get("name") or call.data["target_id"]), str(call.data["host"]), int(call.data.get("port", 8000)), bool(call.data.get("enabled", True)))
            c.osc_targets[target.target_id] = target
            c.save_osc_targets()
            c.publish(osc_targets=[t.__dict__ for t in c.osc_targets.values()])
        async def _remove_osc_target(call):
            c = coordinator_for_call(hass, call)
            c.osc_targets.pop(str(call.data["target_id"]), None)
            c.save_osc_targets()
            c.publish(osc_targets=[t.__dict__ for t in c.osc_targets.values()])
        async def _send_osc(call):
            c = coordinator_for_call(hass, call)
            target_id = str(call.data["target_id"])
            target = c.osc_targets.get(target_id)
            if not target: raise ValueError(f"Unknown OSC target: {target_id}")
            args = call.data.get("args", [])
            if not isinstance(args, list): raise ValueError("OSC args must be a list")
            c.security.require_unlocked()
            c.osc_output.send(target, str(call.data["address"]), args)
            c.publish_osc_status()
        async def _send_osc_profile_action(call):
            c = coordinator_for_call(hass, call)
            from ..osc_profiles import PROFILES
            profile_key = str(call.data["profile"])
            action_key = str(call.data["action"])
            profile = next((p for p in PROFILES if p.key == profile_key), None)
            if not profile:
                raise ValueError(f"Unknown OSC profile: {profile_key}")
            action = next((a for a in profile.actions if a.key == action_key), None)
            if not action:
                raise ValueError(f"Unknown OSC action: {profile_key}/{action_key}")
            target = c.osc_targets.get(str(call.data["target_id"]))
            if not target:
                raise ValueError("Unknown OSC target")
            c.security.require_unlocked()
            address = action.address
            params = dict(call.data.get("params") or {})
            for key, value in params.items():
                address = address.replace("{" + str(key) + "}", str(value))
            if "{" in address or "}" in address:
                raise ValueError("Missing OSC action parameters")
            args = call.data.get("args", [])
            if not isinstance(args, list):
                raise ValueError("OSC args must be a list")
            c.osc_output.send(target, address, args)
            c.publish_osc_status()
        hass.services.async_register(DOMAIN, "set_osc_output_enabled", _set_osc_output_enabled)
        hass.services.async_register(DOMAIN, "create_osc_target", _create_osc_target)
        hass.services.async_register(DOMAIN, "remove_osc_target", _remove_osc_target)
        hass.services.async_register(DOMAIN, "send_osc", _send_osc)
        hass.services.async_register(DOMAIN, "send_osc_profile_action", _send_osc_profile_action)

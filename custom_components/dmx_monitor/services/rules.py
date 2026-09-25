"""Show Network rules service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN, guarded
from ..rules import DmxAction, DmxCondition, DmxRule, parse_channel_selection

async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "create_rule"):
        async def _create_rule(call):
            coordinator = coordinator_for_call(hass, call)
            data = call.data
            try:
                action_data = data.get("action") or None
                off_action_data = data.get("off_action") or None
                action = DmxAction(**action_data) if action_data else None
                off_action = DmxAction(**off_action_data) if off_action_data else None
                condition = DmxCondition(
                    channels=parse_channel_selection(data["channels"]),
                    mode=str(data.get("mode", "any")),
                    threshold_on=int(data.get("threshold_on", 10)),
                    threshold_off=(int(data["threshold_off"]) if data.get("threshold_off") is not None else None),
                    x=int(data.get("x", 1)),
                )
                rule = DmxRule(
                    name=str(data["name"]), universe=int(data["universe"]), source=data.get("source") or None,
                    condition=condition, action=action, off_action=off_action,
                    on_delay_ms=int(data.get("on_delay_ms", 0)), off_delay_ms=int(data.get("off_delay_ms", 0)),
                    enabled=bool(data.get("enabled", False)), test_mode=bool(data.get("test_mode", False)),
                )
                coordinator.rules.add(rule)
                await coordinator.async_save_rules()
                coordinator.publish(dmx_rules=coordinator.rules.snapshot())
            except (KeyError, TypeError, ValueError) as err:
                raise ValueError(f"Invalid DMX rule: {err}") from err

        async def _update_rule(call):
            coordinator = coordinator_for_call(hass, call)
            data = call.data
            old_name = str(data.get("old_name") or data.get("name"))
            try:
                action_data = data.get("action") or None
                off_action_data = data.get("off_action") or None
                action = DmxAction(**action_data) if action_data else None
                off_action = DmxAction(**off_action_data) if off_action_data else None
                rule = DmxRule(
                    name=str(data["name"]), universe=int(data["universe"]), source=data.get("source") or None,
                    condition=DmxCondition(
                        channels=parse_channel_selection(data["channels"]),
                        mode=str(data.get("mode", "any")), threshold_on=int(data.get("threshold_on", 10)),
                        threshold_off=(int(data["threshold_off"]) if data.get("threshold_off") is not None else None),
                        x=int(data.get("x", 1)),
                    ),
                    action=action, off_action=off_action,
                    on_delay_ms=int(data.get("on_delay_ms", 0)), off_delay_ms=int(data.get("off_delay_ms", 0)),
                    enabled=bool(data.get("enabled", False)), test_mode=bool(data.get("test_mode", False)),
                )
                coordinator.rules.update(old_name, rule)
                await coordinator.async_save_rules()
                coordinator.publish(dmx_rules=coordinator.rules.snapshot(), dmx_rule_traces=coordinator.rules.trace_snapshot())
            except (KeyError, TypeError, ValueError) as err:
                raise ValueError(f"Invalid DMX rule: {err}") from err

        async def _remove_rule(call):
            coordinator = coordinator_for_call(hass, call)
            coordinator.rules.remove(str(call.data["name"]))
            await coordinator.async_save_rules()
            coordinator.publish(dmx_rules=coordinator.rules.snapshot())

        async def _set_rule_enabled(call):
            coordinator = coordinator_for_call(hass, call)
            coordinator.rules.set_enabled(str(call.data["name"]), bool(call.data["enabled"]))
            await coordinator.async_save_rules()
            coordinator.publish(dmx_rules=coordinator.rules.snapshot())

        async def _set_rule_test_mode(call):
            coordinator = coordinator_for_call(hass, call)
            coordinator.rules.set_test_mode(str(call.data["name"]), bool(call.data["enabled"]))
            await coordinator.async_save_rules()
            coordinator.publish(dmx_rules=coordinator.rules.snapshot())

        hass.services.async_register(DOMAIN, "create_rule", guarded(_create_rule))
        hass.services.async_register(DOMAIN, "update_rule", guarded(_update_rule))
        hass.services.async_register(DOMAIN, "remove_rule", guarded(_remove_rule))
        hass.services.async_register(DOMAIN, "set_rule_enabled", guarded(_set_rule_enabled))
        hass.services.async_register(DOMAIN, "set_rule_test_mode", guarded(_set_rule_test_mode))

        async def _test_rule(call):
            coordinator = coordinator_for_call(hass, call)
            name = str(call.data["name"])
            rule = coordinator.rules.rules.get(name)
            if rule is None:
                raise ValueError(f"Unknown DMX rule: {name}")
            values = call.data.get("values")
            if not isinstance(values, list):
                # Optional convenience: test against the current matching universe.
                values = None
                for item in coordinator.dmx_tracker.all():
                    if item.universe == rule.universe and (not rule.source or rule.source in {item.source, item.protocol}):
                        values = list(getattr(item, "values", b"")[:512])
                        break
            if values is None:
                raise ValueError("No DMX snapshot available for this rule")
            values = [int(v) for v in values[:512]]
            # DMX channel values are single bytes (0-255). Audit-confirmed
            # gap: passing out-of-range values (e.g. 256, -1) was silently
            # accepted with "aucune erreur affichée, aucun résultat détaillé"
            # -- neither rejected nor normalized. Reject clearly instead of
            # letting invalid simulated data flow into threshold comparisons.
            out_of_range = [v for v in values if v < 0 or v > 255]
            if out_of_range:
                raise ValueError(
                    f"DMX values must be between 0 and 255 (got out-of-range: {out_of_range[:5]}"
                    f"{', ...' if len(out_of_range) > 5 else ''})"
                )
            result = coordinator.rules.test(rule, values)
            coordinator.publish(dmx_rule_test={
                "rule": result.rule_name,
                "active": result.trace.active,
                "target": result.trace.target,
                "active_channels": list(result.trace.active_channels),
                "count_active": result.trace.count_active,
                "required": result.trace.required,
                "threshold": result.trace.threshold,
                "reason": result.trace.reason,
            })

        async def _clear_rule_history(call):
            coordinator = coordinator_for_call(hass, call)
            coordinator.rules.history.clear()
            coordinator.publish(dmx_rule_traces=coordinator.rules.trace_snapshot())

        hass.services.async_register(DOMAIN, "test_rule", guarded(_test_rule))

        hass.services.async_register(DOMAIN, "clear_rule_history", guarded(_clear_rule_history))

        async def _set_light_sync(call):
            coordinator = coordinator_for_call(hass, call)
            enabled = bool(call.data.get("enabled", False))
            coordinator.set_light_sync_enabled(enabled)

        hass.services.async_register(DOMAIN, "set_light_sync_enabled", guarded(_set_light_sync))

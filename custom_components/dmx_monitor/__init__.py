"""Show Network integration."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry
import logging
from .runtime_data import ShowNetworkRuntimeData

DOMAIN = "dmx_monitor"
_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "binary_sensor", "switch"]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the single canonical frontend asset path."""
    if not hass.data.get(f"{DOMAIN}_static_registered"):
        from homeassistant.components.http import StaticPathConfig
        static_dir = str(__import__("pathlib").Path(__file__).parent / "static")
        await hass.http.async_register_static_paths([StaticPathConfig("/api/dmx_monitor/static", static_dir, False)])
        hass.data[f"{DOMAIN}_static_registered"] = True

    # Expose the existing Show Network frontend as a real Home Assistant
    # sidebar panel. Earlier builds served the JS bundle but never registered
    # a panel, so there was no visible interface unless a dashboard was added
    # manually.
    if not hass.data.get(f"{DOMAIN}_panel_registered"):
        from homeassistant.components import panel_custom
        await panel_custom.async_register_panel(
            hass,
            webcomponent_name="show-network-pro-dashboard",
            frontend_url_path="show-network",
            module_url="/api/dmx_monitor/static/show-network.js?v=0.12.4",
            sidebar_title="Show Network",
            sidebar_icon="mdi:network-outline",
            require_admin=True,
            config={},
            config_panel_domain=DOMAIN,
        )
        hass.data[f"{DOMAIN}_panel_registered"] = True
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one entry through the runtime composer and service registry."""
    settings = {**entry.data, **entry.options}
    from .services import async_register_services
    from .runtime.setup import async_setup_runtime
    runtime = await async_setup_runtime(hass, entry, settings)
    await async_register_services(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime.values
    entry.runtime_data = ShowNetworkRuntimeData(coordinator=runtime.coordinator, resource_registry=runtime.resources, archive=runtime.archive, backup_manager=runtime.backup_manager)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate legacy entries without destructive data changes."""
    if config_entry.version < 2:
        others = {entry.unique_id for entry in hass.config_entries.async_entries(DOMAIN) if entry.entry_id != config_entry.entry_id}
        hass.config_entries.async_update_entry(config_entry, version=2, unique_id="show_network" if "show_network" not in others else None)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload platforms and stop every background protocol resource safely."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    registry = data.get("resource_registry")
    if registry is not None:
        await registry.async_stop_all(_LOGGER)
    else:
        for key, method in (("ma_listener", "stop"), ("ptp_monitor", "stop"), ("dante_monitor", "stop"), ("aes67_monitor", "stop"), ("enttec_input", "stop"), ("dmx_network", "stop"), ("punchlight", "async_stop")):
            resource = data.get(key)
            if resource:
                try:
                    await getattr(resource, method)()
                except asyncio.CancelledError:
                    raise
                except Exception as err:
                    _LOGGER.debug("Error while stopping %s: %s", key, err)
    for key in ("backup_cancel", "archive_backup_cancel", "punchlight_discovery_cancel", "vendor_discovery_cancel"):
        cancel = data.get(key)
        if cancel:
            try:
                cancel()
            except Exception as err:
                _LOGGER.debug("Error cancelling %s: %s", key, err)
    coordinator = data.get("coordinator")
    if coordinator:
        coordinator.dmx_universe_entity_callback = None
        coordinator.ha_builder_callbacks = {}
        coordinator.ha_builder_remove_callbacks = {}
        try:
            await coordinator.watchdogs.async_stop()
        except Exception as err:
            _LOGGER.debug("Error stopping watchdogs: %s", err)
        try:
            await coordinator.async_stop()
        except Exception as err:
            _LOGGER.debug("Error stopping coordinator workers: %s", err)
    archive = data.get("archive")
    if archive:
        try:
            archive.record("system", "integration_stop", {"entry_id": entry.entry_id})
            await archive.async_stop()
        except Exception as err:
            _LOGGER.debug("Error stopping archive: %s", err)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok

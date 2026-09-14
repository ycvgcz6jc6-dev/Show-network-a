"""Show Network archive service handlers."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN

async def async_register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, "archive_export"):
        async def _archive_export(call):
            c = coordinator_for_call(hass, call)
            target = call.data.get("target")
            path = await hass.async_add_executor_job(c.archive.export_zip, target) if c.archive else None
            if c.archive:
                c.archive.record("archive", "journal_exported", {"target": str(path) if path else None})
            c.publish(archive=await hass.async_add_executor_job(c.archive.status) if c.archive else {})
        async def _archive_set_destination(call):
            c = coordinator_for_call(hass, call)
            destination = str(call.data["destination"])
            await hass.async_add_executor_job(c.archive.set_destination, destination)
            c.publish(archive=await hass.async_add_executor_job(c.archive.status))
            c.archive.record("archive", "destination_changed", {"destination": destination})
        async def _archive_backup(call):
            c = coordinator_for_call(hass, call)
            path = await hass.async_add_executor_job(c.archive.export_zip) if c.archive else None
            if c.archive:
                c.archive.record("archive", "journal_backup_created", {"target": str(path) if path else None})
            c.publish(archive=await hass.async_add_executor_job(c.archive.status) if c.archive else {})
        hass.services.async_register(DOMAIN, "archive_export", _archive_export)
        hass.services.async_register(DOMAIN, "archive_backup", _archive_backup)
        hass.services.async_register(DOMAIN, "archive_set_destination", _archive_set_destination)

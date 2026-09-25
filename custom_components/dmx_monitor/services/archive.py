"""Show Network archive, configuration backup and diagnostics handlers."""
from __future__ import annotations

import functools

from homeassistant.core import HomeAssistant

from ..services.common import coordinator_for_call, DOMAIN, guarded


async def async_register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "archive_export"):
        return

    async def _archive_export(call):
        c = coordinator_for_call(hass, call)
        target = call.data.get("target")
        path = await hass.async_add_executor_job(c.archive.export_zip, target) if c.archive else None
        if c.archive:
            c.archive.record("archive", "journal_exported", {"target": str(path) if path else None})
        c.publish(archive=await _archive_status(c))

    async def _archive_set_destination(call):
        c = coordinator_for_call(hass, call)
        destination = str(call.data["destination"])
        await hass.async_add_executor_job(c.archive.set_destination, destination)
        c.archive.record("archive", "destination_changed", {"destination": destination})
        c.publish(archive=await _archive_status(c))

    async def _archive_backup(call):
        c = coordinator_for_call(hass, call)
        path = await hass.async_add_executor_job(c.archive.export_zip) if c.archive else None
        if c.archive:
            c.archive.record("archive", "journal_backup_created", {"target": str(path) if path else None})
        c.publish(archive=await _archive_status(c))

    async def _config_backup_create(call):
        c = coordinator_for_call(hass, call)
        reason = str(call.data.get("reason", "manual"))[:80]
        path = await hass.async_add_executor_job(c.config_backups.export_bundle, None, reason)
        if c.archive:
            c.archive.record("persistence", "configuration_backup_created", {"target": str(path), "reason": reason})
        c.publish(archive=await _archive_status(c))

    async def _config_backup_restore(call):
        c = coordinator_for_call(hass, call)
        c.security.require_unlocked()
        source = str(call.data["source"])
        result = await hass.async_add_executor_job(c.config_backups.restore_bundle, source)
        if c.archive:
            c.archive.record("persistence", "configuration_backup_restored", {
                "source": source,
                "files": len(result.get("restored", [])),
                "restart_required": True,
            })
        c.publish(archive=await _archive_status(c))
        # The restored files are intentionally not hot-applied piecemeal. A
        # config-entry reload gives every runtime module one coherent snapshot.
        entry_id = getattr(c, "config_entry_id", None)
        if entry_id:
            hass.async_create_task(hass.config_entries.async_reload(entry_id))

    async def _diagnostics_export(call):
        c = coordinator_for_call(hass, call)
        archive_status = await hass.async_add_executor_job(c.archive.status) if c.archive else {}
        config_status = await hass.async_add_executor_job(c.config_backups.status)
        resources = c.resource_registry.snapshot() if c.resource_registry else []
        path = await hass.async_add_executor_job(
            functools.partial(
                c.diagnostics_exporter.export,
                dict(c.data),
                config_status=config_status,
                archive_status=archive_status,
                resources=resources,
            )
        )
        if c.archive:
            c.archive.record("diagnostics", "support_bundle_created", {"target": str(path)})
        c.publish(archive=await _archive_status(c))

    async def _archive_status(c):
        status = await hass.async_add_executor_job(c.archive.status) if c.archive else {}
        status["configuration_backups"] = await hass.async_add_executor_job(c.config_backups.status)
        status["diagnostics"] = c.diagnostics_exporter.status()
        return status

    hass.services.async_register(DOMAIN, "archive_export", guarded(_archive_export))
    hass.services.async_register(DOMAIN, "archive_backup", guarded(_archive_backup))
    hass.services.async_register(DOMAIN, "archive_set_destination", guarded(_archive_set_destination))
    hass.services.async_register(DOMAIN, "config_backup_create", guarded(_config_backup_create))
    hass.services.async_register(DOMAIN, "config_backup_restore", guarded(_config_backup_restore))
    hass.services.async_register(DOMAIN, "diagnostics_export", guarded(_diagnostics_export))

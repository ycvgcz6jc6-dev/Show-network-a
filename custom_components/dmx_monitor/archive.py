"""Persistent Show Timeline and journal archive.

The archive is intentionally metadata-first: it stores compact events rather
than raw packet payloads.  The destination is configurable and may be any
existing HA-accessible directory (for example /media/show_network, a second
mounted disk, or a mounted NAS/SMB share).
"""
from __future__ import annotations
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib, json, os, shutil, asyncio
from collections import deque
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile
from .security import redact, validate_archive_limits

DEFAULT_RETENTION_DAYS = 7
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_DESTINATION = "show_network_archive"

class EventArchive:
    def __init__(self, config_dir: str, retention_days: int = DEFAULT_RETENTION_DAYS,
                 max_bytes: int = DEFAULT_MAX_BYTES, destination: str | None = None) -> None:
        self.config_dir = Path(config_dir)
        self.retention_days, self.max_bytes = validate_archive_limits(retention_days, max_bytes)
        self.destination = destination or DEFAULT_DESTINATION
        self.root = self._resolve_root(self.destination)
        self._last_backup_success: str | None = None
        self._last_backup_error: str | None = None
        self._last_backup_path: str | None = None
        self._queue: asyncio.Queue[tuple[str, str, dict[str, Any] | None] | None] = asyncio.Queue(maxsize=2000)
        self._worker: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._recent = deque(maxlen=100)

    def _resolve_root(self, destination: str) -> Path:
        value = str(destination or DEFAULT_DESTINATION).strip()
        if not value:
            value = DEFAULT_DESTINATION
        p = Path(value).expanduser()
        if not p.is_absolute():
            p = self.config_dir / value
        return p.resolve()

    def set_destination(self, destination: str) -> Path:
        new_root = self._resolve_root(destination)
        self.destination = str(destination)
        self.root = new_root
        self._last_backup_error = None
        return new_root

    def _storage_check(self) -> dict[str, Any]:
        """Check destination health without mounting or writing anything.

        HA's internal config storage is trusted. Explicit external destinations
        must resolve to an existing mounted filesystem; Show Network never
        mounts SMB/NAS itself.
        """
        root = self.root
        try:
            relative_to_config = root.is_relative_to(self.config_dir.resolve())
        except AttributeError:
            relative_to_config = str(root).startswith(str(self.config_dir.resolve()) + os.sep)

        existing = root if root.exists() else root.parent
        while not existing.exists() and existing != existing.parent:
            existing = existing.parent
        mounted = os.path.ismount(existing)
        requires_mount = not relative_to_config
        available = bool(root.exists() or root.parent.exists())
        if requires_mount:
            ready = mounted and available and os.access(existing, os.W_OK | os.X_OK)
        else:
            ready = available and os.access(existing, os.W_OK | os.X_OK)
        try:
            free_bytes = shutil.disk_usage(existing).free
        except OSError:
            free_bytes = None
        return {
            "ready": ready,
            "mounted": mounted,
            "requires_mount": requires_mount,
            "writable": bool(os.access(existing, os.W_OK | os.X_OK)),
            "path": str(root),
            "free_bytes": free_bytes,
        }

    def _require_storage(self) -> dict[str, Any]:
        status = self._storage_check()
        if not status["ready"]:
            raise OSError("Show Network backup storage is not available or mounted")
        self.root.mkdir(parents=True, exist_ok=True)
        return status

    async def async_start(self) -> None:
        if self._worker and not self._worker.done():
            return
        self._loop = asyncio.get_running_loop()
        self._worker = asyncio.create_task(self._writer_loop(), name="show-network-archive-writer")

    async def async_stop(self) -> None:
        worker = self._worker
        if not worker:
            return
        try:
            await self._queue.put(None)
            await worker
        finally:
            self._worker = None
            self._loop = None

    async def _writer_loop(self) -> None:
        while True:
            item = await self._queue.get()
            if item is None:
                self._queue.task_done()
                break
            kind, event, data = item
            try:
                await asyncio.to_thread(self._record_sync, kind, event, data)
            except Exception:
                # Journaling must never take down Home Assistant.
                logging.getLogger(__name__).debug('Non-fatal error in %s', __name__, exc_info=True)
            finally:
                self._queue.task_done()

    def record(self, kind: str, event: str, data: dict[str, Any] | None = None) -> None:
        """Queue a journal event; never perform disk I/O on HA's event loop."""
        self._recent.append({"ts": datetime.now(timezone.utc).isoformat(), "kind": str(kind)[:40], "event": str(event)[:200], "data": redact(self._json_safe(data or {}))})
        if self._worker and not self._worker.done():
            try:
                self._queue.put_nowait((kind, event, data))
                return
            except asyncio.QueueFull:
                return
        # Synchronous fallback is used only before the async writer starts.
        self._record_sync(kind, event, data)

    def _record_sync(self, kind: str, event: str, data: dict[str, Any] | None = None) -> None:
        self._require_storage()
        safe_kind = "".join(c if c.isalnum() or c in "_-" else "_" for c in kind.lower())[:40] or "general"
        item = self._make_item(kind, event, data)
        path = self.root / f"{safe_kind}.jsonl"
        self._append(path, item)
        self._append(self.root / "show_timeline.jsonl", item)
        self._rotate(path)
        self._rotate(self.root / "show_timeline.jsonl")
        self.cleanup()

    def _make_item(self, kind: str, event: str, data: dict[str, Any] | None) -> dict[str, Any]:
        ts = datetime.now(timezone.utc).isoformat()
        item = {"ts": ts, "kind": str(kind)[:40], "event": str(event)[:200],
                "data": redact(self._json_safe(data or {})), "prev_hash": self._last_hash(self.root / "show_timeline.jsonl")}
        canonical = json.dumps(item, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        item["hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return item

    @staticmethod
    def _append(path: Path, item: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")

    def _last_hash(self, path: Path) -> str | None:
        if not path.exists(): return None
        try:
            with path.open("rb") as fh:
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                fh.seek(max(0, size - 8192))
                lines = fh.read().decode("utf-8", errors="ignore").splitlines()
            if lines: return json.loads(lines[-1]).get("hash")
        except (OSError, ValueError, TypeError):
            return None
        return None

    def _rotate(self, path: Path) -> None:
        try:
            if path.stat().st_size <= self.max_bytes: return
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            path.rename(path.with_name(f"{path.stem}.{stamp}.jsonl"))
        except OSError:
            return

    def cleanup(self) -> None:
        status = self._storage_check()
        if not status["ready"]:
            return
        cutoff = datetime.now(timezone.utc).timestamp() - self.retention_days * 86400
        for path in (*self.root.glob("*.jsonl"), *self.root.glob("show_network_journal_*.zip")):
            try:
                if path.stat().st_mtime < cutoff: path.unlink()
            except OSError:
                logging.getLogger(__name__).debug('Non-fatal error in %s', __name__, exc_info=True)

    def export_zip(self, target: str | None = None, include_all: bool = True) -> Path:
        self._require_storage()
        self.cleanup()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = Path(target).expanduser() if target else self.root / f"show_network_journal_{stamp}.zip"
        if not destination.is_absolute():
            destination = self.root / destination
        destination = destination.resolve()
        try:
            destination.relative_to(self.root.resolve())
        except ValueError as err:
            raise ValueError("Archive export target must remain inside the configured backup storage") from err
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with ZipFile(destination, "w", ZIP_DEFLATED) as zf:
                for path in sorted(self.root.glob("*.jsonl")):
                    zf.write(path, arcname=path.name)
                zf.writestr("archive_manifest.json", json.dumps({
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "retention_days": self.retention_days,
                    "destination": str(self.root),
                    "format": "show-network-timeline-v1",
                }, indent=2))
        except Exception as err:
            self._last_backup_error = str(err)[:300]
            raise
        self._last_backup_success = datetime.now(timezone.utc).isoformat()
        self._last_backup_error = None
        self._last_backup_path = str(destination)
        return destination

    def status(self) -> dict[str, Any]:
        storage = self._storage_check()
        files = list(self.root.glob("*.jsonl")) if storage["ready"] else []
        size = sum(p.stat().st_size for p in files if p.exists())
        last_success = self._last_backup_success
        if not last_success and storage["ready"]:
            try:
                candidates = list(self.root.glob("show_network_journal_*.zip"))
                if candidates:
                    latest = max(candidates, key=lambda item: item.stat().st_mtime)
                    last_success = datetime.fromtimestamp(latest.stat().st_mtime, timezone.utc).isoformat()
            except OSError:
                logging.getLogger(__name__).debug('Non-fatal error in %s', __name__, exc_info=True)
        return {"destination": str(self.root), "configured_destination": self.destination,
                "files": len(files), "bytes": size, "retention_days": self.retention_days,
                "max_bytes_per_file": self.max_bytes, "timeline_file": str(self.root / "show_timeline.jsonl"),
                "storage_ready": storage["ready"], "storage_mounted": storage["mounted"],
                "storage_requires_mount": storage["requires_mount"], "storage_writable": storage["writable"],
                "storage_free_bytes": storage["free_bytes"],
                "last_backup_success": last_success,
                "last_backup_error": self._last_backup_error,
                "last_backup_path": self._last_backup_path,
                "recent_events": list(self._recent)}

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if is_dataclass(value): return EventArchive._json_safe(asdict(value))
        if isinstance(value, dict): return {str(k): EventArchive._json_safe(v) for k,v in value.items()}
        if isinstance(value, (list, tuple, set)): return [EventArchive._json_safe(v) for v in value]
        if isinstance(value, (str, int, float, bool)) or value is None: return value
        return str(value)

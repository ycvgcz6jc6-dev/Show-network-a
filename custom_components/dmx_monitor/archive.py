"""Persistent Show Timeline and journal archive.

The archive is intentionally metadata-first: it stores compact events rather
than raw packet payloads.  The destination is configurable and may be any
existing HA-accessible directory (for example /media/show_network, a second
mounted disk, or a mounted NAS/SMB share).
"""
from __future__ import annotations
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib, json, os, shutil, asyncio, logging, time
from collections import deque
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile
from .security import redact, validate_archive_limits

_LOGGER = logging.getLogger(__name__)
# Minimum seconds between repeated log lines for the same error category --
# an audited installation could otherwise flood the log during a sustained
# failure (disk full, permissions lost mid-show) instead of one clear
# warning plus a running counter, which is what operators actually need.
_LOG_RATE_LIMIT_S = 60.0

DEFAULT_RETENTION_DAYS = 7
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_DESTINATION = "show_network_archive"
# Per-file rotation threshold: how big a single *.jsonl category file (or
# show_timeline.jsonl) is allowed to grow before being rotated into a
# timestamped file. Deliberately much smaller than the total quota below --
# previously max_bytes was used for BOTH this AND the (never actually
# enforced) total quota, which is exactly the "limite par fichier" vs
# "quota total" confusion an external audit correctly flagged.
PER_FILE_ROTATE_BYTES = 512 * 1024
# How many show_network_journal_*.zip exports to keep at most, regardless of
# age. A ZIP export bundles every current *.jsonl file; with an export every
# few hours (see runtime/setup.py), age-based retention alone lets dozens of
# near-duplicate ZIPs accumulate -- confirmed as the dominant contributor to
# an audited installation reaching ~63 MB against a configured 5 MB quota.
MAX_ZIP_EXPORTS = 5

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
        # NOTE (audit fix Z-07): every failure path below used to be a bare
        # `except Exception: pass` / `except asyncio.QueueFull: return` with
        # no counter and no log line -- an operator had no way to know
        # events were silently being lost (queue overflow, a write failing,
        # a rotation failing) short of noticing missing data much later.
        self._dropped_events = 0
        self._write_errors = 0
        self._rotate_errors = 0
        self._last_error: str | None = None
        self._last_error_at: str | None = None
        self._last_logged_at: dict[str, float] = {}
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

    def _record_error(self, category: str, message: str) -> None:
        """Record + rate-limited-log a failure. Never raises."""
        self._last_error = message
        self._last_error_at = datetime.now(timezone.utc).isoformat()
        now = time.monotonic()
        last = self._last_logged_at.get(category, 0.0)
        if now - last >= _LOG_RATE_LIMIT_S:
            self._last_logged_at[category] = now
            _LOGGER.warning("Show Network archive %s: %s", category, message)

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
            except Exception as exc:
                # Journaling must never take down Home Assistant, but it
                # must not vanish without a trace either (audit fix Z-07).
                self._write_errors += 1
                self._record_error("write", f"{type(exc).__name__}: {exc}")
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
                self._dropped_events += 1
                self._record_error("queue_full", f"journal queue saturated (maxsize={self._queue.maxsize}); event dropped ({self._dropped_events} total)")
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
            if path.stat().st_size <= PER_FILE_ROTATE_BYTES: return
            # NOTE (audit fix): second-precision timestamps let two
            # rotations within the same second collide and silently
            # overwrite each other. Microseconds make a collision
            # astronomically unlikely; the counter suffix loop is a hard
            # guarantee even so.
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            target = path.with_name(f"{path.stem}.{stamp}.jsonl")
            suffix = 0
            while target.exists():
                suffix += 1
                target = path.with_name(f"{path.stem}.{stamp}.{suffix}.jsonl")
            path.rename(target)
        except OSError as exc:
            self._rotate_errors += 1
            self._record_error("rotate", f"could not rotate {path.name}: {exc}")

    def cleanup(self) -> None:
        status = self._storage_check()
        if not status["ready"]:
            return
        cutoff = datetime.now(timezone.utc).timestamp() - self.retention_days * 86400

        # 1) Age-based purge, as before.
        for path in (*self.root.glob("*.jsonl"), *self.root.glob("show_network_journal_*.zip")):
            try:
                if path.stat().st_mtime < cutoff: path.unlink()
            except OSError:
                pass

        # 2) Cap the number of ZIP exports regardless of age -- a ZIP export
        # bundles every current *.jsonl file, so an export every few hours
        # (see runtime/setup.py) is the dominant contributor to archive
        # bloat if left to accumulate for the full retention window.
        try:
            zips = sorted(self.root.glob("show_network_journal_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old_zip in zips[MAX_ZIP_EXPORTS:]:
                try:
                    old_zip.unlink()
                except OSError:
                    pass
        except OSError:
            pass

        # 3) Global quota: max_bytes is the TOTAL archive size (jsonl +
        # zip), not a per-file limit (see PER_FILE_ROTATE_BYTES for that).
        # If still over quota after the age/count-based purges above,
        # delete the oldest remaining files (by mtime, any type) until back
        # under the limit. show_timeline.jsonl is deliberately never
        # deleted by this step (it is the canonical hash-chained record);
        # only its own rotated .jsonl copies are eligible.
        try:
            all_files = sorted(
                (*self.root.glob("*.jsonl"), *self.root.glob("show_network_journal_*.zip")),
                key=lambda p: p.stat().st_mtime,
            )
        except OSError:
            return
        total = sum(p.stat().st_size for p in all_files if p.exists())
        if total <= self.max_bytes:
            return
        for path in all_files:
            if total <= self.max_bytes:
                break
            if path.name == "show_timeline.jsonl":
                continue
            try:
                size = path.stat().st_size
                path.unlink()
                total -= size
            except OSError:
                continue

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
        jsonl_files = list(self.root.glob("*.jsonl")) if storage["ready"] else []
        zip_files = list(self.root.glob("show_network_journal_*.zip")) if storage["ready"] else []
        bytes_jsonl = sum(p.stat().st_size for p in jsonl_files if p.exists())
        bytes_zip = sum(p.stat().st_size for p in zip_files if p.exists())
        bytes_total = bytes_jsonl + bytes_zip
        last_success = self._last_backup_success
        if not last_success and storage["ready"]:
            try:
                candidates = list(self.root.glob("show_network_journal_*.zip"))
                if candidates:
                    latest = max(candidates, key=lambda item: item.stat().st_mtime)
                    last_success = datetime.fromtimestamp(latest.stat().st_mtime, timezone.utc).isoformat()
            except OSError:
                pass
        return {"destination": str(self.root), "configured_destination": self.destination,
                "files": len(jsonl_files) + len(zip_files), "bytes": bytes_total, "retention_days": self.retention_days,
                # NOTE: "bytes" is kept for backward compatibility with existing
                # readers (== bytes_total below); prefer the split fields.
                "bytes_jsonl": bytes_jsonl, "bytes_zip": bytes_zip, "bytes_total": bytes_total,
                "max_bytes_total": self.max_bytes, "max_bytes_per_file": PER_FILE_ROTATE_BYTES,
                "max_zip_exports": MAX_ZIP_EXPORTS, "zip_export_count": len(zip_files),
                "over_limit": bytes_total > self.max_bytes,
                "timeline_file": str(self.root / "show_timeline.jsonl"),
                "storage_ready": storage["ready"], "storage_mounted": storage["mounted"],
                "storage_requires_mount": storage["requires_mount"], "storage_writable": storage["writable"],
                "storage_free_bytes": storage["free_bytes"],
                "last_backup_success": last_success,
                "last_backup_error": self._last_backup_error,
                "last_backup_path": self._last_backup_path,
                "dropped_events": self._dropped_events,
                "write_errors": self._write_errors,
                "rotate_errors": self._rotate_errors,
                "last_error": self._last_error,
                "last_error_at": self._last_error_at,
                "recent_events": list(self._recent)}

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if is_dataclass(value): return EventArchive._json_safe(asdict(value))
        if isinstance(value, dict): return {str(k): EventArchive._json_safe(v) for k,v in value.items()}
        if isinstance(value, (list, tuple, set)): return [EventArchive._json_safe(v) for v in value]
        if isinstance(value, (str, int, float, bool)) or value is None: return value
        return str(value)

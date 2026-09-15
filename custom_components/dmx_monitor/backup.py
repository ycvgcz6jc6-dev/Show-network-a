from __future__ import annotations
import logging

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile


class ConfigBackupManager:
    """Atomic, rotating backup store for user-created Show Network data.

    Two formats are kept on purpose:
    * timestamped directories for fast local rollback and the existing automatic
      backup workflow;
    * self-describing ZIP bundles for manual export/restore.

    Secrets are excluded from portable bundles by default.  The security file
    can still be preserved by Home Assistant's own backup system.
    """

    FILES = (
        "show_network_control_mappings.json",
        "show_network_device_overrides.json",
        "show_network_dmx_circuit_monitor.json",
        "show_network_dmx_ha_mappings.json",
        "show_network_dmx_ha_zones.json",
        "show_network_dmx_scenes.json",
        "show_network_fixture_patches.json",
        "show_network_ha_builder.json",
        "show_network_midi_targets.json",
        "show_network_osc_targets.json",
        "show_network_power_manager.json",
        "show_network_rules.json",
        "show_network_show_control.json",
    )
    FORMAT = "show-network-config-backup-v2"

    def __init__(self, config_dir: str, keep: int = 10) -> None:
        self.config_dir = Path(config_dir).resolve()
        self.root = self.config_dir / "show_network_backups"
        self.keep = max(1, int(keep))
        self._last_backup_success: str | None = None
        self._last_backup_error: str | None = None
        self._last_backup_path: str | None = None
        self._last_restore_success: str | None = None
        self._last_restore_error: str | None = None
        self._last_restore_path: str | None = None

    @staticmethod
    def _stamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _present_files(self) -> list[Path]:
        return [self.config_dir / name for name in self.FILES if (self.config_dir / name).is_file()]

    def backup(self, reason: str = "scheduled") -> Path | None:
        """Create an atomic timestamped directory backup."""
        self.root.mkdir(parents=True, exist_ok=True)
        stamp = self._stamp()
        final = self.root / stamp
        tmp = self.root / f".{stamp}.tmp-{os.getpid()}"
        try:
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
            tmp.mkdir(parents=True)
            copied: list[dict[str, object]] = []
            for src in self._present_files():
                dst = tmp / src.name
                shutil.copy2(src, dst)
                copied.append({"name": src.name, "bytes": dst.stat().st_size, "sha256": self._sha256(dst)})
            if not copied:
                shutil.rmtree(tmp, ignore_errors=True)
                return None
            (tmp / "metadata.json").write_text(
                json.dumps({"format": self.FORMAT, "reason": str(reason)[:80], "created_at": stamp, "files": copied}, indent=2),
                encoding="utf-8",
            )
            if final.exists():
                # Extremely unlikely (two backups in the same second), but never
                # overwrite an existing rollback point.
                final = self.root / f"{stamp}-{os.getpid()}"
            tmp.replace(final)
            self._last_backup_success = datetime.now(timezone.utc).isoformat()
            self._last_backup_error = None
            self._last_backup_path = str(final)
            self.prune()
            return final
        except Exception as err:
            self._last_backup_error = str(err)[:300]
            shutil.rmtree(tmp, ignore_errors=True)
            raise

    def export_bundle(self, target: str | None = None, reason: str = "manual") -> Path:
        """Create a portable, checksummed ZIP of all persisted Show Network data."""
        self.root.mkdir(parents=True, exist_ok=True)
        stamp = self._stamp()
        destination = Path(target).expanduser() if target else self.root / f"show_network_config_{stamp}.zip"
        if not destination.is_absolute():
            destination = self.root / destination
        destination = destination.resolve()
        try:
            destination.relative_to(self.root.resolve())
        except ValueError as err:
            raise ValueError("Configuration backup target must remain inside show_network_backups") from err

        files = self._present_files()
        manifest_files = []
        for src in files:
            manifest_files.append({"name": src.name, "bytes": src.stat().st_size, "sha256": self._sha256(src)})
        manifest = {
            "format": self.FORMAT,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "reason": str(reason)[:80],
            "secrets_included": False,
            "files": manifest_files,
        }
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".show-network-config-", suffix=".zip", dir=destination.parent)
        os.close(fd)
        tmp = Path(tmp_name)
        try:
            with ZipFile(tmp, "w", ZIP_DEFLATED) as zf:
                zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
                for src in files:
                    zf.write(src, arcname=f"config/{src.name}")
            tmp.replace(destination)
            self._last_backup_success = datetime.now(timezone.utc).isoformat()
            self._last_backup_error = None
            self._last_backup_path = str(destination)
            self.prune()
            return destination
        except Exception as err:
            self._last_backup_error = str(err)[:300]
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                logging.getLogger(__name__).debug('Non-fatal error in %s', __name__, exc_info=True)
            raise

    def inspect_bundle(self, source: str) -> dict:
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        try:
            with ZipFile(path, "r") as zf:
                names = set(zf.namelist())
                if "manifest.json" not in names:
                    raise ValueError("Missing Show Network backup manifest")
                manifest = json.loads(zf.read("manifest.json"))
                if manifest.get("format") != self.FORMAT:
                    raise ValueError("Unsupported Show Network backup format")
                rows = manifest.get("files")
                if not isinstance(rows, list):
                    raise ValueError("Invalid backup manifest file list")
                allowed = set(self.FILES)
                checked = []
                for row in rows:
                    name = str(row.get("name", ""))
                    if name not in allowed or Path(name).name != name:
                        raise ValueError(f"Backup contains unsupported file: {name}")
                    member = f"config/{name}"
                    if member not in names:
                        raise ValueError(f"Backup is incomplete: {name}")
                    payload = zf.read(member)
                    digest = hashlib.sha256(payload).hexdigest()
                    if digest != str(row.get("sha256", "")):
                        raise ValueError(f"Checksum mismatch: {name}")
                    if len(payload) != int(row.get("bytes", -1)):
                        raise ValueError(f"Size mismatch: {name}")
                    checked.append({"name": name, "bytes": len(payload), "sha256": digest})
                return {"path": str(path), "created_at": manifest.get("created_at"), "files": checked, "file_count": len(checked)}
        except BadZipFile as err:
            raise ValueError("Invalid ZIP backup") from err

    def restore_bundle(self, source: str) -> dict:
        """Validate completely, then atomically replace persisted config files.

        A pre-restore rollback point is created first.  Files not present in the
        bundle are left untouched, which makes older bundles forward-compatible.
        """
        path = Path(source).expanduser().resolve()
        try:
            path.relative_to(self.root.resolve())
        except ValueError as err:
            raise ValueError("Restore source must be inside show_network_backups") from err
        info = self.inspect_bundle(str(path))
        rollback = self.backup("pre_restore")
        staged_dir = Path(tempfile.mkdtemp(prefix=".show-network-restore-", dir=self.config_dir))
        replaced: list[str] = []
        try:
            with ZipFile(path, "r") as zf:
                for row in info["files"]:
                    name = row["name"]
                    payload = zf.read(f"config/{name}")
                    staged = staged_dir / name
                    staged.write_bytes(payload)
                for row in info["files"]:
                    name = row["name"]
                    staged = staged_dir / name
                    target = self.config_dir / name
                    os.replace(staged, target)
                    replaced.append(name)
            self._last_restore_success = datetime.now(timezone.utc).isoformat()
            self._last_restore_error = None
            self._last_restore_path = str(path)
            return {**info, "restored": replaced, "rollback": str(rollback) if rollback else None, "restart_required": True}
        except Exception as err:
            self._last_restore_error = str(err)[:300]
            raise
        finally:
            shutil.rmtree(staged_dir, ignore_errors=True)

    def prune(self) -> None:
        if not self.root.exists():
            return
        dirs = sorted((p for p in self.root.iterdir() if p.is_dir() and not p.name.startswith(".")), key=lambda p: p.name, reverse=True)
        for old in dirs[self.keep:]:
            shutil.rmtree(old, ignore_errors=True)
        bundles = sorted(self.root.glob("show_network_config_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in bundles[self.keep:]:
            try:
                old.unlink()
            except OSError:
                logging.getLogger(__name__).debug('Non-fatal error in %s', __name__, exc_info=True)

    def status(self) -> dict:
        present = self._present_files()
        backups = []
        if self.root.exists():
            try:
                backups = sorted(
                    [p for p in self.root.iterdir() if (p.is_dir() and not p.name.startswith(".")) or p.name.startswith("show_network_config_")],
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )[: self.keep]
            except OSError:
                backups = []
        return {
            "format": self.FORMAT,
            "files_known": len(self.FILES),
            "files_present": len(present),
            "present_files": [p.name for p in present],
            "backup_count": len(backups),
            "backups": [{"name": p.name, "path": str(p), "bytes": p.stat().st_size if p.is_file() else None} for p in backups],
            "last_backup_success": self._last_backup_success,
            "last_backup_error": self._last_backup_error,
            "last_backup_path": self._last_backup_path,
            "last_restore_success": self._last_restore_success,
            "last_restore_error": self._last_restore_error,
            "last_restore_path": self._last_restore_path,
            "portable_secrets_included": False,
        }

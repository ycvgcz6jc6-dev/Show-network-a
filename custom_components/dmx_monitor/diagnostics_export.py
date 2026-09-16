"""Redacted support-bundle exporter for Show Network."""
from __future__ import annotations

import json
import os
import platform
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from .security import redact


class DiagnosticsExporter:
    FORMAT = "show-network-diagnostics-v1"

    def __init__(self, config_dir: str) -> None:
        self.config_dir = Path(config_dir).resolve()
        self.root = self.config_dir / "show_network_diagnostics"
        self.last_success: str | None = None
        self.last_error: str | None = None
        self.last_path: str | None = None

    @staticmethod
    def _safe(value: Any) -> Any:
        try:
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            if isinstance(value, dict):
                return {str(k): DiagnosticsExporter._safe(v) for k, v in value.items()}
            if isinstance(value, (list, tuple, set)):
                return [DiagnosticsExporter._safe(v) for v in value]
            return str(value)

    def export(self, snapshot: dict[str, Any], *, config_status: dict[str, Any], archive_status: dict[str, Any], resources: list[dict[str, Any]] | None = None) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = self.root / f"show_network_diagnostics_{stamp}.zip"
        fd, tmp_name = tempfile.mkstemp(prefix=".show-network-diag-", suffix=".zip", dir=self.root)
        os.close(fd)
        tmp = Path(tmp_name)
        # Explicitly omit high-volume DMX payloads and any known credential fields.
        bounded = dict(snapshot)
        bounded.pop("dmx_payloads", None)
        bounded.pop("raw_dmx", None)
        payload = redact(self._safe(bounded))
        manifest = {
            "format": self.FORMAT,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "contains_credentials": False,
        }
        try:
            with ZipFile(tmp, "w", ZIP_DEFLATED) as zf:
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))
                zf.writestr("runtime_snapshot.json", json.dumps(payload, ensure_ascii=False, indent=2))
                zf.writestr("persistence_status.json", json.dumps(redact(config_status), ensure_ascii=False, indent=2))
                zf.writestr("archive_status.json", json.dumps(redact(archive_status), ensure_ascii=False, indent=2))
                zf.writestr("resources.json", json.dumps(redact(resources or []), ensure_ascii=False, indent=2))
            tmp.replace(destination)
            self.last_success = datetime.now(timezone.utc).isoformat()
            self.last_error = None
            self.last_path = str(destination)
            self._prune(5)
            return destination
        except Exception as err:
            self.last_error = str(err)[:300]
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def _prune(self, keep: int) -> None:
        files = sorted(self.root.glob("show_network_diagnostics_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[max(1, keep):]:
            try:
                old.unlink()
            except OSError:
                pass

    def status(self) -> dict[str, Any]:
        return {"format": self.FORMAT, "last_success": self.last_success, "last_error": self.last_error, "last_path": self.last_path}

from __future__ import annotations
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

class ConfigBackupManager:
    """Small, atomic, rotating backup store for user-created Show Network data."""
    FILES = ("show_network_dmx_ha_mappings.json", "show_network_dmx_ha_zones.json", "show_network_rules.json")
    def __init__(self, config_dir: str, keep: int = 10) -> None:
        self.config_dir = Path(config_dir)
        self.root = self.config_dir / "show_network_backups"
        self.keep = max(1, int(keep))

    def backup(self, reason: str = "scheduled") -> Path | None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = self.root / stamp
        target.mkdir(parents=True, exist_ok=True)
        copied = False
        for name in self.FILES:
            src = self.config_dir / name
            if src.exists() and src.is_file():
                shutil.copy2(src, target / name)
                copied = True
        if not copied:
            try: target.rmdir()
            except OSError: pass
            return None
        (target / "metadata.json").write_text(json.dumps({"reason": reason, "created_at": stamp}, indent=2), encoding="utf-8")
        self.prune()
        return target

    def prune(self) -> None:
        dirs = sorted((p for p in self.root.glob("*") if p.is_dir()), reverse=True)
        for old in dirs[self.keep:]:
            shutil.rmtree(old, ignore_errors=True)

from __future__ import annotations
import json
from pathlib import Path
from .dmx_ha_mapping import DmxHAMapping

class DmxHAMappingStore:
    def __init__(self, hass_config_path: str):
        self.path = Path(hass_config_path) / "show_network_dmx_ha_mappings.json"
        self._last_payload: str | None = None

    def load(self):
        if not self.path.exists(): return []
        try:
            raw_text = self.path.read_text(encoding="utf-8")
            self._last_payload = raw_text
            raw=json.loads(raw_text)
        except (OSError, ValueError, TypeError): return []
        out=[]
        for d in raw if isinstance(raw,list) else []:
            try:
                d=dict(d); d["channels"]=tuple(d.get("channels",[])); out.append(DmxHAMapping(**d))
            except (TypeError, ValueError): pass
        return out

    def save(self, mappings):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        raw=json.dumps([m.snapshot() for m in mappings], ensure_ascii=False, indent=2)
        if raw == self._last_payload and self.path.exists():
            return
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(raw, encoding="utf-8")
        tmp.replace(self.path)
        self._last_payload = raw

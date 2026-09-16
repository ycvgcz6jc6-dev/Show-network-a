"""Unified receive-only OSC/MIDI control mapping runtime."""
from __future__ import annotations
from dataclasses import asdict
import json
from pathlib import Path
from .osc_mapping import Mapping, MappingEngine

class ControlMappingStore:
    def __init__(self, path: str): self.path=Path(path)
    def load(self):
        if not self.path.exists(): return []
        try: return json.loads(self.path.read_text())
        except Exception: return []
    def save(self, mappings):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp=self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(mappings, indent=2, ensure_ascii=False))
        tmp.replace(self.path)

def midi_address(message):
    ch=(message.channel if message.channel is not None else 0)+1
    if message.message_type=="control_change" and len(message.data)>=2: return f"midi/cc/{ch}/{message.data[0]}"
    if message.message_type in ("note_on","note_off") and message.data: return f"midi/note/{ch}/{message.data[0]}"
    if message.message_type=="pitchwheel": return f"midi/pitch/{ch}"
    return None

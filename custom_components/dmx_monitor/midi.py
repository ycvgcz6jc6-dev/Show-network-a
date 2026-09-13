"""Receive-only MIDI input foundation.

MIDI IN is treated as another CONTROL source alongside OSC. The module is
transport-agnostic: a future platform adapter can use Mido/RtMidi or an
available system MIDI backend. No MIDI OUT is implemented here.
"""
from __future__ import annotations
from dataclasses import dataclass
from time import monotonic

@dataclass
class MIDIMessage:
    message_type: str
    channel: int | None
    data: tuple[int,...]
    source: str | None
    timestamp: float

class MIDILearnSession:
    def __init__(self, max_controls=128):
        self.active=False
        self.samples={}
        self.max_controls=max_controls

    def start(self): self.active=True
    def stop(self): self.active=False
    def clear(self): self.samples.clear()

    def observe(self, message: MIDIMessage):
        if not self.active: return None
        key=(message.source,message.message_type,message.channel,message.data[0] if message.data else None)
        if key not in self.samples and len(self.samples)>=self.max_controls:
            return None
        item=self.samples.setdefault(key,{"count":0,"last":None,"min":None,"max":None})
        item["count"]+=1
        item["last"]=message.data
        if message.message_type in ("control_change","pitchwheel") and message.data:
            value=message.data[-1]
            item["min"]=value if item["min"] is None else min(item["min"],value)
            item["max"]=value if item["max"] is None else max(item["max"],value)
        return item

def normalize_control_change(channel, controller, value, source=None):
    return MIDIMessage("control_change",channel,(controller,value),source,monotonic())

def normalize_note(channel, note, velocity, source=None, on=True):
    return MIDIMessage("note_on" if on else "note_off",channel,(note,velocity),source,monotonic())

def normalize_pitchwheel(channel, value, source=None):
    return MIDIMessage("pitchwheel",channel,(value,),source,monotonic())

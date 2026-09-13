"""OSC Learn mode.

Learn mode observes incoming OSC packets and proposes mappings. It never
transmits anything and never executes a learned mapping automatically.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import deque
from time import monotonic

@dataclass
class LearnedOSC:
    address: str
    value_type: str
    sample_value: object
    min_value: float | None
    max_value: float | None
    count: int
    source_ip: str | None
    last_seen: float

class OSCLearnSession:
    def __init__(self, max_addresses=64):
        self.max_addresses=max_addresses
        self.samples={}
        self.active=False

    def start(self):
        self.active=True

    def stop(self):
        self.active=False

    def clear(self):
        self.samples.clear()

    def observe(self,address,value,source_ip=None):
        if not self.active or not address:
            return None
        kind=self._type_name(value)
        item=self.samples.get(address)
        now=monotonic()
        if item is None:
            if len(self.samples)>=self.max_addresses:
                return None
            numeric=isinstance(value,(int,float)) and not isinstance(value,bool)
            item=LearnedOSC(
                address=address,value_type=kind,sample_value=value,
                min_value=float(value) if numeric else None,
                max_value=float(value) if numeric else None,
                count=0,source_ip=source_ip,last_seen=now
            )
            self.samples[address]=item
        else:
            item.count+=1
            item.last_seen=now
            if source_ip: item.source_ip=source_ip
            if isinstance(value,(int,float)) and not isinstance(value,bool):
                item.min_value=min(item.min_value,float(value))
                item.max_value=max(item.max_value,float(value))
        item.count=max(item.count,1)
        return item

    @staticmethod
    def _type_name(value):
        if isinstance(value,bool): return "bool"
        if isinstance(value,int): return "int"
        if isinstance(value,float): return "float"
        if isinstance(value,str): return "string"
        return type(value).__name__

    def suggestions(self):
        out=[]
        for item in self.samples.values():
            destination="input_number"
            attribute="value"
            if item.value_type=="bool":
                destination="switch"; attribute="turn_on"
            elif item.address.lower().endswith(("color","rgb")):
                destination="light"; attribute="rgb_color"
            elif "brightness" in item.address.lower() or "dimmer" in item.address.lower():
                destination="light"; attribute="brightness"
            out.append({
                "address":item.address,
                "value_type":item.value_type,
                "observed_min":item.min_value,
                "observed_max":item.max_value,
                "suggested_destination":destination,
                "suggested_attribute":attribute,
                "source_ip":item.source_ip,
                "samples":item.count,
            })
        return out

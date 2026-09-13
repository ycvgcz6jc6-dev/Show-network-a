"""Receive-only OSC input foundation with optional Learn mode."""
from __future__ import annotations
import asyncio
import struct
from .osc_learn import OSCLearnSession, LearnedOSC
from .security import ip_allowed, normalize_ip_allowlist

class OSCMessage:
    def __init__(self,address,values,source):
        self.address=address; self.values=values; self.source=source

def parse_basic_message(data: bytes):
    def read_string(offset):
        end=data.index(b"\0",offset)
        raw=data[offset:end].decode("utf-8")
        return raw,(end//4+1)*4
    address,off=read_string(0)
    tags,off=read_string(off)
    if not tags.startswith(","): raise ValueError("invalid OSC type tag")
    values=[]
    for tag in tags[1:]:
        if tag=="f": values.append(struct.unpack(">f",data[off:off+4])[0]); off+=4
        elif tag=="i": values.append(struct.unpack(">i",data[off:off+4])[0]); off+=4
        elif tag=="h": values.append(struct.unpack(">q",data[off:off+8])[0]); off+=8
        elif tag=="d": values.append(struct.unpack(">d",data[off:off+8])[0]); off+=8
        elif tag=="s": value,off=read_string(off); values.append(value)
        elif tag in ("T","F","N","I"): values.append({"T":True,"F":False,"N":None,"I":float("inf")}[tag])
        else: raise ValueError(f"unsupported OSC type: {tag}")
    return address,tuple(values)

class OSCReceiver:
    def __init__(self,host="0.0.0.0",port=8000,learn=None,callback=None,allowed_sources=None):
        self.host=host; self.port=port; self.transport=None; self.messages=0
        self.learn=learn
        self.callback=callback
        self.allowed_sources=normalize_ip_allowlist(allowed_sources)
        self.rejected_messages=0

    async def start(self):
        loop=asyncio.get_running_loop()
        self.transport,_=await loop.create_datagram_endpoint(
            lambda:_OSCProtocol(self),local_addr=(self.host,self.port)
        )

    async def stop(self):
        if self.transport: self.transport.close(); self.transport=None

    def handle(self,data,addr):
        if not ip_allowed(addr[0], self.allowed_sources):
            self.rejected_messages += 1
            return None
        address,values=parse_basic_message(data)
        self.messages+=1
        message = OSCMessage(address,values,addr)
        if self.learn:
            for value in values:
                self.learn.observe(address,value,addr[0])
        if self.callback:
            result = self.callback(message)
            if asyncio.iscoroutine(result):
                asyncio.create_task(result, name="show-network-osc-callback")
        return message

class _OSCProtocol(asyncio.DatagramProtocol):
    def __init__(self,owner): self.owner=owner
    def datagram_received(self,data,addr):
        try:self.owner.handle(data,addr)
        except Exception:pass

"""Minimal read-only SNMPv1 GET client used for GigaCore telemetry.

No SET, WALK or configuration operation is implemented intentionally.
"""
from __future__ import annotations
import asyncio
import random
import socket
from typing import Optional


def _len(n: int) -> bytes:
    if n < 128:
        return bytes([n])
    b = n.to_bytes((n.bit_length()+7)//8, "big")
    return bytes([0x80 | len(b)]) + b

def _tlv(tag: int, payload: bytes) -> bytes:
    return bytes([tag]) + _len(len(payload)) + payload

def _int(n: int) -> bytes:
    if n == 0: return _tlv(0x02, b"\x00")
    length=max(1,(n.bit_length()+7)//8)
    b=n.to_bytes(length,"big",signed=False)
    if b[0]&0x80: b=b"\x00"+b
    return _tlv(0x02,b)

def _oid(oid: str) -> bytes:
    parts=[int(x) for x in oid.split('.') if x]
    if len(parts)<2: raise ValueError("invalid OID")
    out=bytes([40*parts[0]+parts[1]])
    for x in parts[2:]:
        chunks=[x&0x7f]; x >>= 7
        while x:
            chunks.append(x&0x7f); x >>= 7
        for i,v in enumerate(reversed(chunks)):
            out += bytes([v | (0x80 if i < len(chunks)-1 else 0)])
    return _tlv(0x06,out)

def _null_oid(oid: str) -> bytes:
    return _tlv(0x30, _oid(oid)+_tlv(0x05,b""))

def build_get(oid: str, community: str, request_id: int) -> bytes:
    vb=_null_oid(oid)
    pdu=_tlv(0xa0, _int(request_id)+_int(0)+_int(0)+_tlv(0x30,vb))
    return _tlv(0x30, _tlv(0x02,b"\x00") + _tlv(0x04,community.encode()) + pdu)

def _read_len(data: bytes, pos: int):
    n=data[pos]; pos+=1
    if n<128: return n,pos
    k=n&0x7f
    return int.from_bytes(data[pos:pos+k],"big"),pos+k

def _read_tlv(data: bytes,pos: int):
    tag=data[pos]; pos+=1; n,pos=_read_len(data,pos); return tag,data[pos:pos+n],pos+n

def parse_response(data: bytes, request_id: int) -> Optional[object]:
    try:
        _,msg,_=_read_tlv(data,0); pos=0
        _,_,pos=_read_tlv(msg,pos)  # version
        _,_,pos=_read_tlv(msg,pos)  # community
        _,pdu,pos=_read_tlv(msg,pos); p=0
        _,rid,p=_read_tlv(pdu,p)
        if int.from_bytes(rid,'big',signed=True) != request_id:return None
        _,err,p=_read_tlv(pdu,p)
        if int.from_bytes(err,'big',signed=True) != 0:return None
        _,_,p=_read_tlv(pdu,p)  # error index
        _,vbl,_=_read_tlv(pdu,p); q=0; _,vb,q=_read_tlv(vbl,q)
        v=0; _,_,v=_read_tlv(vb,v)  # returned OID
        tag,raw,_=_read_tlv(vb,v)
        if tag == 0x04:return raw.decode("utf-8",errors="replace")
        if tag == 0x02:return int.from_bytes(raw,'big',signed=True)
        if tag in (0x41,0x42,0x43,0x46):return int.from_bytes(raw,'big',signed=False)
        if tag == 0x06:
            if not raw:return None
            first=raw[0];parts=[first//40,first%40];current=0
            for byte in raw[1:]:
                current=(current<<7)|(byte&0x7f)
                if not (byte&0x80):parts.append(current);current=0
            return ".".join(str(x) for x in parts)
    except (IndexError,ValueError):
        return None
    return None

async def async_get(host: str, community: str, oid: str, timeout: float=1.5) -> Optional[object]:
    request_id=random.randint(1,2_000_000_000)
    packet=build_get(oid,community,request_id)
    loop=asyncio.get_running_loop()
    def recv():
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
            s.settimeout(timeout); s.sendto(packet,(host,161)); return s.recvfrom(4096)[0]
    try:
        data=await loop.run_in_executor(None,recv)
        return parse_response(data,request_id)
    except (OSError, asyncio.TimeoutError):
        return None

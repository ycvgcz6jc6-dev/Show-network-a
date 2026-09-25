"""Small read-only SNMPv1 client used by Show Network discovery/telemetry.

Only GET and GETNEXT are implemented.  No SET operation exists in this module.
GETNEXT is used for bounded standard-MIB walks so real ifIndex values can be
observed instead of assuming ports are numbered 1..N.
"""
from __future__ import annotations
import asyncio
import random
import socket
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

# NOTE (stability fix): every SNMP call in this project funnels through
# _async_request() below. It used to run its blocking socket recv() on
# Home Assistant's SHARED default executor (run_in_executor(None, ...)).
# With several configured switches/amplifiers that are unreachable (wrong
# IP, powered off, etc.), each one ties up a shared-pool worker for up to
# its own timeout (typically 0.7-0.9s) before failing -- with enough such
# devices probed concurrently (see runtime/setup.py's vendor discovery,
# which gathers every switch's telemetry at once every 180s), this can
# starve Home Assistant's shared pool of workers for unrelated core
# operations, a plausible contributor to reports of WebSocket ping/pong
# timeouts and DMX reception instability that had no other clear cause.
# A small dedicated pool means Show Network's own network probing can
# never compete with Home Assistant's core executor usage, no matter how
# many configured devices are unreachable.
_SNMP_EXECUTOR = ThreadPoolExecutor(max_workers=16, thread_name_prefix="show_network_snmp")


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

def build_request(oid: str, community: str, request_id: int, *, get_next: bool=False) -> bytes:
    vb=_null_oid(oid)
    pdu_tag = 0xA1 if get_next else 0xA0
    pdu=_tlv(pdu_tag, _int(request_id)+_int(0)+_int(0)+_tlv(0x30,vb))
    return _tlv(0x30, _tlv(0x02,b"\x00") + _tlv(0x04,community.encode()) + pdu)

def build_get(oid: str, community: str, request_id: int) -> bytes:
    return build_request(oid, community, request_id, get_next=False)

def _read_len(data: bytes, pos: int):
    n=data[pos]; pos+=1
    if n<128: return n,pos
    k=n&0x7f
    return int.from_bytes(data[pos:pos+k],"big"),pos+k

def _read_tlv(data: bytes,pos: int):
    tag=data[pos]; pos+=1; n,pos=_read_len(data,pos); return tag,data[pos:pos+n],pos+n

def _decode_oid(raw: bytes) -> str | None:
    if not raw: return None
    first=raw[0]; parts=[first//40, first%40]; current=0
    for byte in raw[1:]:
        current=(current<<7)|(byte&0x7f)
        if not (byte&0x80): parts.append(current); current=0
    return ".".join(str(x) for x in parts)

def _decode_value(tag: int, raw: bytes):
    if tag == 0x04:return raw.decode("utf-8",errors="replace")
    if tag == 0x02:return int.from_bytes(raw,'big',signed=True)
    if tag in (0x41,0x42,0x43,0x46):return int.from_bytes(raw,'big',signed=False)
    if tag == 0x06:return _decode_oid(raw)
    if tag in (0x80,0x81,0x82): return None  # noSuchObject/noSuchInstance/endOfMibView
    return raw.hex()

def parse_response_varbind(data: bytes, request_id: int) -> Optional[tuple[str, object]]:
    try:
        _,msg,_=_read_tlv(data,0); pos=0
        _,_,pos=_read_tlv(msg,pos)
        _,_,pos=_read_tlv(msg,pos)
        _,pdu,pos=_read_tlv(msg,pos); p=0
        _,rid,p=_read_tlv(pdu,p)
        if int.from_bytes(rid,'big',signed=True) != request_id:return None
        _,err,p=_read_tlv(pdu,p)
        if int.from_bytes(err,'big',signed=True) != 0:return None
        _,_,p=_read_tlv(pdu,p)
        _,vbl,_=_read_tlv(pdu,p); q=0; _,vb,q=_read_tlv(vbl,q)
        v=0; _,returned_oid_raw,v=_read_tlv(vb,v)
        returned_oid=_decode_oid(returned_oid_raw)
        tag,raw,_=_read_tlv(vb,v)
        if not returned_oid:return None
        return returned_oid, _decode_value(tag,raw)
    except (IndexError,ValueError):
        return None

def parse_response(data: bytes, request_id: int) -> Optional[object]:
    item=parse_response_varbind(data, request_id)
    return item[1] if item else None

async def _async_request(host: str, community: str, oid: str, *, timeout: float=1.5,
                         source_ip: str | None=None, get_next: bool=False):
    request_id=random.randint(1,2_000_000_000)
    packet=build_request(oid,community,request_id,get_next=get_next)
    loop=asyncio.get_running_loop()
    def recv():
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
            s.settimeout(timeout)
            if source_ip:
                s.bind((source_ip,0))
            s.sendto(packet,(host,161))
            return s.recvfrom(4096)[0]
    try:
        data=await loop.run_in_executor(_SNMP_EXECUTOR,recv)
        return parse_response_varbind(data,request_id)
    except (OSError, asyncio.TimeoutError, TimeoutError):
        return None

async def async_get(host: str, community: str, oid: str, timeout: float=1.5,
                    source_ip: str | None=None) -> Optional[object]:
    item=await _async_request(host,community,oid,timeout=timeout,source_ip=source_ip,get_next=False)
    return item[1] if item else None

async def async_get_next(host: str, community: str, oid: str, timeout: float=1.5,
                         source_ip: str | None=None) -> Optional[tuple[str, object]]:
    return await _async_request(host,community,oid,timeout=timeout,source_ip=source_ip,get_next=True)

async def async_walk(host: str, community: str, base_oid: str, *, timeout: float=1.0,
                     source_ip: str | None=None, max_rows: int=128) -> list[tuple[str, object]]:
    """Bounded read-only SNMPv1 GETNEXT walk under ``base_oid``."""
    base=base_oid.strip('.')
    current=base
    rows=[]
    seen=set()
    for _ in range(max(0, int(max_rows))):
        item=await async_get_next(host,community,current,timeout=timeout,source_ip=source_ip)
        if not item: break
        oid,value=item
        if oid in seen or not (oid == base or oid.startswith(base+'.')): break
        seen.add(oid); rows.append(item); current=oid
    return rows

def index_suffix(oid: str, base: str) -> str | None:
    """The trailing index portion of a walked table OID (everything after
    ``base``), or None if ``oid`` isn't actually under ``base`` at all (a
    walk can run one step past its own subtree before async_walk's own
    boundary check stops it). Shared by every module that walks an SNMP
    table -- switch_port_telemetry.py (IF-MIB, single ifIndex),
    lldp_discovery.py (LLDP-MIB's composite index), switch_temperature.py
    (ENTITY-SENSOR-MIB) -- kept here rather than in any one of them to
    avoid a circular import between modules that both need it."""
    base = base.strip('.')
    if oid == base or not oid.startswith(base + '.'):
        return None
    return oid[len(base) + 1:]

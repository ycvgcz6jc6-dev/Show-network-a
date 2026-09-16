"""Minimal, dependency-free SNMPv2c GET client over raw UDP.

This project declares no third-party SNMP library in manifest.json, and
CHANGELOG.md documents fixes to "SNMP BER request encoding and response
value parsing" -- both point at a hand-rolled ASN.1 BER encoder/decoder
rather than a library such as pysnmp. This module reconstructs that
approach: it only implements exactly what the rest of the codebase needs
(a single-OID SNMP GET request/response), not a general SNMP stack.

Only SNMP GET is implemented. GETNEXT/GETBULK (needed to walk a table such
as ifTable or lldpRemTable) are intentionally out of scope here; a future
topology/table-walking module should add them separately rather than
overload this module's responsibility.
"""
from __future__ import annotations

import asyncio
import logging
import random
import socket
from typing import Any

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 161
DEFAULT_TIMEOUT_S = 2.0
DEFAULT_VERSION = 1  # SNMP message version field: 0 = v1, 1 = v2c, 3 = v3.

# ASN.1 / SNMP tag bytes actually needed for a GET request/response.
_TAG_INTEGER = 0x02
_TAG_OCTET_STRING = 0x04
_TAG_NULL = 0x05
_TAG_OBJECT_IDENTIFIER = 0x06
_TAG_SEQUENCE = 0x30
_TAG_IP_ADDRESS = 0x40
_TAG_COUNTER32 = 0x41
_TAG_GAUGE32 = 0x42
_TAG_TIME_TICKS = 0x43
_TAG_OPAQUE = 0x44
_TAG_COUNTER64 = 0x46
_TAG_NO_SUCH_OBJECT = 0x80
_TAG_NO_SUCH_INSTANCE = 0x81
_TAG_END_OF_MIB_VIEW = 0x82
_TAG_GET_REQUEST_PDU = 0xA0
_TAG_GET_NEXT_REQUEST_PDU = 0xA1
_TAG_GET_RESPONSE_PDU = 0xA2

_EXCEPTION_TAGS = {
    _TAG_NO_SUCH_OBJECT: "noSuchObject",
    _TAG_NO_SUCH_INSTANCE: "noSuchInstance",
    _TAG_END_OF_MIB_VIEW: "endOfMibView",
}


class SNMPError(Exception):
    """Base error for anything that goes wrong talking SNMP to a host."""


class SNMPTimeoutError(SNMPError):
    """No response was received within the configured timeout."""


class SNMPResponseError(SNMPError):
    """The agent replied but with an error-status or an exception value."""


# ---------------------------------------------------------------------------
# BER encoding
# ---------------------------------------------------------------------------

def _encode_length(n: int) -> bytes:
    if n < 0x80:
        return bytes((n,))
    encoded = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes((0x80 | len(encoded),)) + encoded


def _encode_tlv(tag: int, value: bytes) -> bytes:
    return bytes((tag,)) + _encode_length(len(value)) + value


def _encode_integer(value: int) -> bytes:
    if value == 0:
        body = b"\x00"
    else:
        length = max(1, (value.bit_length() + 8) // 8)
        body = value.to_bytes(length, "big", signed=True)
        # Trim redundant leading 0x00/0xFF bytes while keeping the sign correct.
        while len(body) > 1 and (
            (body[0] == 0x00 and body[1] & 0x80 == 0)
            or (body[0] == 0xFF and body[1] & 0x80 != 0)
        ):
            body = body[1:]
    return _encode_tlv(_TAG_INTEGER, body)


def _encode_octet_string(value: bytes | str) -> bytes:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return _encode_tlv(_TAG_OCTET_STRING, value)


def _encode_null() -> bytes:
    return _encode_tlv(_TAG_NULL, b"")


def _encode_oid(dotted: str) -> bytes:
    parts = [int(p) for p in dotted.strip(".").split(".")]
    if len(parts) < 2:
        raise ValueError(f"OID must have at least two components: {dotted!r}")
    body = bytearray()
    body.append(parts[0] * 40 + parts[1])
    for sub in parts[2:]:
        if sub == 0:
            body.append(0)
            continue
        chunk = []
        n = sub
        while n:
            chunk.append(n & 0x7F)
            n >>= 7
        chunk.reverse()
        for i, byte in enumerate(chunk):
            body.append(byte | 0x80 if i < len(chunk) - 1 else byte)
    return _encode_tlv(_TAG_OBJECT_IDENTIFIER, bytes(body))


def _encode_sequence(children: bytes) -> bytes:
    return _encode_tlv(_TAG_SEQUENCE, children)


def _build_request(community: str, oid: str, request_id: int, version: int, pdu_tag: int) -> bytes:
    varbind = _encode_sequence(_encode_oid(oid) + _encode_null())
    varbind_list = _encode_sequence(varbind)
    pdu_body = (
        _encode_integer(request_id)
        + _encode_integer(0)  # error-status
        + _encode_integer(0)  # error-index
        + varbind_list
    )
    pdu = _encode_tlv(pdu_tag, pdu_body)
    message_body = _encode_integer(version) + _encode_octet_string(community) + pdu
    return _encode_sequence(message_body)


def _build_get_request(community: str, oid: str, request_id: int, version: int) -> bytes:
    return _build_request(community, oid, request_id, version, _TAG_GET_REQUEST_PDU)


def _build_get_next_request(community: str, oid: str, request_id: int, version: int) -> bytes:
    return _build_request(community, oid, request_id, version, _TAG_GET_NEXT_REQUEST_PDU)


# ---------------------------------------------------------------------------
# BER decoding
# ---------------------------------------------------------------------------

def _read_length(data: bytes, offset: int) -> tuple[int, int]:
    if offset >= len(data):
        raise SNMPResponseError("truncated SNMP length")
    first = data[offset]
    if first & 0x80 == 0:
        return first, offset + 1
    n_octets = first & 0x7F
    if n_octets == 0:
        raise SNMPResponseError("indefinite-length BER not supported")
    end = offset + 1 + n_octets
    if end > len(data):
        raise SNMPResponseError("truncated SNMP length octets")
    length = int.from_bytes(data[offset + 1:end], "big")
    return length, end


def _read_tlv(data: bytes, offset: int) -> tuple[int, bytes, int]:
    if offset >= len(data):
        raise SNMPResponseError("truncated SNMP TLV")
    tag = data[offset]
    length, value_start = _read_length(data, offset + 1)
    value_end = value_start + length
    if value_end > len(data):
        raise SNMPResponseError("truncated SNMP TLV value")
    return tag, data[value_start:value_end], value_end


def _decode_value(tag: int, value: bytes) -> Any:
    if tag == _TAG_INTEGER:
        return int.from_bytes(value, "big", signed=True) if value else 0
    if tag in (_TAG_COUNTER32, _TAG_GAUGE32, _TAG_TIME_TICKS, _TAG_COUNTER64):
        return int.from_bytes(value, "big", signed=False) if value else 0
    if tag == _TAG_OCTET_STRING or tag == _TAG_OPAQUE:
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value
    if tag == _TAG_NULL:
        return None
    if tag == _TAG_OBJECT_IDENTIFIER:
        return _decode_oid(value)
    if tag == _TAG_IP_ADDRESS:
        return ".".join(str(b) for b in value) if len(value) == 4 else value.hex()
    if tag in _EXCEPTION_TAGS:
        raise SNMPResponseError(f"agent returned {_EXCEPTION_TAGS[tag]}")
    _LOGGER.debug("Unhandled SNMP value tag 0x%02x, returning raw bytes", tag)
    return value


def _decode_oid(value: bytes) -> str:
    if not value:
        return ""
    first = value[0]
    parts = [first // 40, first % 40]
    n = 0
    for byte in value[1:]:
        n = (n << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(n)
            n = 0
    return ".".join(str(p) for p in parts)


def _parse_response_varbind(data: bytes) -> tuple[str, Any]:
    """Parse a GetResponse-PDU message and return (oid, decoded_value) of its
    single variable-binding. Shared by GET and GETNEXT response parsing."""
    tag, message_body, _ = _read_tlv(data, 0)
    if tag != _TAG_SEQUENCE:
        raise SNMPResponseError("response is not a valid SNMP message")
    _version_tag, _version_value, pos = _read_tlv(message_body, 0)
    _community_tag, _community_value, pos = _read_tlv(message_body, pos)
    pdu_tag, pdu_body, _ = _read_tlv(message_body, pos)
    if pdu_tag != _TAG_GET_RESPONSE_PDU:
        raise SNMPResponseError(f"unexpected PDU tag in response: 0x{pdu_tag:02x}")

    _reqid_tag, _reqid_value, pos = _read_tlv(pdu_body, 0)
    errstatus_tag, errstatus_value, pos = _read_tlv(pdu_body, pos)
    _errindex_tag, _errindex_value, pos = _read_tlv(pdu_body, pos)
    error_status = _decode_value(errstatus_tag, errstatus_value)
    if error_status:
        raise SNMPResponseError(f"agent returned error-status {error_status}")

    varbindlist_tag, varbindlist_body, _ = _read_tlv(pdu_body, pos)
    if varbindlist_tag != _TAG_SEQUENCE:
        raise SNMPResponseError("malformed variable-bindings list")

    varbind_tag, varbind_body, _ = _read_tlv(varbindlist_body, 0)
    if varbind_tag != _TAG_SEQUENCE:
        raise SNMPResponseError("malformed variable-binding")
    oid_tag, oid_value, vpos = _read_tlv(varbind_body, 0)
    if oid_tag != _TAG_OBJECT_IDENTIFIER:
        raise SNMPResponseError("variable-binding does not start with an OID")
    returned_oid = _decode_oid(oid_value)
    value_tag, value_bytes, _ = _read_tlv(varbind_body, vpos)
    return returned_oid, _decode_value(value_tag, value_bytes)


def _parse_get_response(data: bytes, requested_oid: str) -> Any:
    try:
        _oid, value = _parse_response_varbind(data)
    except SNMPResponseError as exc:
        raise SNMPResponseError(f"{exc} (GET {requested_oid})") from exc
    return value


def _parse_get_next_response(data: bytes) -> tuple[str, Any]:
    return _parse_response_varbind(data)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def async_get_next(
    host: str,
    community: str,
    oid: str,
    *,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT_S,
    version: int = DEFAULT_VERSION,
) -> tuple[str, Any]:
    """Perform a single SNMP GETNEXT and return (next_oid, decoded_value).

    Used to walk a table one row at a time: repeatedly calling this with the
    previously-returned OID advances lexicographically through the MIB tree.
    Raises the same exceptions as async_get.
    """
    request_id = random.randint(1, 0x7FFFFFFF)
    packet = _build_get_next_request(community, oid, request_id, version)

    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setblocking(False)
    try:
        await loop.sock_sendto(sock, packet, (host, port))
        try:
            data = await asyncio.wait_for(loop.sock_recv(sock, 4096), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise SNMPTimeoutError(f"no SNMP response from {host}:{port} for GETNEXT {oid}") from exc
        return _parse_get_next_response(data)
    finally:
        sock.close()


async def async_walk(
    host: str,
    community: str,
    base_oid: str,
    *,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT_S,
    version: int = DEFAULT_VERSION,
    max_rows: int = 256,
) -> list[tuple[str, Any]]:
    """Walk every OID under ``base_oid`` via repeated GETNEXT.

    Stops when the returned OID no longer starts with ``base_oid`` (the walk
    left the requested subtree -- the normal, successful end of a walk), when
    ``max_rows`` is reached (a safety bound against a misbehaving agent or an
    unexpectedly huge table), or when a GETNEXT fails (timeout/error), in
    which case whatever was collected so far is returned rather than raising,
    since a partial LLDP/interface table is still useful telemetry and a
    read-only monitoring walk should never crash the caller.
    """
    prefix = base_oid.strip(".") + "."
    results: list[tuple[str, Any]] = []
    current = base_oid
    seen: set[str] = set()
    for _ in range(max_rows):
        try:
            next_oid, value = await async_get_next(host, community, current, port=port, timeout=timeout, version=version)
        except SNMPError as exc:
            _LOGGER.debug("SNMP walk of %s stopped at %s: %s", base_oid, current, exc)
            break
        if not next_oid.startswith(prefix) and next_oid != base_oid:
            break
        if next_oid in seen:
            # Defensive: a misbehaving/looping agent must not hang this walk.
            _LOGGER.debug("SNMP walk of %s saw repeated OID %s, stopping", base_oid, next_oid)
            break
        seen.add(next_oid)
        results.append((next_oid, value))
        current = next_oid
    return results


async def async_get(
    host: str,
    community: str,
    oid: str,
    *,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT_S,
    version: int = DEFAULT_VERSION,
) -> Any:
    """Perform a single read-only SNMP GET and return the decoded value.

    Raises SNMPTimeoutError if no reply arrives in time, or SNMPResponseError
    if the agent replies with an error-status or an exception value
    (noSuchObject/noSuchInstance/endOfMibView -- typically "this OID doesn't
    exist on this device"). Callers in this codebase already wrap concurrent
    calls with ``asyncio.gather(..., return_exceptions=True)``, so raising
    here (rather than returning None) is the correct behaviour: it lets one
    failed OID not affect the others in the same poll cycle.
    """
    request_id = random.randint(1, 0x7FFFFFFF)
    packet = _build_get_request(community, oid, request_id, version)

    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setblocking(False)
    try:
        await loop.sock_sendto(sock, packet, (host, port))
        try:
            data = await asyncio.wait_for(loop.sock_recv(sock, 4096), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise SNMPTimeoutError(f"no SNMP response from {host}:{port} for {oid}") from exc
        return _parse_get_response(data, oid)
    finally:
        sock.close()

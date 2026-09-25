#!/usr/bin/env python3
"""Tiny read-only HTTP bridge for Show Network + LA_avdecc JSON dumps.

SECURITY (audit fix): this bridge previously listened on 0.0.0.0 with no
authentication, letting any machine that could reach the port read the full
AV entity inventory. This revision listens on 127.0.0.1 by default and
requires a shared bearer token (AVDECC_AUTH_TOKEN env var; auto-generated
and logged once at startup if unset). This bridge has no write endpoint, so
the remaining risk after this fix is read-only information disclosure to
whoever holds the token -- still worth protecting, but there is no
equivalent of the RDM bridge's SET-authorization concern here.
"""
from __future__ import annotations
import argparse
import hmac
import json
import logging
import os
import secrets
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger("la_avdecc_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

AUTH_TOKEN = os.getenv("AVDECC_AUTH_TOKEN") or secrets.token_urlsafe(24)
if not os.getenv("AVDECC_AUTH_TOKEN"):
    _LOGGER.warning(
        "AVDECC_AUTH_TOKEN not set -- generated a token for this run (changes "
        "on every restart): %s -- set AVDECC_AUTH_TOKEN to pin it. Clients "
        "must send 'Authorization: Bearer <token>'.", AUTH_TOKEN,
    )


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _first(d: dict[str, Any], *names: str):
    wanted = {n.lower().replace("_", "") for n in names}
    for key, value in d.items():
        if key.lower().replace("_", "") in wanted and value not in (None, ""):
            return value
    return None


def _find_any(root: Any, *names: str):
    for node in _walk(root):
        value = _first(node, *names)
        if value not in (None, ""):
            return value
    return None


def _entity_candidates(payload: Any) -> list[dict[str, Any]]:
    # LA_avdecc serializer layout can evolve. Locate the shallowest dictionaries
    # that actually carry an EntityID rather than hard-coding a private layout.
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node in _walk(payload):
        eid = _first(node, "entity_id", "entityID", "EntityID")
        if eid is None:
            continue
        key = str(eid)
        if key in seen:
            continue
        seen.add(key)
        found.append(node)
    return found


def _list_matching(root: Any, token: str, limit: int = 128) -> list[dict[str, Any]]:
    rows = []
    for node in _walk(root):
        if token in " ".join(str(k).lower() for k in node.keys()):
            rows.append(node)
            if len(rows) >= limit:
                break
    return rows


def normalize_dump(payload: Any, *, mtime: float | None = None) -> dict[str, Any]:
    entities = []
    now = time.time()
    for node in _entity_candidates(payload):
        eid = _first(node, "entity_id", "entityID", "EntityID")
        if eid is None:
            continue
        manufacturer = _find_any(node, "vendor_name", "manufacturer", "vendorName")
        model = _find_any(node, "model_name", "modelName", "model")
        name = _find_any(node, "entity_name", "entityName", "name")
        serial = _find_any(node, "serial_number", "serialNumber")
        firmware = _find_any(node, "firmware_version", "firmwareVersion")
        entity = {
            "entity_id": str(eid),
            "manufacturer": str(manufacturer) if manufacturer else None,
            "model": str(model) if model else None,
            "name": str(name) if name else None,
            "serial": str(serial) if serial else None,
            "firmware": str(firmware) if firmware else None,
            "online": True,
            "last_seen": float(mtime or now),
            "streams": _list_matching(node, "stream", 64),
            "controls": _list_matching(node, "control", 128),
            "clock": {"descriptors": _list_matching(node, "clock", 64)},
            "counters": {"statistics": _list_matching(node, "statistic", 64), "diagnostics": _list_matching(node, "diagnostic", 64)},
        }
        entities.append(entity)
    return {"entities": entities, "source": "L-Acoustics/avdecc", "generated_at": now}


class Handler(BaseHTTPRequestHandler):
    dump_path = Path(os.environ.get("AVDECC_DUMP", "/data/avdecc-network.json"))

    def _json(self, status: int, body: Any):
        data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(data)

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return False
        return hmac.compare_digest(header[len("Bearer "):].strip(), AUTH_TOKEN)

    def do_GET(self):
        if self.path == "/health":
            # No sensitive data here -- left open for monitoring/Show Network reachability checks.
            exists = self.dump_path.exists()
            age = None if not exists else max(0.0, time.time() - self.dump_path.stat().st_mtime)
            return self._json(200 if exists else 503, {"ok": exists, "dump": str(self.dump_path), "age_s": age})
        if not self._authorized():
            return self._json(401, {"error": "unauthorized"})
        if self.path != "/v1/entities":
            return self._json(404, {"error": "not found"})
        try:
            stat = self.dump_path.stat()
            if stat.st_size > 16 * 1024 * 1024:
                raise ValueError("LA_avdecc dump too large")
            payload = json.loads(self.dump_path.read_text(encoding="utf-8"))
            return self._json(200, normalize_dump(payload, mtime=stat.st_mtime))
        except Exception as exc:
            _LOGGER.warning("Could not read/parse AVDECC dump: %s", exc)
            return self._json(503, {"entities": [], "error": "dump unavailable"})

    def log_message(self, fmt, *args):
        print("[bridge] " + (fmt % args), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--dump", default=os.environ.get("AVDECC_DUMP", "/data/avdecc-network.json"))
    args = ap.parse_args()
    Handler.dump_path = Path(args.dump)
    if args.listen == "0.0.0.0":
        _LOGGER.warning("--listen 0.0.0.0: listening on all interfaces. Put this behind a firewall, "
                         "an isolated network, or a TLS-terminating reverse proxy/SSH tunnel.")
    ThreadingHTTPServer((args.listen, args.port), Handler).serve_forever()

if __name__ == "__main__":
    main()

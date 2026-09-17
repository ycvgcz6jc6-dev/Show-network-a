#!/usr/bin/env python3
"""Tiny OLA RDM bridge for Show Network.

Uses OLA's documented command-line utilities. GET polling is safe/read-only.
SET is available only when RDM_ALLOW_SET=1 and only for an explicit allow-list.

SECURITY (audit fix): this bridge previously listened on 0.0.0.0 with no
authentication at all, and its SET endpoint accepted any universe number
regardless of RDM_UNIVERSES -- meaning anyone who could reach the port could
both read the full RDM device inventory and, if RDM_ALLOW_SET=1 was set,
issue RDM writes on a universe the operator never intended to expose. This
revision:
  - binds to 127.0.0.1 by default (set RDM_BIND=0.0.0.0 explicitly to
    expose more broadly -- e.g. from inside a container -- at your own risk;
    put a reverse proxy or SSH tunnel with TLS in front if doing so);
  - requires a shared bearer token on every request (RDM_AUTH_TOKEN env var;
    if unset, one is generated at startup and printed to the log once --
    it rotates on every restart unless you pin it);
  - rejects a SET whose universe is not in RDM_UNIVERSES, closing the exact
    gap the audit found;
  - returns generic error text to the client, logging the real exception
    server-side only.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import logging
import os
import re
import secrets
import subprocess
import time

_LOGGER = logging.getLogger("rdm_ola_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

UNIVERSES = tuple(sorted({int(x) for x in os.getenv("RDM_UNIVERSES", "1").replace(";", ",").split(",") if x.strip().isdigit() and 0 <= int(x) <= 63999}))
ALLOW_SET = os.getenv("RDM_ALLOW_SET", "0") == "1"
ALLOWED_SET_PIDS = {"dmx_start_address", "dmx_personality", "device_label", "identify_device"}
UID_RE = re.compile(r"\b([0-9a-fA-F]{4}:[0-9a-fA-F]{8})\b")
CACHE_TTL = float(os.getenv("RDM_CACHE_TTL", "5"))
_cache = {"at": 0.0, "devices": []}

AUTH_TOKEN = os.getenv("RDM_AUTH_TOKEN") or secrets.token_urlsafe(24)
if not os.getenv("RDM_AUTH_TOKEN"):
    _LOGGER.warning(
        "RDM_AUTH_TOKEN not set -- generated a token for this run (changes on "
        "every restart): %s -- set RDM_AUTH_TOKEN to pin it. Clients must send "
        "'Authorization: Bearer <token>'.", AUTH_TOKEN,
    )


def run(*argv: str, timeout: float = 4.0) -> str:
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or f"exit {p.returncode}").strip())
    return p.stdout


def get_pid(universe: int, uid: str, pid: str) -> str | None:
    try:
        out = run("ola_rdm_get", "--universe", str(universe), "--uid", uid, pid)
    except Exception:
        return None
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    if not lines:
        return None
    text = " ".join(lines)
    return text.split(":", 1)[1].strip() if ":" in text else text


def as_int(text):
    if text is None: return None
    m = re.search(r"(?<![0-9A-Fa-f])(-?\d+)", str(text))
    return int(m.group(1)) if m else None


def scan():
    now = time.time()
    if now - _cache["at"] < CACHE_TTL:
        return _cache["devices"]
    rows=[]
    for universe in UNIVERSES:
        try:
            out=run("ola_rdm_discover", "--universe", str(universe))
        except Exception:
            continue
        for uid in sorted(set(m.group(1).lower() for m in UID_RE.finditer(out))):
            supported = get_pid(universe, uid, "supported_parameters")
            row={
                "uid": uid, "universe": universe, "last_seen": now,
                "source": "OLA",
                "manufacturer_label": get_pid(universe, uid, "manufacturer_label"),
                "model_description": get_pid(universe, uid, "device_model_description"),
                "device_label": get_pid(universe, uid, "device_label"),
                "software_version_label": get_pid(universe, uid, "software_version_label"),
                "dmx_start_address": as_int(get_pid(universe, uid, "dmx_start_address")),
            }
            if supported:
                row["supported_parameters"] = sorted(set(re.findall(r"\(([^)]+)\)", supported)))
            info = get_pid(universe, uid, "device_info")
            if info:
                row["extra"]={"device_info_raw": info}
            rows.append(row)
    _cache.update(at=now, devices=rows)
    return rows


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, obj):
        body=json.dumps(obj, separators=(",", ":")).encode()
        self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return False
        return hmac.compare_digest(header[len("Bearer "):].strip(), AUTH_TOKEN)

    def do_GET(self):
        if self.path == "/health":
            # Health check deliberately does not require auth (no sensitive
            # data) so monitoring tools/Show Network can verify reachability.
            self.send_json(200, {"ok": True, "backend":"OLA", "read_only": not ALLOW_SET, "universes": UNIVERSES}); return
        if not self._authorized():
            self.send_json(401, {"error": "unauthorized"}); return
        if self.path == "/v1/devices":
            try: self.send_json(200, {"devices": scan(), "backend":"OLA", "read_only": not ALLOW_SET})
            except Exception as exc:
                _LOGGER.warning("scan() failed: %s", exc)
                self.send_json(503, {"error": "scan failed"})
            return
        self.send_json(404,{"error":"not found"})

    def do_POST(self):
        if not self._authorized():
            self.send_json(401, {"error": "unauthorized"}); return
        if self.path != "/v1/set": self.send_json(404,{"error":"not found"}); return
        if not ALLOW_SET: self.send_json(403,{"error":"RDM writes disabled"}); return
        try:
            size=min(int(self.headers.get("Content-Length","0")),65536); data=json.loads(self.rfile.read(size) or b"{}")
            uid=str(data["uid"]).lower(); universe=int(data["universe"]); pid=str(data["pid"])
            if not UID_RE.fullmatch(uid): raise ValueError("invalid UID")
            if universe not in UNIVERSES: raise ValueError("universe not in RDM_UNIVERSES allow-list")
            if pid not in ALLOWED_SET_PIDS: raise ValueError("PID not allowed")
            out=run("ola_rdm_set", "--universe", str(universe), "--uid", uid, pid, str(data.get("value","")))
            _cache["at"]=0.0
            self.send_json(200,{"ok":True,"result":out.strip()})
        except (KeyError, ValueError) as exc:
            # Caller-facing validation errors: safe to echo, no internals leaked.
            self.send_json(400,{"error":str(exc)})
        except Exception as exc:
            _LOGGER.warning("SET failed: %s", exc)
            self.send_json(400,{"error":"request failed"})

    def log_message(self, *_): pass

if __name__ == "__main__":
    bind = os.getenv("RDM_BIND", "127.0.0.1")
    port = int(os.getenv("RDM_PORT", "8098"))
    if bind == "0.0.0.0":
        _LOGGER.warning("RDM_BIND=0.0.0.0: listening on all interfaces. Put this behind a firewall, "
                         "an isolated network, or a TLS-terminating reverse proxy/SSH tunnel.")
    ThreadingHTTPServer((bind, port), Handler).serve_forever()

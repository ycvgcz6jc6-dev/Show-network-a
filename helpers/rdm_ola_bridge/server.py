#!/usr/bin/env python3
"""Tiny OLA RDM bridge for Show Network.

Uses OLA's documented command-line utilities. GET polling is safe/read-only.
SET is available only when RDM_ALLOW_SET=1 and only for an explicit allow-list.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json, os, re, subprocess, time

UNIVERSES = tuple(sorted({int(x) for x in os.getenv("RDM_UNIVERSES", "1").replace(";", ",").split(",") if x.strip().isdigit() and 0 <= int(x) <= 63999}))
ALLOW_SET = os.getenv("RDM_ALLOW_SET", "0") == "1"
ALLOWED_SET_PIDS = {"dmx_start_address", "dmx_personality", "device_label", "identify_device"}
UID_RE = re.compile(r"\b([0-9a-fA-F]{4}:[0-9a-fA-F]{8})\b")
CACHE_TTL = float(os.getenv("RDM_CACHE_TTL", "5"))
_cache = {"at": 0.0, "devices": []}


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
    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"ok": True, "backend":"OLA", "read_only": not ALLOW_SET, "universes": UNIVERSES}); return
        if self.path == "/v1/devices":
            try: self.send_json(200, {"devices": scan(), "backend":"OLA", "read_only": not ALLOW_SET})
            except Exception as exc: self.send_json(503, {"error": f"{type(exc).__name__}: {exc}"})
            return
        self.send_json(404,{"error":"not found"})
    def do_POST(self):
        if self.path != "/v1/set": self.send_json(404,{"error":"not found"}); return
        if not ALLOW_SET: self.send_json(403,{"error":"RDM writes disabled"}); return
        try:
            size=min(int(self.headers.get("Content-Length","0")),65536); data=json.loads(self.rfile.read(size) or b"{}")
            uid=str(data["uid"]).lower(); universe=int(data["universe"]); pid=str(data["pid"])
            if not UID_RE.fullmatch(uid): raise ValueError("invalid UID")
            if pid not in ALLOWED_SET_PIDS: raise ValueError("PID not allowed")
            out=run("ola_rdm_set", "--universe", str(universe), "--uid", uid, pid, str(data.get("value","")))
            _cache["at"]=0.0
            self.send_json(200,{"ok":True,"result":out.strip()})
        except Exception as exc: self.send_json(400,{"error":f"{type(exc).__name__}: {exc}"})
    def log_message(self, *_): pass

if __name__ == "__main__":
    ThreadingHTTPServer((os.getenv("RDM_BIND","0.0.0.0"), int(os.getenv("RDM_PORT","8098"))), Handler).serve_forever()

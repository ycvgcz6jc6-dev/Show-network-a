from __future__ import annotations
import asyncio, socket
from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class ProjectorRecord:
    name: str
    host: str
    port: int = 4352
    manufacturer: str | None = None
    model: str | None = None
    power: str | None = None
    input_source: str | None = None
    av_mute: str | None = None
    errors: str | None = None
    lamp_hours: int | None = None
    lamp_status: str | None = None
    temperature_c: float | None = None
    profile: str = 'auto'
    online: bool = False
    last_error: str | None = None

class PJLinkMonitor:
    def __init__(self, projectors: list[dict[str, Any]] | None = None):
        self.records = [ProjectorRecord(name=str(p.get('name') or p.get('host')), host=str(p['host']), port=int(p.get('port',4352)), profile=str(p.get('profile','auto'))) for p in (projectors or []) if p.get('host')]

    @staticmethod
    def _query(host: str, port: int, cmd: str, timeout: float = 2.0) -> str:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            banner=s.recv(256)
            if not banner.startswith(b'PJLINK '): raise ConnectionError('not a PJLink endpoint')
            # Do not guess credentials. Authenticated endpoints are monitorable only if they accept unauthenticated status.
            s.sendall((cmd+'\r').encode('ascii'))
            return s.recv(2048).decode('ascii','replace').strip()

    @classmethod
    def _poll_one(cls, r: ProjectorRecord):
        vals={}
        for key,cmd in [('power','%1POWR ?'),('input_source','%1INPT ?'),('av_mute','%1AVMT ?'),('errors','%1ERST ?'),('lamp','%1LAMP ?'),('manufacturer','%1INF1 ?'),('model','%1NAME ?'),('temperature_c','%1TEMP ?')]:
            try: vals[key]=cls._query(r.host,r.port,cmd)
            except Exception: pass
        if not vals: raise ConnectionError('no PJLink response')
        def payload(v): return v.split('=',1)[1] if '=' in v else None
        p=payload(vals.get('power',''))
        r.power={'0':'off','1':'on','2':'cooling','3':'warming'}.get(p,p)
        r.input_source=payload(vals.get('input_source',''))
        a=payload(vals.get('av_mute','')); r.av_mute={'30':'off','31':'on'}.get(a,a)
        e=payload(vals.get('errors','')); r.errors=e
        l=payload(vals.get('lamp',''))
        if l:
            parts=l.split();
            try:r.lamp_hours=int(parts[0])
            except Exception:pass
            r.lamp_status=' '.join(parts[1:]) or None
        r.manufacturer=payload(vals.get('manufacturer','')) or r.manufacturer
        r.model=payload(vals.get('model','')) or r.model
        t=payload(vals.get('temperature_c',''))
        if t:
            try:
                # PJLink TEMP payloads commonly contain sensor/value pairs; use the first numeric value.
                import re
                m=re.search(r'(-?\d+(?:\.\d+)?)', t)
                if m: r.temperature_c=float(m.group(1))
            except Exception: pass
        r.online=True; r.last_error=None
        return r

    async def async_update(self):
        for r in self.records:
            try: await asyncio.get_running_loop().run_in_executor(None,self._poll_one,r)
            except Exception as e: r.online=False; r.last_error=str(e)

    def snapshot(self): return [asdict(r) for r in self.records]

from __future__ import annotations
import hashlib
import re
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


def _slug(value: object) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value or "").strip()).strip("_")
    return text[:64]


def uid_from_record(record, fallback=None):
    """Stable device identifier; IP/list position are never primary identity."""
    serial = getattr(record, "serial_number", None)
    mac = getattr(record, "mac", None)
    if serial:
        return f"serial_{_slug(serial)}"
    if mac:
        return f"mac_{_slug(str(mac).lower())}"
    configured = getattr(record, "name", None) or fallback or "projector"
    digest = hashlib.sha1(str(configured).encode("utf-8")).hexdigest()[:12]
    return f"configured_{_slug(configured)}_{digest}"


class ProjectorEntity(CoordinatorEntity):
    _attr_has_entity_name = True
    def __init__(self, c, r, uid, suffix):
        super().__init__(c); self.r=r; self._uid=uid; self._attr_unique_id=f"projector_{uid}_{suffix}"; self._attr_name=suffix.replace('_',' ').title()
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, f"projector_{self._uid}")}, "name": self.r.name,
                "manufacturer": self.r.manufacturer or "Projector", "model": self.r.model or self.r.profile or "Projector",
                "configuration_url": f"http://{self.r.host}"}


class ProjectorOnline(ProjectorEntity, BinarySensorEntity):
    def __init__(self,c,r,i): super().__init__(c,r,i,'online')
    @property
    def is_on(self): return self.r.online
    @property
    def extra_state_attributes(self):
        return {'host': self.r.host, 'port': self.r.port, 'profile': self.r.profile,
                'transport': self.r.transport, 'telemetry_source': self.r.telemetry_source,
                'reachable': self.r.reachable, 'valid_telemetry': self.r.valid_telemetry,
                'stale': self.r.stale, 'telemetry_age_s': self.r.telemetry_age_s,
                'source_interface': self.r.source_interface, 'last_error': self.r.last_error}


class ProjectorState(ProjectorEntity, SensorEntity):
    def __init__(self,c,r,i,key): self.key=key; super().__init__(c,r,i,key)
    @property
    def native_value(self): return getattr(self.r,self.key,None)
    @property
    def extra_state_attributes(self):
        attrs={'host':self.r.host,'port':self.r.port,'manufacturer':self.r.manufacturer,'model':self.r.model,
               'profile':self.r.profile,'transport':self.r.transport,'telemetry_source':self.r.telemetry_source,
               'authenticated':self.r.authenticated,'auth_method':self.r.auth_method,'stale':self.r.stale,
               'telemetry_age_s':self.r.telemetry_age_s,'last_error':self.r.last_error}
        if self.key == 'temperature_c': attrs['temperatures_c']=dict(list(self.r.temperatures_c.items())[:16])
        if self.key == 'power': attrs['fans_rpm']=dict(list(self.r.fans_rpm.items())[:16]); attrs['signal']=self.r.signal
        return attrs


def binary_entities(c):
    return [ProjectorOnline(c, r, uid_from_record(r)) for r in c.projector_monitor.records]


def sensor_entities(c):
    out=[]
    for r in c.projector_monitor.records:
        base=uid_from_record(r)
        for key in ("power","input_source","av_mute","lamp_hours","temperature_c","errors","serial_number","software_version","input_resolution","recommended_resolution","filter_hours"):
            out.append(ProjectorState(c,r,base,key))
    return out

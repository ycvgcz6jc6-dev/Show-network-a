from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN

def uid_from_record(record, fallback=None):
    """Stable local identifier; never uses IP/host as the identifier."""
    serial = getattr(record, "serial", None)
    mac = getattr(record, "mac", None)
    if serial:
        return f"serial_{serial}"
    if mac:
        return f"mac_{mac}"
    return f"configured_{fallback if fallback is not None else record.name}"

class ProjectorEntity(CoordinatorEntity):
    _attr_has_entity_name=True
    def __init__(self,c,r,uid,suffix):
        super().__init__(c); self.r=r; self._uid=uid; self._attr_unique_id=f"projector_{uid}_{suffix}"; self._attr_name=suffix.replace('_',' ').title()
    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, f"projector_{self._uid}") }, "name": self.r.name, "manufacturer": self.r.manufacturer or "Projector", "model": self.r.model or "PJLink", "configuration_url": f"http://{self.r.host}"}

class ProjectorOnline(ProjectorEntity,BinarySensorEntity):
    def __init__(self,c,r,i): super().__init__(c,r,i,'online')
    @property
    def is_on(self): return self.r.online
    @property
    def extra_state_attributes(self): return {'host':self.r.host,'port':self.r.port,'last_error':self.r.last_error}

class ProjectorState(ProjectorEntity,SensorEntity):
    def __init__(self,c,r,i,key): self.key=key; super().__init__(c,r,i,key)
    @property
    def native_value(self): return getattr(self.r,self.key,None)
    @property
    def extra_state_attributes(self): return {'host':self.r.host,'port':self.r.port,'manufacturer':self.r.manufacturer,'model':self.r.model,'profile':self.r.profile,'last_error':self.r.last_error}

def binary_entities(c):
    """Return projector binary-sensor entities for the HA binary_sensor platform."""
    out = []
    for i, r in enumerate(c.projector_monitor.records):
        base = f"{i}_{uid_from_record(r, i)}"
        out.append(ProjectorOnline(c, r, base))
    return out


def sensor_entities(c):
    """Return projector sensor entities for the HA sensor platform."""
    out = []
    for i, r in enumerate(c.projector_monitor.records):
        base = f"{i}_{uid_from_record(r, i)}"
        out.extend([
            ProjectorState(c, r, base, "power"),
            ProjectorState(c, r, base, "input_source"),
            ProjectorState(c, r, base, "av_mute"),
            ProjectorState(c, r, base, "lamp_hours"),
            ProjectorState(c, r, base, "temperature_c"),
            ProjectorState(c, r, base, "errors"),
        ])
    return out

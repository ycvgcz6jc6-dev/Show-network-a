"""ETC equipment catalogue and sensor/diagnostic model.

This module is deliberately a capability catalogue.  Live CEM3 values are
provided separately by the conservative web monitor; this catalogue does not
claim a generic proprietary Net3 telemetry transport. Capabilities carry an
evidence level so the UI can distinguish documented capabilities from live
telemetry and hardware-observed web queries.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ETCSensorDefinition:
    key: str
    label_fr: str
    label_en: str
    unit: str | None = None
    source: str = "documented_capability"
    live_supported: bool = False


ETC_CONSOLES = {
    "eos_apex": "Eos Apex",
    "eos_gio_at5": "Eos Gio @5",
    "eos_gio": "Eos Gio",
    "eos_ion_xe": "Eos Ion Xe",
    "eos_ion": "Eos Ion",
    "eos_element": "Eos Element",
    "eosnomad": "ETCnomad",
}

ETC_POWER = {
    "sensor3_cem3": "Sensor3 / CEM3",
    "sensor3": "Sensor3",
    "cem3": "CEM3",
    "phaseadept": "PhaseAdept",
}

# Fields explicitly useful for a professional diagnostic UI.  Some are
# available as CEM3 error/status information; transport support is kept false
# until a documented passive network/API path is implemented.
ETC_SENSORS = (
    ETCSensorDefinition("cpu_temperature", "Température CPU", "CPU temperature", "°C", "cem3_web_system", True),
    ETCSensorDefinition("phase_x_voltage", "Tension phase X", "Phase X voltage", "V", "cem3_web_system", True),
    ETCSensorDefinition("phase_y_voltage", "Tension phase Y", "Phase Y voltage", "V", "cem3_web_system", True),
    ETCSensorDefinition("phase_z_voltage", "Tension phase Z", "Phase Z voltage", "V", "cem3_web_system", True),
    ETCSensorDefinition("line_frequency", "Fréquence secteur", "Line frequency", "Hz", "cem3_web_system", True),
    ETCSensorDefinition("rack_status", "État rack", "Rack status", None, "cem3_web_system", True),
    ETCSensorDefinition("active_errors", "Erreurs actives", "Active errors", None, "cem3_web_system", True),
    ETCSensorDefinition("software_version", "Version CEM3", "CEM3 software version", None, "cem3_web_system", True),
    ETCSensorDefinition("panic_state", "État Panic", "Panic state", None, "cem3_web_system", True),
    ETCSensorDefinition("circuits", "État circuits", "Circuit status", None, "cem3_web_dimmers", True),
    ETCSensorDefinition("actual_load", "Charge réelle AF", "AF actual load", "A", "documented_capability", False),
    ETCSensorDefinition("recorded_load", "Charge enregistrée AF", "AF recorded load", "A", "documented_capability", False),
)


def sensor_catalog() -> list[dict]:
    return [asdict(sensor) for sensor in ETC_SENSORS]


def profile(model: str | None = None) -> dict:
    return {
        "manufacturer": "ETC",
        "model": model,
        "category": "lighting_control_and_power",
        "console_families": ETC_CONSOLES,
        "power_families": ETC_POWER,
        "protocols": ["sACN", "ETC Net3", "DMX", "RDM", "CEM3 HTTP web interface"],
        "sensors": sensor_catalog(),
        "evidence_policy": "official_documentation_plus_explicit_hardware_observation_for_cem3_web_queries",
    }

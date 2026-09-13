"""ETC equipment catalogue and sensor/diagnostic model.

This module is deliberately a capability catalogue.  It does not pretend to
have a proprietary CEM3/Net3 transport when no public read-only transport has
been established.  Capabilities are exposed with an evidence level so the UI
can distinguish documented capabilities from live telemetry.
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
ETC_SENSORS = tuple(
    ETCSensorDefinition(*row)
    for row in (
        ("cpu_temperature", "Température CPU", "CPU temperature", "°C"),
        ("phase_a_voltage", "Tension phase A", "Phase A voltage", "V"),
        ("phase_b_voltage", "Tension phase B", "Phase B voltage", "V"),
        ("phase_c_voltage", "Tension phase C", "Phase C voltage", "V"),
        ("line_frequency", "Fréquence secteur", "Line frequency", "Hz"),
        ("phase_a_status", "État phase A", "Phase A status"),
        ("phase_b_status", "État phase B", "Phase B status"),
        ("phase_c_status", "État phase C", "Phase C status"),
        ("dmx_port_a_status", "DMX port A", "DMX port A status"),
        ("dmx_port_b_status", "DMX port B", "DMX port B status"),
        ("fan_status", "Ventilateur", "Fan status"),
        ("zero_cross_status", "Zero-cross", "Zero-cross status"),
        ("temperature_sensor_status", "Capteur température", "Temperature sensor status"),
        ("rack_detect_status", "Détection rack", "Rack detect status"),
        ("memory_status", "Mémoire", "Memory status"),
        ("af_card_1_status", "AF Card 1", "AF Card 1 status"),
        ("af_card_2_status", "AF Card 2", "AF Card 2 status"),
        ("af_card_3_status", "AF Card 3", "AF Card 3 status"),
        ("af_card_4_status", "AF Card 4", "AF Card 4 status"),
        ("dmx_error_count", "Erreurs DMX", "DMX error count"),
    )
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
        "protocols": ["sACN", "Art-Net", "ETC Net3", "DMX", "RDM"],
        "sensors": sensor_catalog(),
        "evidence_policy": "official_documentation_only",
    }

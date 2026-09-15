"""Projector control plane.

Monitoring is handled in :mod:`projector_monitor`.  This module contains only
explicit write operations and never bypasses the Home Assistant service lock.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .projector_protocols import (
    BarcoPulseJSONRPC,
    ChristieHSSerialAPI,
    DigitalProjectionASCII,
    PJLinkClient,
    PanasonicWebAPI,
)

VENDOR_PROFILES = {
    "panasonic_webapi": {"name": "Panasonic Web API", "transport": "HTTP/HTTPS Digest", "default_port": 80},
    "digital_projection_ascii": {"name": "Digital Projection ASCII", "transport": "TCP", "default_port": 7000},
    "christie_hs": {"name": "Christie HS Serial API", "transport": "TCP", "default_port": 3002},
    "barco_pulse": {"name": "Barco Pulse / Prospector", "transport": "JSON-RPC 2.0/TCP", "default_port": 9090},
    "pjlink": {"name": "PJLink", "transport": "TCP", "default_port": 4352},
}


@dataclass
class ProjectorState:
    host: str
    port: int = 4352
    manufacturer: str | None = None
    model: str | None = None
    power: str | None = None
    input_source: str | None = None
    av_mute: str | None = None
    errors: list[str] = field(default_factory=list)
    temperatures_c: dict[str, float] = field(default_factory=dict)
    source_hours: dict[str, float] = field(default_factory=dict)
    online: bool = False
    last_error: str | None = None


class ProjectorController:
    """Execute one authorized projector command after the service gate."""

    def __init__(self, *, control_enabled: bool = False) -> None:
        self.control_enabled = control_enabled

    def set_control_enabled(self, enabled: bool) -> None:
        self.control_enabled = bool(enabled)

    def _require_enabled(self) -> None:
        if not self.control_enabled:
            raise PermissionError("projector control is disabled")

    @staticmethod
    def _profile(value: str | None) -> str:
        return str(value or "pjlink").strip().lower().replace("-", "_").replace(" ", "_")

    def send(self, host: str, *, profile: str = "pjlink", config: dict[str, Any] | None = None,
             name: str, value: str | None = None) -> Any:
        self._require_enabled()
        cfg = dict(config or {})
        p = self._profile(profile)
        timeout = float(cfg.get("timeout", 3.0))
        if p in {"panasonic", "panasonic_web_api", "panasonic_webapi"}:
            adapter = PanasonicWebAPI(
                host, username=cfg.get("username"), password=cfg.get("password"),
                scheme=str(cfg.get("scheme", "http")),
                port=int(cfg["vendor_port"]) if cfg.get("vendor_port") else None,
                timeout=timeout,
            )
        elif p in {"digital_projection_ascii", "digital_projection_rev_a", "digital_projection_rev_f", "digital_projection_rev_h", "digital_projection_simplified"}:
            adapter = DigitalProjectionASCII(host, int(cfg.get("vendor_port", 7000)), timeout=timeout)
        elif p in {"christie_hs", "christie_hs_2k", "christie_hs_serial"}:
            adapter = ChristieHSSerialAPI(host, int(cfg.get("vendor_port", 3002)), timeout=timeout)
        elif p in {"barco_pulse", "barco_prospector", "barco_jsonrpc"}:
            code = cfg.get("passcode")
            adapter = BarcoPulseJSONRPC(host, int(cfg.get("vendor_port", 9090)), timeout=timeout,
                                        passcode=int(code) if code not in (None, "") else None)
        else:
            adapter = PJLinkClient(host, int(cfg.get("pjlink_port", cfg.get("port", 4352))),
                                   password=cfg.get("pjlink_password") or cfg.get("password"), timeout=timeout)
        return adapter.write(name, value)

    # Backward-compatible entry point used by existing service/tests.
    def send_pjlink(self, host: str, port: int, name: str, value: str | None = None,
                    timeout: float = 3.0, password: str | None = None) -> str:
        self._require_enabled()
        return PJLinkClient(host, port, password=password, timeout=timeout).write(name, value)

    def snapshot(self, state: ProjectorState) -> dict[str, Any]:
        return {
            "host": state.host,
            "port": state.port,
            "manufacturer": state.manufacturer,
            "model": state.model,
            "power": state.power,
            "input_source": state.input_source,
            "av_mute": state.av_mute,
            "errors": list(state.errors),
            "temperatures_c": dict(state.temperatures_c),
            "source_hours": dict(state.source_hours),
            "online": state.online,
            "last_error": state.last_error,
            "control_enabled": self.control_enabled,
        }

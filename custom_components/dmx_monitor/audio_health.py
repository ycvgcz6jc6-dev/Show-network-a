"""Passive audio-network health aggregation."""
from __future__ import annotations
import time

STALE_S = 15.0

class AudioHealth:
    def __init__(self, stale_s: float = STALE_S) -> None:
        self.stale_s = float(stale_s)

    @staticmethod
    def _age(ts: float | None, now: float) -> float | None:
        if not ts:
            return None
        return max(0.0, now - ts)

    def snapshot(self, dante: dict | None = None, ptp: dict | None = None,
                 aes67: dict | None = None, st2110: dict | None = None,
                 avb: dict | None = None) -> dict:
        now = time.time()
        dante = dante or {}; ptp = ptp or {}; aes67 = aes67 or {}; st2110 = st2110 or {}; avb = avb or {}
        ages = {
            "dante": self._age(dante.get("dante_last_seen"), now),
            "ptp": self._age(ptp.get("ptp_last_seen"), now),
            "aes67": self._age(aes67.get("aes67_last_seen"), now),
            "st2110": self._age(st2110.get("st2110_last_seen"), now),
            "avb": self._age(avb.get("avb_last_seen"), now),
        }
        active = {k: v is not None and v <= self.stale_s for k, v in ages.items()}
        # Capability matrix is deliberately conservative.  A passive packet
        # observer can prove traffic presence and PTPv2 announce identity, but
        # it cannot claim Dante Controller-only device telemetry (subscriptions,
        # late-packet histograms, redundancy state, channel metering, etc.) unless
        # a future documented/authorised telemetry source supplies those fields.
        gm = ptp.get("ptp_active_grandmaster_identity")
        clock_present = bool(ptp.get("ptp_clock_present"))
        return {
            "audio_health": "ok" if any(active.values()) else "silent",
            "audio_stale_timeout_s": self.stale_s,
            "audio_protocols_active": [k for k, v in active.items() if v],
            "audio_protocols_stale": [k for k, v in active.items() if v is False and ages[k] is not None],
            "audio_last_seen_age_s": ages,
            "audio_sources": {
                "dante": dante.get("dante_fresh_sources", 0),
                "ptp": ptp.get("ptp_sources", 0),
                "aes67": aes67.get("aes67_sap_sources", 0),
                "st2110": st2110.get("st2110_sources", 0),
                "avb": avb.get("sources", 0),
            },
            "audio_network_health": {
                "clock": {
                    "state": "observed" if clock_present else "not_observed",
                    "leader_identity": gm,
                    "last_leader_identity": ptp.get("ptp_grandmaster_identity"),
                    "leader_fresh": bool(ptp.get("ptp_grandmaster_fresh")),
                    "leader_semantics": "ptpv2_announce_grandmaster" if gm else None,
                    "age_s": ptp.get("ptp_clock_age_s"),
                    "packet_arrival_jitter_ms": ptp.get("ptp_jitter_ms"),
                    "clock_offset_ns": None,
                    "clock_offset_available": False,
                    "note": "PTPv2 grandmaster identity is decoded from Announce. Passive packet-arrival jitter is not Dante clock offset/stability."
                },
                "dante_device_telemetry": {
                    "subscriptions": "available_via_dante_managed_api_when_configured",
                    "latency_histograms": "unavailable",
                    "late_packets": "unavailable",
                    "primary_secondary": "unavailable",
                    "signal_presence": "available_on_supported_devices_via_authorized_dante_management_source",
                    "peak_rms": "requires_real_audio_or_manufacturer_level_telemetry",
                    "firmware": "available_only_when_explicitly_observed",
                    "reason": "Passive traffic is never decoded as proprietary Controller telemetry. Documented Dante Managed API data may be used when explicitly configured."
                },
                "network_telemetry": {
                    "source": "switch_telemetry",
                    "warning_utilization_pct": 70,
                    "critical_utilization_pct": 85,
                    "threshold_note": "70% is a conservative Show Network warning; 85% follows Audinate's approximate Rx/Tx utilization rule of thumb for clock performance."
                },
                "measurement_policy": "measured_or_explicitly_unavailable_never_simulated",
            },
        }

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
        return {
            "audio_health": "ok" if any(active.values()) else "silent",
            "audio_stale_timeout_s": self.stale_s,
            "audio_protocols_active": [k for k, v in active.items() if v],
            "audio_protocols_stale": [k for k, v in active.items() if v is False and ages[k] is not None],
            "audio_last_seen_age_s": ages,
            "audio_sources": {
                "dante": dante.get("dante_sources", 0),
                "ptp": ptp.get("ptp_sources", 0),
                "aes67": aes67.get("aes67_sap_sources", 0),
                "st2110": st2110.get("st2110_sources", 0),
                "avb": avb.get("sources", 0),
            },
        }

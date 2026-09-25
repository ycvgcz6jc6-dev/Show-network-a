"""Curated Philips Hue lamp capability catalog.

The catalog is deliberately metadata-only: it does not bundle Philips firmware or
proprietary API content. Live bridge data, when available, is preferred over the
static model hints.
"""
from __future__ import annotations

HUE_CATALOG = {
    # Common Hue color / ambiance families.
    "LCT001": {"name": "Hue color lamp", "kind": "rgb", "gamut": "B", "ct_min": 153, "ct_max": 500},
    "LCT002": {"name": "Hue BR30 color", "kind": "rgb", "gamut": "B", "ct_min": 153, "ct_max": 500},
    "LCT003": {"name": "Hue GU10 color", "kind": "rgb", "gamut": "B", "ct_min": 153, "ct_max": 500},
    "LCT007": {"name": "Hue color 800 lm", "kind": "rgb", "gamut": "B", "ct_min": 153, "ct_max": 500},
    "LCT010": {"name": "Hue color A19", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCT011": {"name": "Hue color BR30", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCT012": {"name": "Hue color E14", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCT024": {"name": "Hue Play", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCA001": {"name": "Hue White and Color B22", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCA002": {"name": "Hue White and Color A19", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCA003": {"name": "Hue White and Color E26", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCA005": {"name": "Hue White and Color 800 lm", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCA007": {"name": "Hue White and Color 1100 lm", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCG001": {"name": "Hue White and Color GU10", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCG002": {"name": "Hue GU10 v2", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCF003": {"name": "Hue Signe", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCF005": {"name": "Hue Calla", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCF001": {"name": "Hue Lily", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCX001": {"name": "Hue Play Gradient Lightstrip", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500, "gradient": True},
    "LCL001": {"name": "Hue Lightstrip Plus", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LCL003": {"name": "Hue Outdoor Lightstrip", "kind": "rgb", "gamut": "C", "ct_min": 153, "ct_max": 500},
    "LLC020": {"name": "Hue Go", "kind": "rgb", "gamut": "A", "ct_min": 153, "ct_max": 500},
    # White / White Ambiance families.
    "LWB014": {"name": "Hue White", "kind": "dimmer"},
    "LTW001": {"name": "Hue White Ambiance A19", "kind": "cct", "ct_min": 153, "ct_max": 454},
    "LLM010": {"name": "Hue White and Color module", "kind": "cct", "ct_min": 153, "ct_max": 454},
    "LLM011": {"name": "Hue White and Color module", "kind": "cct", "ct_min": 153, "ct_max": 454},
    "LLM012": {"name": "Hue White and Color module", "kind": "cct", "ct_min": 153, "ct_max": 454},
}


def get(model_id: str | None) -> dict:
    """Return a safe copy of the best known model hint."""
    return dict(HUE_CATALOG.get(str(model_id or ""), {"name": "Hue / unknown model", "kind": "unknown"}))


def snapshot() -> list[dict]:
    return [{"model_id": model_id, **data} for model_id, data in sorted(HUE_CATALOG.items())]

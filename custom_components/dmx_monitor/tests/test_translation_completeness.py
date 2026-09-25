"""Translation completeness (block 8, Observabilité: UI/UX & translations).

Audit-confirmed gap: French (230 keys) was the complete reference, but
English was missing 12 keys and German/Spanish/Italian/Dutch were each
missing 16 -- all real, user-facing config-flow field labels
(dmx_artnet_enabled, dmx_sacn_enabled, dmx_source, ma_enabled, each in
the initial setup step, the reconfigure step, and the options step) plus
two error messages (invalid_json, port_in_use) missing entirely from
the four non-English languages. A user setting up or reconfiguring the
integration in one of those languages would have seen these specific
fields fall back to raw keys or English text instead of their own
language.

This test guards against the same drift happening again silently: any
future edit that adds a key to one language file without the others
will fail here, rather than being discovered only when a user in that
language actually opens the config flow.
"""
from __future__ import annotations

import json
import os

TRANSLATIONS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "custom_components", "dmx_monitor", "translations"
)
LANGUAGES = ["fr", "en", "de", "es", "it", "nl"]


def _flatten(d: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for k, v in d.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys |= _flatten(v, full)
        else:
            keys.add(full)
    return keys


def _load(lang: str) -> dict:
    path = os.path.join(TRANSLATIONS_DIR, f"{lang}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_all_translation_files_are_valid_json():
    for lang in LANGUAGES:
        _load(lang)  # raises if malformed -- the assertion is that this doesn't raise


def test_all_languages_have_the_same_key_set():
    flat = {lang: _flatten(_load(lang)) for lang in LANGUAGES}
    all_keys = set().union(*flat.values())
    missing_by_lang = {lang: sorted(all_keys - keys) for lang, keys in flat.items()}
    offenders = {lang: missing for lang, missing in missing_by_lang.items() if missing}
    assert not offenders, f"translation files have drifted apart: {offenders}"


def test_dmx_config_fields_present_in_every_language():
    """The exact fields the audit found missing -- pinned individually so
    a future partial fix (e.g. only config.step.user, forgetting
    reconfigure/options) is still caught precisely."""
    required_suffixes = [
        "data.dmx_artnet_enabled", "data.dmx_sacn_enabled",
        "data.dmx_source", "data.ma_enabled",
    ]
    required_prefixes = ["config.step.user", "config.step.reconfigure", "options.step.init"]
    for lang in LANGUAGES:
        flat = _flatten(_load(lang))
        for prefix in required_prefixes:
            for suffix in required_suffixes:
                key = f"{prefix}.{suffix}"
                assert key in flat, f"{lang}.json is missing {key}"


def test_session_added_fields_present_in_every_language_and_location():
    """Every new config field added over this session (Yamaha OSC, QLab,
    Resolume, Nexus Audio, Millumin, Green-GO, Sendspin/spin2dante) was
    found to have zero translation entries at all -- a gap introduced by
    the session's own work, not the original audit. Plus a small
    pre-existing gap found alongside it: aes70_hosts/aes70_port were
    missing specifically from options.step.init (present in
    config.step.user/reconfigure only)."""
    required_new_fields = [
        "yamaha_osc_hosts", "qlab_hosts", "resolume_hosts", "nexus_audio_hosts",
        "millumin_listen_port", "millumin_ping_target", "greengo_multicast_group",
        "sendspin_dante_players", "avdecc_bridge_url", "rdm_bridge_url", "rdmnet_bridge_url",
    ]
    required_prefixes = ["config.step.user", "config.step.reconfigure", "options.step.init"]
    for lang in LANGUAGES:
        flat = _flatten(_load(lang))
        for prefix in required_prefixes:
            for field in required_new_fields:
                key = f"{prefix}.data.{field}"
                assert key in flat, f"{lang}.json is missing {key}"
        for field in ("aes70_hosts", "aes70_port"):
            key = f"options.step.init.data.{field}"
            assert key in flat, f"{lang}.json is missing {key} (pre-existing gap)"


def test_error_messages_present_in_every_language():
    for lang in LANGUAGES:
        flat = _flatten(_load(lang))
        for key in ("config.error.invalid_json", "config.error.port_in_use",
                    "options.error.invalid_json", "options.error.port_in_use"):
            assert key in flat, f"{lang}.json is missing {key}"


def test_no_empty_string_values():
    """A present-but-empty translation is arguably worse than a missing
    one (looks intentional, silently shows a blank label)."""
    for lang in LANGUAGES:
        data = _load(lang)
        flat_items = {}

        def collect(d, prefix=""):
            for k, v in d.items():
                full = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    collect(v, full)
                else:
                    flat_items[full] = v

        collect(data)
        empties = [k for k, v in flat_items.items() if isinstance(v, str) and not v.strip()]
        assert not empties, f"{lang}.json has empty-string values: {empties}"

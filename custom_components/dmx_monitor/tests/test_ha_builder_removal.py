"""Home Assistant-integrated test for HA Builder entity removal.

Audit-confirmed gap: ha_builder_remove_callbacks was initialized in every
platform module (switch, sensor, binary_sensor, number, button) but never
populated, so removing a HA Builder item deleted it from storage while the
live Home Assistant entity kept existing as an orphan. This test exercises
the real Home Assistant entity registry (not a mock) to prove that after
this fix, deleting an item removes both its state and its entity registry
entry.

Requires pytest-homeassistant-custom-component (see tests/conftest.py) and
must be run with --asyncio-mode=auto: pytest-homeassistant-custom-component
defines `hass` as a plain @pytest.fixture async generator rather than
@pytest_asyncio.fixture, so pytest-asyncio's default "strict" mode does not
resolve it (the test receives the unresolved async_generator object
instead of a running Home Assistant instance).
"""
from __future__ import annotations

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pytest_homeassistant_custom_component.common import MockEntityPlatform

from custom_components.dmx_monitor.const import DOMAIN
from custom_components.dmx_monitor.ha_builder import HABuilder
from custom_components.dmx_monitor import switch as switch_platform
from custom_components.dmx_monitor import button as button_platform

pytestmark = pytest.mark.asyncio


class _Stub:
    """Minimal stand-in for a coordinator sub-manager with an on/off flag."""
    def __init__(self):
        self.enabled = False
        self.control_enabled = False


class _FakeCoordinator(DataUpdateCoordinator):
    """Just enough surface for switch.py / button.py's async_setup_entry.

    Subclasses the real DataUpdateCoordinator (rather than a bespoke
    object) so that CoordinatorEntity's own lifecycle methods --
    async_add_listener, last_update_success, etc., which
    async_added_to_hass() genuinely calls -- work exactly as they would in
    production. Deliberately still not the full production Coordinator:
    this test targets the HA Builder add/remove wiring itself, which only
    touches ha_builder and the two callback dicts -- pulling in the real
    Coordinator (DMX trackers, network interface snapshots, etc.) would
    only add unrelated setup cost and failure surface. The handful of
    sub-manager stubs below exist only because switch.py's
    async_setup_entry also creates several unrelated safety-gate switches
    alongside the HA Builder ones in the same entities list, and each
    reads one coordinator attribute to compute its own state.
    """

    def __init__(self, hass, tmp_path):
        super().__init__(hass, __import__("logging").getLogger(__name__), name="test_dmx_monitor")
        self.ha_builder = HABuilder(str(tmp_path / "ha_builder_items.json"))
        self.data = {}
        self.osc_output = _Stub()
        self.midi_output = _Stub()
        self.show_control = _Stub()
        self.projector_controller = _Stub()
        self.dmx_scene_bank = _Stub()
        self.fixture_control = _Stub()

    def publish(self, **kwargs):
        self.data.update(kwargs)

    def publish(self, **kwargs):
        self.data.update(kwargs)


def _make_fake_add_entities(hass, added_entities, platform_domain):
    """A real EntityPlatform's async_add_entities, bound to a throwaway
    MockEntityPlatform (from pytest-homeassistant-custom-component).

    Using the genuine EntityPlatform machinery -- rather than
    hand-reimplementing registry/state/restore_state bookkeeping -- is
    what lets entity.async_remove() (called by our async_remove_builder_
    entity helper) work exactly as it would in a real Home Assistant
    instance, including the internal restore_state housekeeping that a
    partial reimplementation kept tripping over.

    Home Assistant's real AddEntitiesCallback (what switch.py/button.py
    actually call) is a plain, non-async callable despite the name --
    production code calls it as `async_add_entities(entities)`, no
    `await`. It schedules the real async work as a background task
    instead, which is why every test here does `await
    hass.async_block_till_done()` right after calling into
    async_setup_entry.
    """
    platform = MockEntityPlatform(hass, domain=platform_domain, platform_name=DOMAIN)

    def _add(new_entities, update_before_add=False):
        added_entities.extend(new_entities)
        hass.async_create_task(platform.async_add_entities(new_entities, update_before_add=update_before_add))

    return _add


async def test_switch_create_and_remove_round_trip(hass, tmp_path):
    coordinator = _FakeCoordinator(hass, tmp_path)
    item = coordinator.ha_builder.create("Audit switch", entity_type="switch")
    hass.data.setdefault(DOMAIN, {})["test_entry"] = {"coordinator": coordinator}

    added_entities: list = []

    class _FakeEntry:
        entry_id = "test_entry"

    await switch_platform.async_setup_entry(
        hass, _FakeEntry(), _make_fake_add_entities(hass, added_entities, "switch")
    )
    await hass.async_block_till_done()

    matching = [e for e in added_entities if getattr(e, "item_id", None) == item.item_id]
    assert len(matching) == 1, "the HA Builder switch should have been added at setup"
    entity = matching[0]

    registry = er.async_get(hass)
    assert registry.async_get_entity_id("switch", DOMAIN, entity.unique_id) is not None, (
        "entity should be in the registry after creation"
    )
    assert hass.states.get(entity.entity_id) is not None, "entity should have a live state after creation"

    # Remove it the way the ha_builder_remove service does: call every
    # registered remove callback with the item_id.
    assert "switch" in coordinator.ha_builder_remove_callbacks, "switch.py must register a remove callback"
    await coordinator.ha_builder_remove_callbacks["switch"](item.item_id)
    await hass.async_block_till_done()

    assert hass.states.get(entity.entity_id) is None, (
        "FAIL: entity state still present after ha_builder_remove -- "
        "this is exactly the audit-confirmed orphaned-entity gap"
    )
    assert registry.async_get_entity_id("switch", DOMAIN, entity.unique_id) is None, (
        "FAIL: entity registry entry still present after removal"
    )


async def test_button_item_is_actually_removed(hass, tmp_path):
    """Same round trip for button.py, the platform the audit's own
    traceback pointed at ('BuilderButton' object has no attribute
    'async_turn_off') -- confirms it now owns its full lifecycle correctly,
    not just creation."""
    coordinator = _FakeCoordinator(hass, tmp_path)
    item = coordinator.ha_builder.create("Audit button", entity_type="button")
    hass.data.setdefault(DOMAIN, {})["test_entry_button"] = {"coordinator": coordinator}

    added_entities: list = []

    class _FakeEntry:
        entry_id = "test_entry_button"

    await button_platform.async_setup_entry(
        hass, _FakeEntry(), _make_fake_add_entities(hass, added_entities, "button")
    )
    await hass.async_block_till_done()

    matching = [e for e in added_entities if getattr(e, "item_id", None) == item.item_id]
    assert len(matching) == 1
    entity = matching[0]

    registry = er.async_get(hass)
    assert registry.async_get_entity_id("button", DOMAIN, entity.unique_id) is not None

    await coordinator.ha_builder_remove_callbacks["button"](item.item_id)
    await hass.async_block_till_done()

    assert hass.states.get(entity.entity_id) is None
    assert registry.async_get_entity_id("button", DOMAIN, entity.unique_id) is None


async def test_removing_one_item_does_not_touch_another(hass, tmp_path):
    """Guards against a sloppy remove callback that clears more than the
    one item_id it was asked to remove."""
    coordinator = _FakeCoordinator(hass, tmp_path)
    keep = coordinator.ha_builder.create("Keep me", entity_type="switch")
    doomed = coordinator.ha_builder.create("Remove me", entity_type="switch")
    hass.data.setdefault(DOMAIN, {})["test_entry_2"] = {"coordinator": coordinator}

    added_entities: list = []

    class _FakeEntry:
        entry_id = "test_entry_2"

    await switch_platform.async_setup_entry(
        hass, _FakeEntry(), _make_fake_add_entities(hass, added_entities, "switch")
    )
    await hass.async_block_till_done()

    keep_entity = next(e for e in added_entities if getattr(e, "item_id", None) == keep.item_id)

    await coordinator.ha_builder_remove_callbacks["switch"](doomed.item_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    assert hass.states.get(keep_entity.entity_id) is not None, "the untouched item's entity must survive"
    assert registry.async_get_entity_id("switch", DOMAIN, keep_entity.unique_id) is not None

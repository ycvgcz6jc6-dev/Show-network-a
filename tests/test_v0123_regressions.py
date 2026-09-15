from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "dmx_monitor"


def test_only_real_ha_platforms_are_forwarded():
    text = (COMP / "__init__.py").read_text()
    assert '"projector_platform"' not in text
    assert 'PLATFORMS = ["sensor", "binary_sensor", "switch", "number", "scene"]' in text


def test_projector_entities_are_bound_to_real_platforms():
    sensor = (COMP / "sensor.py").read_text()
    binary = (COMP / "binary_sensor.py").read_text()
    helper = (COMP / "projector_platform.py").read_text()
    assert "projector_sensor_entities(coordinator)" in sensor
    assert "projector_binary_entities(coordinator)" in binary
    assert "def sensor_entities(c):" in helper
    assert "def binary_entities(c):" in helper
    assert "async def async_setup_entry" not in helper


def test_complex_sensor_native_states_are_not_returned_as_dicts():
    text = (COMP / "sensor.py").read_text()
    native = text.split("    @property\n    def native_value(self):", 1)[1].split("    @property\n    def extra_state_attributes(self):", 1)[0]
    assert 'return dict(self.coordinator.data.get("archive", {}))' not in native
    assert 'return dict(self.coordinator.data.get("network_capacity", {}))' not in native
    assert 'return dict(self.coordinator.data.get("chaos", {}))' not in native
    assert 'return {"mappings": self.coordinator.data.get("dmx_ha_mappings", [])}' not in native


def test_punchlight_keeps_callback_task_references():
    text = (COMP / "punchlight.py").read_text()
    assert "self._callback_tasks" in text
    assert "task.add_done_callback(self._callback_tasks.discard)" in text


def test_manifest_and_const_versions_match():
    import json
    manifest = json.loads((COMP / "manifest.json").read_text())
    const = (COMP / "const.py").read_text()
    assert manifest["version"] == "0.15.2"
    assert 'VERSION = "0.15.2"' in const

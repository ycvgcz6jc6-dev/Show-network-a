"""Shared pytest configuration for Show Network's test suite.

Two categories of tests live under tests/:

1. Pure-logic tests (test_security.py, test_archive.py,
   test_attribute_bounds.py, test_services_common.py,
   test_ma3_web_remote_proxy.py, test_artnet_discovery.py,
   test_video_ip_preview.py) exercise modules with no Home Assistant
   dependency at all. These need only `pip install pytest` and run
   anywhere, including plain CI without a Home Assistant test harness.

2. Home Assistant-integrated tests (test_config_flow.py,
   test_services_registration.py, test_init.py) exercise the config flow,
   service registration, and setup/unload lifecycle against a real (test)
   Home Assistant instance. These require:

       pip install pytest-homeassistant-custom-component

   and are written using that library's standard fixtures (`hass`,
   `MockConfigEntry`, `enable_custom_integrations`). They were written
   following that library's documented conventions but could not be
   executed in the environment this project was developed in (no network
   access to install Home Assistant or its test harness) -- run them with
   a real `pytest` + `pytest-homeassistant-custom-component` install
   before relying on them, the same way any new dependency should be
   verified before trusting it.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `import custom_components.dmx_monitor.xxx` work when pytest is run
# from the repository root (the standard HACS/custom_components layout).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

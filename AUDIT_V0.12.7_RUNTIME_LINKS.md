# Show Network v0.12.7 — runtime links

Corrections driven by real Home Assistant tests from the user.

- Fixed DMX→HA zone/mapping service imports.
- Channel parser now accepts lists and bracketed frontend values.
- Added working `scan_network` service and wired the discovery button with visible progress/results.
- Vendor mDNS discovery now feeds the shared device inventory pipeline.
- Exposed `device_inventory` and `show_network_config` sensors so inventory and network configuration pages have real backing data.
- Network module now shows actual configured bindings for DMX, MA-Net3, Dante, PTP and audio, with a direct button to the Home Assistant integration configuration.
- Security UI now separates first password setup, unlock and password change.
- Moved SecurityManager load/PBKDF2+write, archive status/destination and HA Builder writes off the Home Assistant event loop.
- Kept OSC OUT / Light Sync / projector active controls protected by the security gate.

Validation performed here: Python compile, JavaScript syntax and unit/static tests only. No claim of live HA/network/hardware validation.

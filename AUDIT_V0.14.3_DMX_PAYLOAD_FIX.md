# Show Network v0.14.3 — DMX payload fix

## Confirmed root cause
The coordinator correctly stored live DMX as `values_b64`, while `DmxUniverseSensor.extra_state_attributes` ignored that field and attempted to rebuild it from a non-existent `values` array. Result: packet rate and active-channel counts were real, but the frontend received an empty DMX payload and displayed 512 zeros.

## Fixes
- Preserve coordinator `values_b64` unchanged in the HA aggregate DMX sensor.
- Keep legacy `values` fallback only for compatibility.
- DMX source/universe selector keys are stable and no longer depend on array index.
- Selected protocol/universe/source is retained in browser session storage across HA state refreshes/component recreation.

## Validation scope
Static/unit validation only. No claim of real hardware validation until installed on the user's Home Assistant instance.

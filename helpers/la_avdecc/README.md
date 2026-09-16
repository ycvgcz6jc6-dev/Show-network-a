# Show Network — LA_avdecc helper

Read-only helper around the official **L-Acoustics/avdecc** controller library.
It is intentionally outside the Home Assistant Python process because LA_avdecc
is a native C++/PCap stack.

## Runtime

1. Set `AVDECC_INTERFACE` to the interface connected to the AVB/Milan network.
2. The collector keeps an AVDECC controller alive and publishes an atomic JSON dump.
3. `bridge_server.py` exposes the normalized dump at `GET /v1/entities` and health at `GET /health`.
4. Configure Show Network `avdecc_bridge_url` as `http://<helper>:8765/v1/entities`.

The helper is read-only: it discovers/serializes controller state and does not send
amplifier mute/gain/power commands. It never fabricates temperatures or audio meters.

Linux/containers need access to the physical AVB NIC and packet capture privileges
(e.g. host networking plus the capabilities required by PCap in the deployment).
Pin `AVDECC_REF` to a tested LA_avdecc tag/commit for production builds.

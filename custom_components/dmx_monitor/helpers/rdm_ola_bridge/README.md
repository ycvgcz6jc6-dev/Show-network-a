# Show Network OLA RDM bridge

This helper keeps native OLA outside Home Assistant Core. It uses the documented
`ola_rdm_discover`, `ola_rdm_get` and, only when explicitly enabled,
`ola_rdm_set` tools. Default mode is read-only.

Environment: `RDM_UNIVERSES=1,2,10`, `RDM_PORT=8098`, `RDM_ALLOW_SET=0`.
When writes are enabled, only `dmx_start_address`, `dmx_personality`,
`device_label` and `identify_device` are accepted by the bridge. A `SET` is
also rejected outright if its `universe` is not in `RDM_UNIVERSES`.

## Security (read before exposing beyond localhost)

- **`RDM_BIND`** (default `127.0.0.1`): the bridge only listens on loopback
  by default. Set `RDM_BIND=0.0.0.0` only if you understand the exposure
  this creates (e.g. running inside a container where Show Network reaches
  it over a Docker network) -- put it behind a firewall, an isolated
  network, or a TLS-terminating reverse proxy/SSH tunnel if you do.
- **`RDM_AUTH_TOKEN`**: every request except `/health` requires
  `Authorization: Bearer <token>`. If you don't set this, a random token is
  generated and printed to the log on every start (so it changes on
  restart) -- set it explicitly to pin a stable value, and configure the
  same value in Show Network's options (RDM/RDMnet bridge token field) so
  it can authenticate.


# Show Network RDMnet bridge contract

Show Network's RDMnet backend is deliberately separated from Home Assistant Core.
The native implementation should use ETCLabs/RDMnet (ANSI E1.33) and expose:

- `GET /health`
- `GET /v1/devices` -> `{ "devices": [...] }`
- `POST /v1/set` for explicit gated SETs only

The controller must connect to configured RDMnet scopes (default scope when not
specified), request the broker client list, and populate responders from real
RDMnet RPT messages. DNS-SD broker discovery is delegated to ETCLabs/RDMnet.

No Python emulation of E1.33 is used. Until a native helper is running, the HA
module reports `rdmnet_bridge_configured/error` rather than fabricating devices.

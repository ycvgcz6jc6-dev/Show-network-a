# Show Network dashboards

Les dashboards utilisent les custom elements Show Network fournis par un bundle Lovelace unique :
`/api/dmx_monitor/static/show-network.js`.

Le bundle regroupe les panneaux modulaires afin de réduire les ressources chargées par Lovelace et de garantir
qu'une même version de tous les composants frontend est utilisée.

### Fixture profiles
Show Network keeps fixture metadata separate from HA entities. Profiles use a small generic schema (manufacturer/model, modes, channels and capabilities), allowing DMX patch/mapping logic to evolve without coupling it to Philips Hue or another HA light integration. Proprietary fixture-library data is not bundled.

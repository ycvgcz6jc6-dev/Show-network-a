#!/bin/sh
set -eu
: "${AVDECC_INTERFACE:?Set AVDECC_INTERFACE to the AVB/Milan network interface id}"
DUMP="${AVDECC_DUMP:-/data/avdecc-network.json}"
INTERVAL="${AVDECC_INTERVAL:-2}"
/usr/local/bin/show-network-avdecc-collector --interface "$AVDECC_INTERFACE" --output "$DUMP" --interval "$INTERVAL" &
collector=$!
trap 'kill "$collector" 2>/dev/null || true' INT TERM EXIT
exec /usr/local/bin/show-network-avdecc-bridge --dump "$DUMP" --listen 0.0.0.0 --port "${AVDECC_HTTP_PORT:-8765}"

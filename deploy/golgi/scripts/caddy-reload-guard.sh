#!/bin/bash
# caddy-reload-guard.sh — only reload Caddy if the config actually changed
# Prevents the 30-second reload storm that kills TLS handshakes

HASH_FILE=/tmp/caddy-config-hash
CADDYFILE=/etc/membrane/Caddyfile
SNIPPET_DIR=/opt/membrane/fleet-imports
MIN_INTERVAL=300  # minimum seconds between reloads

# Compute hash of all config files
CURRENT_HASH=$(cat "$CADDYFILE" "$SNIPPET_DIR"/*.snippet 2>/dev/null | sha256sum | cut -d' ' -f1)

# Check last hash
LAST_HASH=""
LAST_TIME=0
if [ -f "$HASH_FILE" ]; then
    LAST_HASH=$(head -1 "$HASH_FILE")
    LAST_TIME=$(tail -1 "$HASH_FILE")
fi

NOW=$(date +%s)
ELAPSED=$((NOW - LAST_TIME))

# Only reload if content changed AND minimum interval passed
if [ "$CURRENT_HASH" = "$LAST_HASH" ]; then
    exit 0  # no change, skip reload
fi

if [ $ELAPSED -lt $MIN_INTERVAL ] && [ $LAST_TIME -gt 0 ]; then
    exit 0  # too soon since last reload, skip
fi

# Content changed and enough time passed — do the reload
echo "$CURRENT_HASH" > "$HASH_FILE"
echo "$NOW" >> "$HASH_FILE"
/opt/membrane/caddy reload --config /etc/membrane/Caddyfile --address localhost:2019 2>&1

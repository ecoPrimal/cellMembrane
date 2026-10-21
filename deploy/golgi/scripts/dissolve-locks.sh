#!/usr/bin/env bash
# dissolve-locks.sh — self-healing lock dissolution
# 
# Watches /opt/membrane/live-terminal/remote/locks/ for instruction files.
# When a lock-dissolve instruction arrives (from any gate), golgi acts on it.
#
# Lock types:
#   dns-porkbun.json  → switch NS at Porkbun via API
#   dns-cloudflare.json → manage CF zone via API
#   do-token.json     → store DO API token, check fleet
#   ssh-key.json      → distribute SSH pubkey to target gate
#
# Each instruction is a JSON file with:
#   { "action": "...", "params": {...}, "from": "gate", "ts": "..." }
#
# The membrane dissolves the lock, writes result, deletes the instruction.

set -euo pipefail

LOCK_DIR="/opt/membrane/live-terminal/remote/locks"
RESULT_DIR="/opt/membrane/live-terminal/lock-results"
SECRETS="/etc/membrane/secrets"

mkdir -p "$LOCK_DIR" "$RESULT_DIR"

dissolve_dns_porkbun() {
    local file="$1"
    local api_key api_secret domain
    api_key=$(jq -r '.params.api_key' "$file")
    api_secret=$(jq -r '.params.api_secret' "$file")
    domain=$(jq -r '.params.domain // "primals.eco"' "$file")
    
    # Store keys for future use
    echo "$api_key" > "$SECRETS/porkbun_api_key"
    echo "$api_secret" > "$SECRETS/porkbun_api_secret"
    chmod 600 "$SECRETS/porkbun_api_key" "$SECRETS/porkbun_api_secret"
    
    # Switch nameservers via Porkbun API
    # https://porkbun.com/api/json/v3/documentation
    local result
    result=$(curl -s -X POST "https://api.porkbun.com/api/json/v3/domain/updateNs/$domain" \
        -H "Content-Type: application/json" \
        -d "{
            \"secretapikey\": \"$api_secret\",
            \"apikey\": \"$api_key\",
            \"ns\": [\"ns1.primals.eco\", \"ns2.primals.eco\"]
        }")
    
    echo "{\"action\": \"dns-porkbun\", \"domain\": \"$domain\", \"result\": $result, \"ts\": \"$(date -u +%FT%TZ)\"}" > "$RESULT_DIR/dns-porkbun-result.json"
    echo "DNS: Porkbun NS switched to sovereign for $domain"
}

dissolve_do_token() {
    local file="$1"
    local token
    token=$(jq -r '.params.token' "$file")
    
    # Store token
    echo "$token" > "$SECRETS/do_api_token"
    chmod 600 "$SECRETS/do_api_token"
    
    # Test it
    local result
    result=$(curl -s -X GET "https://api.digitalocean.com/v2/account" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json")
    
    local status
    status=$(echo "$result" | jq -r '.account.status // "error"')
    
    # Check droplets
    local droplets
    droplets=$(curl -s -X GET "https://api.digitalocean.com/v2/droplets" \
        -H "Authorization: Bearer $token" | jq -r '.droplets[] | "\(.name) \(.status) \(.networks.v4[0].ip_address)"')
    
    echo "{\"action\": \"do-token\", \"account_status\": \"$status\", \"droplets\": \"$droplets\", \"ts\": \"$(date -u +%FT%TZ)\"}" > "$RESULT_DIR/do-token-result.json"
    echo "DO: Token stored, account=$status"
}

dissolve_ssh_key() {
    local file="$1"
    local pubkey target_gate
    pubkey=$(jq -r '.params.pubkey' "$file")
    target_gate=$(jq -r '.params.target // "all"' "$file")
    
    # Write pubkey to membrane for target gate to pick up
    mkdir -p "/opt/membrane/live-terminal/ssh-keys"
    echo "$pubkey" > "/opt/membrane/live-terminal/ssh-keys/$(jq -r '.from' "$file").pub"
    
    echo "{\"action\": \"ssh-key\", \"from\": \"$(jq -r '.from' "$file")\", \"target\": \"$target_gate\", \"ts\": \"$(date -u +%FT%TZ)\"}" > "$RESULT_DIR/ssh-key-result.json"
    echo "SSH: pubkey from $(jq -r '.from' "$file") dropped for $target_gate"
}

# Main loop — process any lock files
for lock_file in "$LOCK_DIR"/*.json; do
    [ -f "$lock_file" ] || continue
    
    action=$(jq -r '.action' "$lock_file")
    echo "Dissolving: $action (from $(jq -r '.from' "$lock_file"))"
    
    case "$action" in
        dns-porkbun)  dissolve_dns_porkbun "$lock_file" ;;
        do-token)     dissolve_do_token "$lock_file" ;;
        ssh-key)      dissolve_ssh_key "$lock_file" ;;
        *)            echo "Unknown lock type: $action" ;;
    esac
    
    # Archive the instruction (don't delete — audit trail)
    mv "$lock_file" "$RESULT_DIR/$(basename "$lock_file").dissolved"
done

echo "All locks processed."

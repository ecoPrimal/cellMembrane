#!/usr/bin/env bash
# deploy.sh — Rebirth a golgi membrane from scratch
# Usage: ssh root@fresh-droplet < deploy.sh
#   OR:  scp -r deploy/golgi/ root@fresh-droplet:/tmp/golgi-deploy && ssh root@fresh-droplet /tmp/golgi-deploy/deploy.sh
#
# Prerequisites: fresh Ubuntu 22.04+ droplet with root SSH access
# The sporePrint is the anchor. This script is the autoclave.

set -euo pipefail
DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
MEMBRANE_DIR="/opt/membrane"
ETC_DIR="/etc/membrane"

echo "═══ GOLGI REBIRTH ═══"
echo "deploying from: $DEPLOY_DIR"
echo ""

# 1. System packages
echo "[1/8] System packages..."
apt-get update -qq
apt-get install -y -qq git curl ufw fail2ban wireguard python3 python3-pip jq sqlite3 > /dev/null
echo "  ✅ packages"

# 2. Create membrane directories
echo "[2/8] Directory structure..."
mkdir -p "$MEMBRANE_DIR" "$ETC_DIR" "$MEMBRANE_DIR/live-terminal/remote" \
         "$MEMBRANE_DIR/feeds" "$MEMBRANE_DIR/fossils" "$MEMBRANE_DIR/neutron" \
         "$MEMBRANE_DIR/skeletons" "$MEMBRANE_DIR/private" "$MEMBRANE_DIR/vault" \
         /caddy
echo "  ✅ directories"

# 3. Deploy scripts
echo "[3/8] Deploying scripts..."
cp "$DEPLOY_DIR"/scripts/*.py "$DEPLOY_DIR"/scripts/*.sh "$MEMBRANE_DIR/"
chmod +x "$MEMBRANE_DIR"/*.sh "$MEMBRANE_DIR"/*.py 2>/dev/null || true
echo "  ✅ $(ls "$MEMBRANE_DIR"/*.py "$MEMBRANE_DIR"/*.sh 2>/dev/null | wc -l) scripts"

# 4. Deploy Caddy + configs
echo "[4/8] Caddy + configs..."
# Caddy binary must be built or downloaded separately (custom build with plugins)
cp "$DEPLOY_DIR"/caddy/Caddyfile "$ETC_DIR/Caddyfile"
cp "$DEPLOY_DIR"/caddy/*.toml "$DEPLOY_DIR"/caddy/*.caddy "$DEPLOY_DIR"/caddy/*.yml "$ETC_DIR/" 2>/dev/null || true
cp "$DEPLOY_DIR"/caddy/gate-name "$ETC_DIR/" 2>/dev/null || true
echo "  ✅ Caddyfile ($(wc -l < "$ETC_DIR/Caddyfile") lines)"

# 5. Deploy systemd units
echo "[5/8] Systemd units..."
for f in "$DEPLOY_DIR"/systemd/*.service "$DEPLOY_DIR"/systemd/*.timer "$DEPLOY_DIR"/systemd/*.target; do
  [ -f "$f" ] && cp "$f" /etc/systemd/system/
done
# Deploy drop-in dirs
for d in "$DEPLOY_DIR"/systemd/*.d; do
  [ -d "$d" ] && mkdir -p "/etc/systemd/system/$(basename "$d")" && cp "$d"/* "/etc/systemd/system/$(basename "$d")/"
done
systemctl daemon-reload
echo "  ✅ systemd units"

# 6. Cron
echo "[6/8] Cron..."
crontab "$DEPLOY_DIR/cron/crontab"
echo "  ✅ crontab installed"

# 7. Fail2ban
echo "[7/8] Fail2ban..."
cp "$DEPLOY_DIR"/fail2ban/*.conf /etc/fail2ban/jail.d/
systemctl restart fail2ban
echo "  ✅ fail2ban"

# 8. Firewall
echo "[8/8] Firewall..."
ufw --force reset > /dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (Caddy redirect)
ufw allow 443/tcp   # HTTPS (Caddy TLS)
ufw allow 51820/udp # WireGuard
ufw --force enable
echo "  ✅ UFW (22, 80, 443, 51820)"

echo ""
echo "═══ GOLGI REBORN ═══"
echo ""
echo "MANUAL STEPS REMAINING:"
echo "  1. Copy Rust binaries (caddy, opsonize-rs, skunkbat, petaltongue, songbird, squirrel)"
echo "  2. Copy /etc/membrane/secrets/ from vault"
echo "  3. Copy /etc/wireguard/wg0.conf and set private key"
echo "  4. systemctl enable --now caddy-tls opsonize skunkbat petaltongue songbird"
echo "  5. Update DNS records to point to new IP"
echo "  6. Update WireGuard peer configs on all gates"
echo "  7. Test: curl -I https://primals.eco"
echo ""
echo "The sporePrint is the anchor. The membrane floats free."

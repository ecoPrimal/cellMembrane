#!/usr/bin/env bash
# git-reverse-transcriptase.sh — PORT enzyme for VCS
# Phenotype (hung shell / unreachable forgejo / stale statics)
#   → genotype (route-around, braid strand+spine, reincarnate/rebuild/rehydrate)
set -euo pipefail

ROOT="${ECOPRIMALS_ROOT:-/home/eastgate/Development/ecoPrimals}"
HUD="$ROOT/infra/hud"
SPORE="$ROOT/infra/sporePrint"
DATA="$HUD/site/public/data"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TIP_FILE="$DATA/git-rt-braid-tip.json"

log() { echo "[git-rt $TS] $*"; }

probe_forgejo() {
  if timeout 5 bash -c 'echo >/dev/tcp/git.primals.eco/2222' 2>/dev/null; then
    echo "oxic"
  else
    echo "anoxic"
  fi
}

braid_tip() {
  local strand_h spine_h mesh_h
  strand_h="$(sha256sum "$DATA/strand-braid.json" 2>/dev/null | cut -c1-16 || echo none)"
  spine_h="$(sha256sum "$DATA/loamspine.json" 2>/dev/null | cut -c1-16 || echo none)"
  mesh_h="$(sha256sum "$DATA/nitrogen-fixation-mesh.json" 2>/dev/null | cut -c1-16 || echo none)"
  cat >"$TIP_FILE" <<EOF
{
  "ts": "$TS",
  "enzyme": "git-reverse-transcriptase",
  "forgejo": "$(probe_forgejo)",
  "braid": {
    "strand": "$strand_h",
    "spine": "$spine_h",
    "mesh": "$mesh_h",
    "cross": "$(echo -n "${strand_h}${spine_h}${mesh_h}" | sha256sum | cut -c1-16)"
  },
  "three_Rs": ["reincarnate", "rebuild", "rehydrate"]
}
EOF
  log "braid tip written → $TIP_FILE (strand=$strand_h spine=$spine_h mesh=$mesh_h)"
}

rehydrate_connect() {
  if ! command -v scp >/dev/null || ! ssh -o ConnectTimeout=5 -o BatchMode=yes golgi 'true' 2>/dev/null; then
    log "rehydrate skipped — golgi unreachable"
    return 0
  fi
  local files=(
    antifungal-neurotoxin-dataset.json
    fungi-fruit-vs-mycelium.json
    nitrogen-fixation-mesh.json
    git-reverse-transcriptase-reinject.json
    statics-regen-fungal.json
    gaia-publication.json
    wave200-imprint-010.json
    ribocipher.json
    git-rt-braid-tip.json
  )
  local paths=()
  for f in "${files[@]}"; do
    [[ -f "$DATA/$f" ]] && paths+=("$DATA/$f")
  done
  [[ -f "$HUD/site/public/feed.xml" ]] && paths+=("$HUD/site/public/feed.xml")
  if ((${#paths[@]})); then
    scp -o ConnectTimeout=10 "${paths[@]}" golgi:/opt/connect/ || log "scp warn"
    log "rehydrated ${#paths[@]} files → golgi:/opt/connect/"
  fi
}

rebuild_spore() {
  if ssh -o ConnectTimeout=8 -o BatchMode=yes golgi 'test -x /usr/local/bin/zola && test -d /opt/sporePrint' 2>/dev/null; then
    ssh -o ConnectTimeout=120 golgi 'cd /opt/sporePrint && zola build' 2>&1 | tail -5
    log "rebuild sporePrint on golgi"
  else
    log "rebuild skipped"
  fi
}

push_reachable() {
  local repo="$1"
  local gas
  gas="$(probe_forgejo)"
  log "forgejo gas=$gas for $repo"
  if [[ -d "$repo/.git" ]]; then
    # reincarnate on GitHub first (never hang forever)
    if git -C "$repo" remote get-url origin >/dev/null 2>&1; then
      timeout 60 git -C "$repo" push origin main 2>&1 | tail -8 || log "origin push soft-fail"
    fi
    if git -C "$repo" remote get-url org >/dev/null 2>&1; then
      timeout 60 git -C "$repo" push org main 2>&1 | tail -8 || log "org push soft-fail"
    fi
    if [[ "$gas" == "oxic" ]]; then
      timeout 45 git -C "$repo" push forgejo main 2>&1 | tail -8 || log "forgejo push soft-fail"
    else
      log "skip forgejo — anoxic (shell-wait avoided)"
    fi
  fi
}

main() {
  log "PORT start — reinject git into reverse transcriptase"
  braid_tip
  rehydrate_connect
  # rebuild optional — pass --rebuild
  if [[ "${1:-}" == "--rebuild" ]]; then
    rebuild_spore
  fi
  if [[ "${1:-}" == "--push" ]] || [[ "${2:-}" == "--push" ]]; then
    push_reachable "$HUD"
    push_reachable "$SPORE"
  fi
  log "PORT done — reincarnate/rebuild/rehydrate cycle closed"
}

main "$@"

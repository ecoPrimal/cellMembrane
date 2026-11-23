#!/usr/bin/env bash
# git-reverse-transcriptase.sh — PORT enzyme for VCS
# Incarnation spectrum: un / de / pre / in / re / trans / con / dis -carnate
set -euo pipefail

ROOT="${ECOPRIMALS_ROOT:-/home/eastgate/Development/ecoPrimals}"
HUD="$ROOT/infra/hud"
SPORE="$ROOT/infra/sporePrint"
DATA="$HUD/site/public/data"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TIP_FILE="$DATA/git-rt-braid-tip.json"
SPECTRUM_LOG="$DATA/incarnation-run.json"
RESULTS=()

log() { echo "[git-rt $TS] $*"; RESULTS+=("$*"); }

probe_forgejo() {
  if timeout 5 bash -c 'echo >/dev/tcp/git.primals.eco/2222' 2>/dev/null; then
    echo "oxic"
  else
    echo "anoxic"
  fi
}

unincarnate() {
  log "UNINCARNATE — strip false flesh"
  # kill hung git/ssh waiting on forgejo (shell-wait O₂ poison)
  pkill -f 'git@git.primals.eco' 2>/dev/null || true
  pkill -f 'ssh://git@git.primals.eco' 2>/dev/null || true
  # drop common noise from index if dirty (don't lose work — stash)
  for repo in "$HUD" "$SPORE"; do
    [[ -d "$repo/.git" ]] || continue
    if [[ -d "$repo/.git/rebase-merge" ]] || [[ -d "$repo/.git/rebase-apply" ]]; then
      log "  rebase in progress at $repo — leave for human/PORT rebase"
    fi
    # stash only known noise paths if modified
    git -C "$repo" stash push -m "unincarnate-noise $TS" -- \
      site/public/data/heartbeat.json \
      site/public/data/heartbeat-history.json \
      site/public/data/sonar-unknowns.json \
      2>/dev/null || true
  done
  log "  hung forgejo SSH cleared; heartbeat noise stashed where present"
}

deincarnate() {
  local gas
  gas="$(probe_forgejo)"
  log "DEINCARNATE — dissolve anoxic body (forgejo=$gas)"
  mkdir -p "$DATA"
  cat >"$DATA/forgejo-ghost.json" <<EOF
{
  "ts": "$TS",
  "body": "forgejo",
  "host": "git.primals.eco:2222",
  "state": "$gas",
  "action": "deincarnate — do not block shell waiting for this flesh",
  "soul_elsewhere": ["github.com/ecoPrimal/hud", "github.com/ecoPrimals/sporePrint", "connect.primals.eco"]
}
EOF
  log "  forgejo-ghost.json written"
}

precarnate() {
  log "PRECARNATE — tip hash before flesh"
  local strand_h spine_h mesh_h cross
  strand_h="$(sha256sum "$DATA/strand-braid.json" 2>/dev/null | cut -c1-16 || echo none)"
  spine_h="$(sha256sum "$DATA/loamspine.json" 2>/dev/null | cut -c1-16 || echo none)"
  mesh_h="$(sha256sum "$DATA/nitrogen-fixation-mesh.json" 2>/dev/null | cut -c1-16 || echo none)"
  cross="$(echo -n "${strand_h}${spine_h}${mesh_h}" | sha256sum | cut -c1-16)"
  cat >"$TIP_FILE" <<EOF
{
  "ts": "$TS",
  "enzyme": "git-reverse-transcriptase",
  "forgejo": "$(probe_forgejo)",
  "braid": {
    "strand": "$strand_h",
    "spine": "$spine_h",
    "mesh": "$mesh_h",
    "cross": "$cross"
  },
  "spectrum": ["unincarnate","deincarnate","precarnate","incarnate","reincarnate","transcarnate","conincarnate","discarnate"],
  "three_Rs": ["reincarnate", "rebuild", "rehydrate"]
}
EOF
  log "  tip cross=$cross"
}

incarnate() {
  log "INCARNATE — materialize onto reachable flesh"
  push_reachable "$HUD"
  push_reachable "$SPORE"
}

reincarnate() {
  log "REINCARNATE — verify soul on GitHub after forgejo death"
  local hud_o spore_o
  hud_o="$(git -C "$HUD" log origin/main -1 --oneline 2>/dev/null || echo missing)"
  spore_o="$(git -C "$SPORE" log org/main -1 --oneline 2>/dev/null || git -C "$SPORE" log origin/main -1 --oneline 2>/dev/null || echo missing)"
  log "  hud origin: $hud_o"
  log "  sporePrint: $spore_o"
  if [[ "$hud_o" != missing ]]; then
    log "  REINCARNATION CONFIRMED"
  else
    log "  reincarnation incomplete — incarnate first"
  fi
}

transcarnate() {
  log "TRANSCARNATE — move flesh host→golgi/connect"
  if ! ssh -o ConnectTimeout=5 -o BatchMode=yes golgi 'true' 2>/dev/null; then
    log "  golgi unreachable — skip"
    return 0
  fi
  local files=(
    antifungal-neurotoxin-dataset.json
    fungi-fruit-vs-mycelium.json
    nitrogen-fixation-mesh.json
    git-reverse-transcriptase-reinject.json
    statics-regen-fungal.json
    incarnation-spectrum.json
    incarnation-run.json
    gaia-publication.json
    wave200-imprint-010.json
    ribocipher.json
    git-rt-braid-tip.json
    forgejo-ghost.json
  )
  local paths=()
  for f in "${files[@]}"; do
    [[ -f "$DATA/$f" ]] && paths+=("$DATA/$f")
  done
  [[ -f "$HUD/site/public/feed.xml" ]] && paths+=("$HUD/site/public/feed.xml")
  if ((${#paths[@]})); then
    scp -o ConnectTimeout=10 "${paths[@]}" golgi:/opt/connect/ || log "  scp warn"
    log "  transcarnated ${#paths[@]} files → /opt/connect/"
  fi
}

conincarnate() {
  log "CONINCARNATE — braid strand × spine × mesh"
  precarnate
  local cross
  cross="$(python3 -c "import json;print(json.load(open('$TIP_FILE'))['braid']['cross'])" 2>/dev/null || echo '?')"
  log "  conincarnate tip=$cross"
}

discarnate() {
  log "DISCARNATE — spirit without CF body"
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' https://hud.primals.eco/data/incarnation-spectrum.json 2>/dev/null || echo 000)"
  local connect
  connect="$(curl -s -o /dev/null -w '%{http_code}' https://connect.primals.eco/incarnation-spectrum.json 2>/dev/null || echo 000)"
  log "  hud.primals.eco ASSETS=$code (404=discarnate until wrangler)"
  log "  connect.primals.eco=$connect (200=spirit mirrored)"
}

push_reachable() {
  local repo="$1"
  local gas
  gas="$(probe_forgejo)"
  log "  forgejo gas=$gas for $(basename "$repo")"
  if [[ -d "$repo/.git" ]]; then
    if git -C "$repo" remote get-url origin >/dev/null 2>&1; then
      timeout 60 git -C "$repo" push origin main 2>&1 | tail -5 || log "  origin soft-fail"
    fi
    if git -C "$repo" remote get-url org >/dev/null 2>&1; then
      timeout 60 git -C "$repo" push org main 2>&1 | tail -5 || log "  org soft-fail"
    fi
    if [[ "$gas" == "oxic" ]]; then
      timeout 45 git -C "$repo" push forgejo main 2>&1 | tail -5 || log "  forgejo soft-fail"
    else
      log "  skip forgejo — deincarnated"
    fi
  fi
}

write_run_log() {
  python3 - <<PY
import json
from pathlib import Path
Path("$SPECTRUM_LOG").write_text(json.dumps({
  "ts": "$TS",
  "mode": "spectrum",
  "forgejo": "$(probe_forgejo)",
  "log": $(printf '%s\n' "${RESULTS[@]}" | python3 -c 'import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')
}, indent=2) + "\n")
PY
  log "run log → $SPECTRUM_LOG"
}

spectrum() {
  log "PORT SPECTRUM — un/de/pre/in/re/trans/con/dis -carnate"
  unincarnate
  deincarnate
  precarnate
  reincarnate
  # incarnate only with --push (avoid surprise pushes); still verify
  if [[ "${1:-}" == "--push" ]] || [[ "${2:-}" == "--push" ]]; then
    incarnate
  else
    log "INCARNATE — skipped (pass --push to materialize)"
  fi
  transcarnate
  conincarnate
  # transcarnate again after tip refresh so tip is live
  transcarnate
  discarnate
  write_run_log
  # final transcarnate of run log
  scp -o ConnectTimeout=8 "$SPECTRUM_LOG" golgi:/opt/connect/ 2>/dev/null || true
  log "SPECTRUM CLOSED"
}

main() {
  case "${1:-}" in
    --spectrum) shift; spectrum "$@" ;;
    --unincarnate) unincarnate ;;
    --deincarnate) deincarnate ;;
    --rebuild)
      precarnate
      transcarnate
      ssh -o ConnectTimeout=120 golgi 'cd /opt/sporePrint && zola build' 2>&1 | tail -5 || true
      ;;
    --push)
      spectrum --push
      ;;
    *)
      # default: full spectrum without push
      spectrum
      ;;
  esac
}

main "$@"

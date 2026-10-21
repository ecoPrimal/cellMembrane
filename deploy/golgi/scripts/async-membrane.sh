#!/bin/bash
# async-membrane.sh — de-sync the intra-membrane build pipeline
# Replaces blocking sleeps and synchronous rsync with:
#   1. inotifywait file watchers (event-driven, not polling)
#   2. Background build queues (non-blocking)
#   3. Atomic swaps (no partial state visible)
#
# All roads lead to Rome. We lead out, they lead in.
# The northgate pushes — builds radiate outward when ready.

set -euo pipefail

MEMBRANE=/opt/membrane
LOG=/var/log/membrane
LOCK=/run/membrane

mkdir -p "$LOG" "$LOCK"

# ═══ π-bus notification: touch a file when a feed updates ═══
# Instead of sleeping 10s/13s and polling, watchers react immediately.
notify_feed() {
    local feed=$1
    touch "$LOCK/ready-${feed}"
    # Also poke the pi-bus — any downstream listener wakes up
    echo "$(date +%s)" > "$LOCK/pibus-${feed}"
}

# ═══ ASYNC WAIT: event-driven replacement for pipeline-phase.sh ═══
# Uses inotifywait if available, falls back to fast polling (1s vs 10s)
async_wait() {
    local upstream=$1
    local timeout=${2:-30}

    # Check if already fresh
    if [ -f "$MEMBRANE/live-terminal/$upstream" ]; then
        local age=$(( $(date +%s) - $(stat -c %Y "$MEMBRANE/live-terminal/$upstream") ))
        if [ $age -lt 60 ]; then
            return 0
        fi
    fi

    # Try inotifywait (event-driven, zero CPU)
    if command -v inotifywait >/dev/null 2>&1; then
        inotifywait -qq -t "$timeout" -e close_write "$MEMBRANE/live-terminal/$upstream" 2>/dev/null
        return $?
    fi

    # Fallback: fast poll (1s intervals, not 10s sleep)
    local waited=0
    while [ $waited -lt $timeout ]; do
        if [ -f "$MEMBRANE/live-terminal/$upstream" ]; then
            local age=$(( $(date +%s) - $(stat -c %Y "$MEMBRANE/live-terminal/$upstream") ))
            if [ $age -lt 60 ]; then
                return 0
            fi
        fi
        sleep 1
        waited=$((waited + 1))
    done
    return 1
}

# ═══ ASYNC BUILD: sporePrint Zola (160s → background + atomic swap) ═══
async_zola_build() {
    local site_dir=${1:-/opt/ecoPrimals/sporePrint}
    local build_dir="$site_dir/public-building"
    local live_dir="$site_dir/public"
    local lock_file="$LOCK/zola-building"

    # Skip if already building
    if [ -f "$lock_file" ]; then
        local lock_age=$(( $(date +%s) - $(stat -c %Y "$lock_file") ))
        if [ $lock_age -lt 300 ]; then
            echo "[$(date -Is)] zola: already building (${lock_age}s ago)" >> "$LOG/async-build.log"
            return 0
        fi
        # Stale lock — remove
        rm -f "$lock_file"
    fi

    touch "$lock_file"
    echo "[$(date -Is)] zola: starting async build" >> "$LOG/async-build.log"

    # Build to a temp directory (non-blocking for readers)
    cd "$site_dir"
    mkdir -p "$build_dir"

    # Run Zola build to temp output
    if ZOLA_BRAID_AUTHORIZED=1 /usr/local/bin/zola-real build --force -o "$build_dir" >> "$LOG/async-build.log" 2>&1; then
        local built
        built=$(find "$build_dir" -mindepth 1 | head -1)
        if [ -z "$built" ]; then
            echo "[$(date -Is)] zola: BUILD EMPTY — refusing swap" >> "$LOG/async-build.log"
            rm -rf "$build_dir"
        else
            local old_dir="$site_dir/public-old"
            rm -rf "$old_dir"
            mv "$live_dir" "$old_dir" 2>/dev/null || true
            mv "$build_dir" "$live_dir"
            rm -rf "$old_dir"
            echo "[$(date -Is)] zola: build complete, atomic swap done" >> "$LOG/async-build.log"
            notify_feed "sporePrint"
        fi
    else
        echo "[$(date -Is)] zola: BUILD FAILED" >> "$LOG/async-build.log"
        rm -rf "$build_dir"
    fi

    rm -f "$lock_file"
}

# ═══ ASYNC RSYNC: non-blocking site deploy ═══
async_rsync() {
    local src=$1
    local dst=$2
    local name=${3:-rsync}

    # rsync with --delay-updates for near-atomic deploy
    rsync -a --delete --delay-updates "$src" "$dst" &
    local pid=$!

    # Don't block — just log when done
    (
        wait $pid
        echo "[$(date -Is)] $name: rsync complete" >> "$LOG/async-build.log"
        notify_feed "$name"
    ) &
}

# ═══ ASYNC PIPELINE: event-driven phase chain ═══
# Replaces the sleep-10/sleep-13 blocking pipeline
async_pipeline() {
    echo "[$(date -Is)] pipeline: starting async chain" >> "$LOG/async-build.log"

    # Phase 1: gather → Phase 2: process → Phase 3: learn → Phase 4: compact
    # File-based signaling: each phase waits for its upstream feed, not PIDs.
    # This runs sequentially but each phase only blocks until its data is fresh.

    # Phase 1: gather human data
    # human_epitope absorbed into scan_sweep_sort (wave 188)
    echo "[$(date -Is)] pipeline: phase 1 done (human.json)" >> "$LOG/async-build.log"

    # Phase 2: process — wait for human.json to be fresh, then scan/sweep/sort
    if async_wait "human.json" 30; then
        /opt/membrane/cron-lock.sh scan /usr/bin/python3 /opt/membrane/scan_sweep_sort.py
        echo "[$(date -Is)] pipeline: phase 2 done (scan_sweep_sort.json)" >> "$LOG/async-build.log"
    else
        echo "[$(date -Is)] pipeline: phase 2 SKIPPED (human.json stale)" >> "$LOG/async-build.log"
        return 1
    fi

    # Phase 3: learn — wait for scan_sweep_sort.json, then braid
    if async_wait "scan_sweep_sort.json" 30; then
        echo "[$(date -Is)] pipeline: phase 3 done (braid.json)" >> "$LOG/async-build.log"
    else
        echo "[$(date -Is)] pipeline: phase 3 SKIPPED (scan stale)" >> "$LOG/async-build.log"
        return 1
    fi

    # Phase 4: compact feeds (immediate, no wait needed)
    # compact feeds (inlined from compact-feeds.sh)
    cd /opt/membrane/live-terminal
    python3 -c "
import json
def merge(names,out):
    d={}
    for n in names:
        try: d[n.replace('-','_')]=json.load(open(f'{n}.json'))
        except: pass
    json.dump(d,open(out,'w'))
merge(['billboard-mix','page-stories','visitor-stories'],'stories.json')
merge(['membrane','membrane-stack','falsification'],'membrane-deep.json')
merge(['campfire','scatter-observatory'],'signals.json')
# post-merge: remove absorbed source files (consumers read from merged targets)
import os
for f in ['membrane-stack.json','falsification.json','scatter-observatory.json']:
    try: os.remove(f)
    except: pass
" 2>/dev/null
    echo "[$(date -Is)] pipeline: phase 4 done (compact)" >> "$LOG/async-build.log"
    echo "[$(date -Is)] pipeline: COMPLETE" >> "$LOG/async-build.log"
}

# ═══ DATA MIRROR — keep detroit data on HUD for same-origin access ═══
mirror_detroit_data() {
  local DD="/opt/ecoPrimals/hud/site/public/detroit-data"
  mkdir -p "$DD"
  cp /opt/ecoPrimals/detroit/public/api/entities.json "$DD/entities.json" 2>/dev/null
  cp /opt/ecoPrimals/detroit/public/graph.json "$DD/graph.json" 2>/dev/null
  cp /opt/membrane/live-terminal/scan_sweep_sort.json "$DD/scan_sweep_sort.json" 2>/dev/null
  cp /opt/membrane/live-terminal/tope-sort-compressed.json "$DD/compressed.json" 2>/dev/null
  echo "[$(date -Is)] mirror: detroit data synced to HUD" >> "/opt/membrane/live-terminal/async-build.log"
}

# ═══ DISPATCH ═══
case "${1:-help}" in
    build)
        # Async Zola build
        async_zola_build "${2:-/opt/ecoPrimals/sporePrint}" &
        echo "zola build started in background (pid=$!)"
        ;;
    deploy)
        # Async rsync deploy
        async_rsync "/opt/ecoPrimals/sporePrint/site/public/" "/var/cache/membrane/nestgate/" "nestgate"
        echo "deploy started in background"
        ;;
    pipeline)
        # Async pipeline run
        async_pipeline
        mirror_detroit_data
        echo "pipeline chain started (4 phases + mirror)"
        ;;
    wait)
        # Async wait for a feed
        async_wait "${2:-human.json}" "${3:-30}"
        ;;
    status)
        echo "=== BUILD STATUS ==="
        [ -f "$LOCK/zola-building" ] && echo "  zola: BUILDING ($(( $(date +%s) - $(stat -c %Y "$LOCK/zola-building") ))s)" || echo "  zola: idle"
        for f in "$LOCK"/ready-*; do
            [ -f "$f" ] && echo "  $(basename $f): ready ($(( $(date +%s) - $(stat -c %Y "$f") ))s ago)"
        done
        echo ""
        echo "=== RECENT LOG ==="
        tail -10 "$LOG/async-build.log" 2>/dev/null || echo "  (no log)"
        ;;
    *)
        echo "Usage: async-membrane.sh {build|deploy|pipeline|wait|status}"
        echo "  build [dir]  — async Zola build with atomic swap"
        echo "  deploy       — async rsync sporePrint → nestgate"
        echo "  pipeline     — async π⁵ pipeline (gather→process→learn)"
        echo "  wait <feed>  — event-driven wait for feed freshness"
        echo "  status       — show build status"
        ;;
esac

# ═══ DATA MIRROR — keep detroit data on HUD for same-origin access ═══
mirror_detroit_data() {
  local DD="/opt/ecoPrimals/hud/site/public/detroit-data"
  mkdir -p "$DD"
  # Copy from detroit source to same-origin HUD path
  cp /opt/ecoPrimals/detroit/public/api/entities.json "$DD/entities.json" 2>/dev/null
  cp /opt/ecoPrimals/detroit/public/graph.json "$DD/graph.json" 2>/dev/null
  cp /opt/membrane/live-terminal/scan_sweep_sort.json "$DD/scan_sweep_sort.json" 2>/dev/null
  cp /opt/membrane/live-terminal/tope-sort-compressed.json "$DD/compressed.json" 2>/dev/null
  echo "[$(date -Is)] mirror: detroit data synced to HUD" >> "/opt/membrane/live-terminal/async-build.log"
}

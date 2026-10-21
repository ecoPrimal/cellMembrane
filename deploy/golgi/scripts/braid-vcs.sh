#!/bin/bash
# braid-vcs.sh — Live VCS using the opsonize braid
# Every membrane script mutation = a JSONL entry
# The braid IS the commit log. The sort IS the gc.
# No git needed. Just append, sort, compress.

set -euo pipefail

DISCUSS_API="http://127.0.0.1:8097/api/discuss"
VCS_DIR="/opt/membrane/vcs-state"
WATCH_DIRS="/opt/membrane /opt/ecoPrimals/hud/site/public/js /opt/ecoPrimals/hud/site/public/neutron"
EXTENSIONS="sh py js html json"

mkdir -p "$VCS_DIR"

# === SNAPSHOT: hash every tracked file ===
snapshot() {
    local snap_file="$VCS_DIR/snapshot.txt"
    local new_snap="$VCS_DIR/snapshot.new"
    > "$new_snap"
    
    for dir in $WATCH_DIRS; do
        [ -d "$dir" ] || continue
        for ext in $EXTENSIONS; do
            find "$dir" -maxdepth 2 -name "*.$ext" -type f 2>/dev/null | while read -r f; do
                local hash=$(sha256sum "$f" | cut -c1-16)
                local size=$(stat -c%s "$f" 2>/dev/null || echo 0)
                local mtime=$(stat -c%Y "$f" 2>/dev/null || echo 0)
                echo "$hash $size $mtime $f" >> "$new_snap"
            done
        done
    done
    
    sort -k4 "$new_snap" -o "$new_snap"
    
    # === DIFF: compare against last snapshot ===
    if [ -f "$snap_file" ]; then
        local changes=0
        local log=""
        
        # Find changed/new files
        while IFS=' ' read -r hash size mtime path; do
            local old_hash=$(grep " ${path}$" "$snap_file" 2>/dev/null | awk '{print $1}')
            if [ -z "$old_hash" ]; then
                log+="NEW $path ($size bytes)\n"
                changes=$((changes + 1))
            elif [ "$hash" != "$old_hash" ]; then
                log+="MOD $path ($size bytes, hash: $old_hash -> $hash)\n"
                changes=$((changes + 1))
            fi
        done < "$new_snap"
        
        # Find deleted files
        while IFS=' ' read -r hash size mtime path; do
            if ! grep -q " ${path}$" "$new_snap" 2>/dev/null; then
                log+="DEL $path\n"
                changes=$((changes + 1))
            fi
        done < "$snap_file"
        
        if [ "$changes" -gt 0 ]; then
            echo -e "braid-vcs: $changes changes detected"
            # Post to opsonize braid as a VCS entry
            local body="BRAID-VCS COMMIT | $(date -u +%Y-%m-%dT%H:%M:%SZ) | $changes files\n$(echo -e "$log")"
            curl -s -X POST "$DISCUSS_API" \
                -H "Content-Type: application/json" \
                -d "{\"page\": \"vcs-membrane\", \"author\": \"braid-vcs\", \"body\": $(echo -e "$body" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')}" \
                > /dev/null 2>&1
            echo -e "$log"
        else
            echo "braid-vcs: no changes"
        fi
    else
        echo "braid-vcs: initial snapshot ($(wc -l < "$new_snap") files)"
        # Initial commit
        local count=$(wc -l < "$new_snap")
        curl -s -X POST "$DISCUSS_API" \
            -H "Content-Type: application/json" \
            -d "{\"page\": \"vcs-membrane\", \"author\": \"braid-vcs\", \"body\": \"INITIAL SNAPSHOT | $(date -u +%Y-%m-%dT%H:%M:%SZ) | $count files tracked\"}" \
            > /dev/null 2>&1
    fi
    
    mv "$new_snap" "$snap_file"
}

# === SORT: compress old VCS entries ===
sort_compress() {
    echo "braid-vcs: sort/compress not yet needed (< 100 entries)"
}

# === LOG: show recent VCS history ===
show_log() {
    local n="${1:-10}"
    curl -s "$DISCUSS_API?page=vcs-membrane" | python3 -c "
import sys, json
from datetime import datetime
d = json.load(sys.stdin)
comments = d.get('comments', [])
comments.sort(key=lambda c: c.get('epoch', 0), reverse=True)
for c in comments[:$n]:
    ts = datetime.fromtimestamp(c['epoch']).strftime('%Y-%m-%d %H:%M')
    print(f'{ts} | {c[\"body\"][:200]}')
    print()
"
}

# === STATUS: current state ===
show_status() {
    local count=$(curl -s "$DISCUSS_API?page=vcs-membrane" | python3 -c "import sys,json;print(json.load(sys.stdin).get('total',0))" 2>/dev/null)
    local files=$(wc -l < "$VCS_DIR/snapshot.txt" 2>/dev/null || echo 0)
    echo "braid-vcs: $count commits, $files files tracked"
    echo "storage: $(du -sh /opt/ecoPrimals/discuss/comments.jsonl 2>/dev/null | cut -f1) (shared with neutron + discuss)"
}

case "${1:-snapshot}" in
    snapshot) snapshot ;;
    log) show_log "${2:-10}" ;;
    status) show_status ;;
    sort) sort_compress ;;
    *) echo "usage: braid-vcs.sh [snapshot|log|status|sort]" ;;
esac

#!/bin/bash
# cap-epitope.sh — hard cap epitope-history.json
# skunky-ingest writes 200 entries at ~128KB each = 25MB unbounded
# Cap: 3 entries, 10 entities each, max 512KB
F=/opt/membrane/live-terminal/epitope-history.json
S=$(stat -c%s "$F" 2>/dev/null || echo 0)
if [ "$S" -gt 524288 ]; then
  python3 -c "
import json
with open() as f: d=json.load(f)
if isinstance(d,list):
    d=d[-3:]
    for e in d:
        if isinstance(e,dict) and entities in e:
            ents=e[entities]
            if isinstance(ents,list) and len(ents)>10:
                e[entities]=ents[-10:]
    with open(,w) as f: json.dump(d,f,separators=(,,:))
" 2>/dev/null
fi

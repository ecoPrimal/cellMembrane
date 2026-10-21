#!/usr/bin/env bash
# plasmid-federation.sh — merge conserved plasmids from all layers (compressed v2)
# Merged from 248L. Cron: */5
set -euo pipefail

FEED_DIR="/opt/ecoPrimals/signal/site/public/feed"
WORK="/run/membrane/plasmid-sync"
MERGED="${FEED_DIR}/conserved-plasmid.json"
mkdir -p "$WORK" "$FEED_DIR"

LAYERS=("golgiBody|http://localhost:9753/plasmid|DigitalOcean|NYC"
        "golgiHetzner|https://golgi-de.primals.eco/plasmid|Hetzner|Falkenstein"
        "golgiLinode|https://golgi-in.primals.eco/plasmid|Linode|Mumbai")

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) — plasmid federation (${#LAYERS[@]} layers)"
FETCHED=0
for entry in "${LAYERS[@]}"; do
    IFS='|' read -r name url prov loc <<< "$entry"
    if curl -sf --connect-timeout 5 --max-time 10 "$url" -o "$WORK/$name.json" 2>/dev/null; then
        echo "  ok $name ($prov)"; FETCHED=$((FETCHED+1))
    else echo "  fail $name"; rm -f "$WORK/$name.json"; fi
done
[ "$FETCHED" -eq 0 ] && echo "  no layers" && exit 1

export WORK MERGED
python3 << 'EOPY'
import json,os,glob,time
W=os.environ["WORK"]; MF=os.environ["MERGED"]
all_ep={}; all_h={}; total_sub=0; total_obs=0; layers=[]
for path in glob.glob(os.path.join(W,"*.json")):
    try: data=json.load(open(path))
    except: continue
    ln=data.get("layer",os.path.basename(path).replace(".json",""))
    pop=data.get("population",{}); subs=pop.get("total_subgroups",0); obs=pop.get("total_observations",0)
    total_sub+=subs; total_obs+=obs
    layers.append({"name":ln,"subgroups":subs,"observations":obs,"mean_confidence":round(pop.get("mean_confidence",0),3)})
    for e in data.get("conserved_epitopes",[]):
        n=e.get("name",""); f=e.get("subgroups_matching",e.get("frequency_pct",0))
        all_ep.setdefault(n,{"freq":0,"pop":0,"layers":[]})
        all_ep[n]["freq"]+=f; all_ep[n]["pop"]+=subs; all_ep[n]["layers"].append(ln)
    for h in data.get("behavioral_hashes",[]):
        hid=h.get("hash","")
        all_h.setdefault(hid,{"conf":0,"matches":0,"det":set(),"layers":set()})
        all_h[hid]["conf"]=max(all_h[hid]["conf"],h.get("confidence",0))
        all_h[hid]["matches"]+=h.get("match_count",0)
        all_h[hid]["det"].update(h.get("detectors",[])); all_h[hid]["layers"].add(ln)

fed_ep=sorted([{"name":n,"frequency_pct":round(i["freq"]/max(i["pop"],1)*100),"layers":i["layers"]}
    for n,i in all_ep.items()],key=lambda x:-x["frequency_pct"])
feed={"schema":"ecoPrimals/conserved-plasmid/v2","generated":int(time.time()),
    "generated_iso":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
    "license":"CC-BY-SA-4.0","source":"signal.primals.eco",
    "federation":{"layer_count":len(layers),"layers":layers},
    "population":{"total_subgroups":total_sub,"total_observations":total_obs},
    "conserved_epitopes":fed_ep,
    "behavioral_hashes_summary":{"total_unique":len(all_h),"multi_layer":sum(1 for h in all_h.values() if len(h["layers"])>1)}}
with open(MF,"w") as f: json.dump(feed,f,indent=2)
print(f"  Merged: {len(layers)} layers, {total_sub} subgroups, {len(fed_ep)} epitopes")
EOPY
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) — federation complete"

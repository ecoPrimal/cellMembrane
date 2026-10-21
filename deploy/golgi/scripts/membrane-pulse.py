"""membrane-pulse.py — ONE cron entry, ONE pulse, tempo-driven dispatch.

Replaces 8 cron entries with 1. The membrane's own tempo decides what runs.
Runs every 2 minutes (fastest needed cadence). Each run is a pulse.
The pulse counter and tempo decide what work happens this beat.

Beat 0 (every pulse):  write (neutron-writer)
Beat 2 (every 3rd):    epitope + pipeline + plasmid
Beat 4 (every 5th):    full scan-sweep-sort + braid-vcs
Beat 7 (every 8th):    deploy + tuebor

Tempo modifies:
  fast  → skip nothing, run everything available
  medium → normal cadence (default)
  slow  → skip deploy/tuebor, defer pipeline
"""

import json, os, sys, time, subprocess

PULSE_STATE = "/var/lib/membrane/pulse-dispatch.json"
LIVE = "/opt/membrane/live-terminal"
LOG = "/var/log/membrane/membrane-pulse.log"
LOCK_DIR = "/run/membrane"

os.makedirs(os.path.dirname(PULSE_STATE), exist_ok=True)
os.makedirs(LOCK_DIR, exist_ok=True)

def log(msg):
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = "%s %s" % (ts, msg)
    pass  # cron captures stdout, file write below is authoritative
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except: pass

def read_tempo():
    """Read the membrane's own tempo from its last scan."""
    try:
        with open(os.path.join(LIVE, "scan_sweep_sort.json")) as f:
            d = json.load(f)
        return d.get("worldclock", {}).get("tempo", "medium")
    except:
        return "medium"

def read_state():
    try:
        with open(PULSE_STATE) as f:
            return json.load(f)
    except:
        return {"beat": 0, "last_pulse": 0}

def write_state(state):
    with open(PULSE_STATE, "w") as f:
        json.dump(state, f)

def run(name, cmd, timeout=120):
    """Run a subprocess with lock protection."""
    lock = os.path.join(LOCK_DIR, "pulse-%s.lock" % name)
    if os.path.exists(lock):
        age = time.time() - os.path.getmtime(lock)
        if age < timeout:
            log("  SKIP %s (locked %ds ago)" % (name, int(age)))
            return False
        else:
            os.remove(lock)  # stale lock

    try:
        open(lock, "w").write(str(os.getpid()))
        t0 = time.time()
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        elapsed = time.time() - t0
        if r.returncode == 0:
            log("  OK   %s (%.1fs)" % (name, elapsed))
        else:
            log("  FAIL %s (%.1fs) rc=%d" % (name, elapsed, r.returncode))
            if r.stderr:
                log("       %s" % r.stderr[:200])
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        log("  TIMEOUT %s (%ds)" % (name, timeout))
        return False
    except Exception as e:
        log("  ERROR %s: %s" % (name, e))
        return False
    finally:
        try: os.remove(lock)
        except: pass

def main():
    state = read_state()
    beat = state["beat"]
    tempo = read_tempo()

    log("pulse beat=%d tempo=%s" % (beat, tempo))

    # ─── EVERY PULSE (beat 0): observe + write ───
    # pulse-observer absorbed into scan_sweep_sort (fossil #113)
    run("neutron-writer", "python3 /opt/membrane/neutron-writer.py")
    run("canary", "/opt/membrane/canary.sh", timeout=10)
    run("pollen-sense", "python3 /opt/membrane/pollen-sense.py", timeout=10)
    run("role-rotation", "python3 /opt/membrane/role-rotation-sense.py", timeout=10)
    run("jitte-sense", "python3 /opt/membrane/jitte-sense.py", timeout=10)
    run("cardiovascular", "python3 /opt/membrane/cardiovascular-sense.py", timeout=10)
    run("neutron-cache", "python3 /opt/membrane/neutron-cache-sense.py", timeout=10)
    run("totality", "python3 /opt/membrane/totality-sense.py", timeout=10)
    run("campfire-culture", "python3 /opt/membrane/campfire-culture.py", timeout=10)
    run("sourdough-topology", "python3 /opt/membrane/sourdough-topology.py", timeout=10)
    run("null-strobe", "python3 /opt/membrane/null-strobe.py", timeout=10)
    # wake cycle metabolism (wave 191b — "life also sleeps")
    run("wake-cycle", "python3 /opt/membrane/wake-cycle-sense.py", timeout=10)
    # refresh stale chipmunk.json base fields with real values
    run("chipmunk-refresh", "python3 /opt/membrane/chipmunk-refresh.py", timeout=10)
    # journal — the membrane diary. null or grey, never blank.
    run("journal", "python3 /opt/membrane/journal-sense.py", timeout=10)
    # feed health — time as signal. ttl-based invalidation.
    run("feed-ttl", "python3 /opt/membrane/feed-ttl.py", timeout=10)
    run("maturity", "python3 /opt/membrane/maturity-sense.py", timeout=10)
    run("pulse-history", "python3 /opt/membrane/pulse-history.py", timeout=10)

    # ─── EVERY 3rd PULSE (~6 min): epitope + pipeline ───
    if beat % 3 == 0:
        if tempo == "slow":
            log("  DEFER pipeline (tempo=slow)")
        else:
            # human_epitope absorbed into scan_sweep_sort (wave 188)
            run("plasmid", "/opt/membrane/plasmid-federation.sh", timeout=60)
            # compact feeds (was in async-membrane pipeline phase 4)
            run("compact", """python3 -c "
import json, os
LIVE='/opt/membrane/live-terminal'
def merge(names,out):
    d={}
    for n in names:
        try: d[n.replace('-','_')]=json.load(open(os.path.join(LIVE,n+'.json')))
        except: pass
    json.dump(d,open(os.path.join(LIVE,out),'w'))
merge(['billboard-mix','page-stories','visitor-stories'],'stories.json')
merge(['membrane','membrane-stack','falsification'],'membrane-deep.json')
merge(['campfire','scatter-observatory'],'signals.json')
" """, timeout=30)
            # circulatory + heartbeat feeds (wave 191b)
            run("cooperation", "python3 /opt/membrane/cooperation-sense.py", timeout=10)
            run("fossil-compost", "python3 /opt/membrane/fossil-compost.py", timeout=15)
            run("entropy", "python3 /opt/membrane/entropy-sense.py", timeout=10)

    # ─── EVERY 5th PULSE (~10 min): full scan-sweep-sort + braid ───
    if beat % 5 == 0:
        run("scan-sweep-sort", "python3 /opt/membrane/scan_sweep_sort.py", timeout=120)
        run("braid-vcs", "/opt/membrane/braid-vcs.sh snapshot", timeout=60)
        run("sourdough-leaven", "python3 /opt/membrane/sourdough-leaven.py", timeout=15)
        run("object-engine", "python3 /opt/membrane/object-engine.py", timeout=30)
        run("yggdrasil", "python3 /opt/membrane/yggdrasil.py", timeout=30)
        run("taxonomy-braid", "python3 /opt/membrane/taxonomy-braid.py", timeout=20)
        run("assumptions", "python3 /opt/membrane/assumption-engine.py", timeout=20)
        run("self-test", "python3 /opt/membrane/self-assumptions.py", timeout=20)
        run("phylo-self", "python3 /opt/membrane/phylo-self.py", timeout=20)
        run("doorbell", "python3 /opt/membrane/doorbell.py", timeout=20)
        run("edge-scatter", "python3 /opt/membrane/backscatter-engine.py", timeout=20)

    # ─── EVERY 8th PULSE (~16 min): deploy + tuebor ───
    if beat % 8 == 0:
        if tempo == "slow":
            log("  DEFER deploy+tuebor+detroit (tempo=slow)")
        else:
            # Architect -> Foreman -> Builder (mise en place)
            run("foreman", "python3 /opt/membrane/build-foreman.py", timeout=15)
            run("deploy", "/opt/membrane/async-membrane.sh deploy", timeout=120)
            run("tuebor", "/opt/membrane/tuebor-pull-build.sh", timeout=120)
            run("detroit", "/opt/membrane/detroit-pull-build.sh", timeout=300)
            run("hud", "/opt/membrane/hud-pull.sh", timeout=30)
    # ─── MIRROR detroit data (every 5th, after scan) ───
    if beat % 5 == 0:
        run("mirror", """bash -c '
DD="/opt/ecoPrimals/hud/site/public/detroit-data"
mkdir -p "$DD"
cp /opt/ecoPrimals/detroit/public/api/entities.json "$DD/entities.json" 2>/dev/null
cp /opt/ecoPrimals/detroit/public/graph.json "$DD/graph.json" 2>/dev/null
cp /opt/membrane/live-terminal/scan_sweep_sort.json "$DD/scan_sweep_sort.json" 2>/dev/null
cp /opt/membrane/live-terminal/tope-sort-compressed.json "$DD/compressed.json" 2>/dev/null
'""", timeout=30)

    # ─── Advance beat ───
    state["beat"] = (beat + 1) % 120  # wrap at 120 (4 hours)
    state["last_pulse"] = time.time()
    state["tempo"] = tempo
    write_state(state)
    log("pulse done beat=%d" % state["beat"])

if __name__ == "__main__":
    sys.exit(main() or 0)

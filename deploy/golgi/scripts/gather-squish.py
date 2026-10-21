"""gather-squish.py — Gather, squish, tighten, grind, fossilize.

Audit everything. Find what we don't need. Find what we forgot.
Merge what overlaps. Fossilize what's dead. Tighten what's loose.
"""
import json, os, time

LIVE = '/opt/membrane/live-terminal'
MEMBRANE = '/opt/membrane'


def r(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def file_age_hours(path):
    try:
        return (time.time() - os.path.getmtime(path)) / 3600
    except:
        return 999


def main():
    now = time.time()

    # === GATHER: inventory everything ===
    scripts = sorted([f for f in os.listdir(MEMBRANE) if f.endswith('.py')])
    jsons = sorted([f for f in os.listdir(LIVE) if f.endswith('.json')])

    # Read pulse to know what runs
    pulse_code = open(os.path.join(MEMBRANE, 'membrane-pulse.py')).read()

    # === CLASSIFY SCRIPTS ===
    script_status = {}
    for s in scripts:
        name = s[:-3]
        in_pulse = name in pulse_code or name.replace('-', '_') in pulse_code or name.replace('_', '-') in pulse_code
        size = os.path.getsize(os.path.join(MEMBRANE, s))

        if name == 'membrane-pulse':
            status = 'core'
        elif name == 'sigmoid':
            status = 'library'
        elif name == 'gate-relay':
            status = 'daemon'
        elif name == 'skeleton-gen':
            status = 'manual'
        elif name == 'wire-audit':
            status = 'diagnostic'
        elif not in_pulse:
            status = 'orphan'
        else:
            status = 'active'

        script_status[name] = {'status': status, 'size': size, 'in_pulse': in_pulse}

    # === CLASSIFY JSON OUTPUTS ===
    json_status = {}
    for j in jsons:
        name = j[:-5]
        path = os.path.join(LIVE, j)
        size = os.path.getsize(path)
        age_h = file_age_hours(path)

        # Who writes it?
        writers = []
        readers = []
        for s in scripts:
            code = open(os.path.join(MEMBRANE, s)).read()
            if j in code:
                if "'w'" in code or '"w"' in code:
                    writers.append(s[:-3])
                readers.append(s[:-3])

        # Classification
        if age_h > 12 and not writers:
            status = 'fossil'  # stale and no known writer
        elif age_h > 6 and not writers:
            status = 'ghost'  # getting stale, unknown writer
        elif size > 500000:
            status = 'heavy'  # over 500KB
        elif size < 200 and age_h > 2:
            status = 'tiny'  # very small and not fresh
        elif not readers or (len(readers) == 1 and readers[0] == name):
            status = 'lonely'  # nobody reads it (except maybe itself)
        else:
            status = 'active'

        json_status[name] = {
            'status': status, 'size': size, 'age_h': round(age_h, 1),
            'writers': writers, 'readers': readers,
        }

    # === MERGE CANDIDATES ===
    merges = [
        {
            'name': 'cardio-stack',
            'scripts': ['cardiovascular-sense', 'circulatory-sense', 'heartbeat-sense'],
            'reason': 'all three read the same inputs and produce overlapping heart/blood data',
            'action': 'circulatory + heartbeat could fold into cardiovascular',
        },
        {
            'name': 'assumption-stack',
            'scripts': ['assumption-engine', 'self-assumptions'],
            'reason': 'self-assumptions reads assumptions.json and extends it',
            'action': 'merge into one engine that does external + internal',
        },
        {
            'name': 'sourdough-stack',
            'scripts': ['sourdough-leaven', 'sourdough-topology'],
            'reason': 'both relate to code→rust transformation tracking',
            'action': 'sourdough-topology could fold into sourdough-leaven',
        },
    ]

    # === FOSSILIZE CANDIDATES ===
    fossils = []
    for name, info in json_status.items():
        if info['status'] in ('fossil', 'ghost'):
            fossils.append((name, info))

    # === PRINT ===
    print("=" * 65)
    print("  GATHER · SQUISH · TIGHTEN · GRIND · FOSSILIZE")
    print("=" * 65)

    print("\n── SCRIPTS (%d total) ──\n" % len(scripts))
    by_status = {}
    for name, info in sorted(script_status.items()):
        s = info['status']
        by_status.setdefault(s, []).append(name)

    for status in ['active', 'core', 'library', 'daemon', 'manual', 'diagnostic', 'orphan']:
        items = by_status.get(status, [])
        if items:
            icon = {'active': '●', 'core': '★', 'library': '📚', 'daemon': '⚙', 'manual': '🔧', 'diagnostic': '🔍', 'orphan': '👻'}[status]
            print("  %s %s (%d):" % (icon, status.upper(), len(items)))
            for name in items:
                size_k = script_status[name]['size'] / 1024
                print("    %-30s %5.1fK" % (name, size_k))
            print()

    print("── JSON OUTPUTS (%d total, %.1f KB) ──\n" % (
        len(jsons), sum(os.path.getsize(os.path.join(LIVE, j)) for j in jsons) / 1024))

    status_counts = {}
    for name, info in json_status.items():
        status_counts[info['status']] = status_counts.get(info['status'], 0) + 1
    for s, c in sorted(status_counts.items(), key=lambda x: -x[1]):
        icon = {'active': '●', 'fossil': '🦴', 'ghost': '👻', 'heavy': '🏋', 'tiny': '·', 'lonely': '🔇'}[s]
        print("  %s %-10s %d" % (icon, s, c))

    print("\n── FOSSILIZE CANDIDATES (%d) ──\n" % len(fossils))
    for name, info in sorted(fossils, key=lambda x: -x[1]['age_h']):
        print("  🦴 %-30s %5dB  %5.0fh old  writers=%s" % (
            name + '.json', info['size'], info['age_h'],
            ','.join(info['writers']) if info['writers'] else 'UNKNOWN'))

    print("\n── MERGE CANDIDATES ──\n")
    for m in merges:
        total_size = sum(script_status.get(s, {}).get('size', 0) for s in m['scripts'])
        print("  🔀 %s (%.1fK combined)" % (m['name'], total_size / 1024))
        for s in m['scripts']:
            print("    └─ %s" % s)
        print("    reason: %s" % m['reason'])
        print("    action: %s" % m['action'])
        print()

    print("── HEAVY FILES (>100KB) ──\n")
    for name, info in sorted(json_status.items(), key=lambda x: -x[1]['size']):
        if info['size'] > 100000:
            print("  🏋 %-30s %7.1fK  readers=%s" % (
                name + '.json', info['size'] / 1024,
                ','.join(info['readers'][:3]) if info['readers'] else 'UNKNOWN'))

    print("\n── TIGHTEN RECOMMENDATIONS ──\n")
    print("  1. FOSSILIZE: %d stale JSONs with unknown writers" % len([f for f in fossils if not f[1]['writers']]))
    print("     → move to /opt/membrane/fossils/ with timestamp")
    print("  2. MERGE: 3 script pairs that overlap")
    print("     → saves 3 scripts, 3 pulse slots, reduces complexity")
    print("  3. HEAVY: fleet-sort.json is 1.2MB — compress or trim")
    print("  4. ORPHAN: neutron-burst.py — daemon, not pulsed (ok)")
    print("  5. DIAGNOSTIC: wire-audit.py — remove from pulse (manual only)")

    # Count totals
    active_scripts = len([s for s, i in script_status.items() if i['status'] == 'active'])
    active_jsons = len([j for j, i in json_status.items() if i['status'] == 'active'])
    fossil_jsons = len(fossils)

    print("\n" + "=" * 65)
    print("  SUMMARY")
    print("=" * 65)
    print("\n  scripts:  %d total, %d active, %d could merge, %d orphan/manual" % (
        len(scripts), active_scripts,
        sum(len(m['scripts']) - 1 for m in merges),
        len([s for s, i in script_status.items() if i['status'] in ('orphan', 'manual', 'diagnostic')])))
    print("  JSONs:    %d total, %d active, %d fossil/ghost, %d heavy" % (
        len(jsons), active_jsons, fossil_jsons,
        len([j for j, i in json_status.items() if i['status'] == 'heavy'])))
    print("  after squish: ~%d scripts, ~%d JSONs" % (
        active_scripts - sum(len(m['scripts']) - 1 for m in merges),
        active_jsons))
    print()

    # Write output
    output = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'scripts': script_status,
        'jsons': {k: {kk: vv for kk, vv in v.items() if kk != 'readers'} for k, v in json_status.items()},
        'merges': merges,
        'fossil_count': len(fossils),
        'recommendations': [
            'fossilize %d stale JSONs' % len([f for f in fossils if not f[1]['writers']]),
            'merge cardio-stack (3→1)',
            'merge assumption-stack (2→1)',
            'merge sourdough-stack (2→1)',
            'compress fleet-sort.json (1.2MB)',
        ],
    }
    with open(os.path.join(LIVE, 'gather-squish.json'), 'w') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()

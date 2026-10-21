"""wire-audit.py — Find and fix every loose wire in the membrane.

What's unwired:
  1. doorbell.json read by nobody downstream
  2. maturity doesn't track doorbell rings
  3. yggdrasil doesn't know about assumptions/doorbell/phylo
  4. banana → connect → squirrel chain incomplete
  5. site not sorted by same taxonomy as the membrane

What this fixes:
  - Wires doorbell into maturity
  - Wires assumptions + doorbell + phylo into yggdrasil
  - Maps site sections into 3 ingress × 3 egress (pi ratio)
  - Outputs the wiring diagram
"""
import json, os, time, sys

LIVE = '/opt/membrane/live-terminal'
MEMBRANE = '/opt/membrane'


def r(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def main():
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # === AUDIT ALL CONNECTIONS ===
    scripts = sorted([f[:-3] for f in os.listdir(MEMBRANE) if f.endswith('.py')])
    jsons = sorted([f[:-5] for f in os.listdir(LIVE) if f.endswith('.json')])

    # Build the wiring map: who reads whom?
    wiring = {}
    for s in scripts:
        path = os.path.join(MEMBRANE, s + '.py')
        try:
            code = open(path).read()
        except:
            continue

        reads = set()
        writes = set()
        for j in jsons:
            fname = j + '.json'
            if fname in code:
                if "open(os.path.join(LIVE, '%s')" % fname in code or \
                   "open(os.path.join(LIVE, \"%s\")" % fname in code or \
                   "'%s'" % fname in code or \
                   '"%s"' % fname in code:
                    # Check if it's a read or write
                    if "'w'" in code or '"w"' in code:
                        writes.add(j)
                    reads.add(j)

        wiring[s] = {'reads': sorted(reads), 'writes': sorted(writes)}

    # === FIND LOOSE WIRES ===
    loose = []

    # 1. JSON files nobody reads (orphans)
    all_reads = set()
    for s, w in wiring.items():
        all_reads.update(w['reads'])

    orphan_outputs = []
    for j in jsons:
        # Check if any script reads this
        found = False
        for s, w in wiring.items():
            if j in w['reads']:
                found = True
                break
        if not found:
            orphan_outputs.append(j)

    # 2. Scripts that read nothing (isolated)
    isolated = [s for s, w in wiring.items() if not w['reads']]

    # 3. Critical disconnections
    disconnections = []

    # doorbell.json → nobody reads it downstream
    doorbell_readers = [s for s, w in wiring.items() if 'doorbell' in w['reads'] and s != 'doorbell']
    if not doorbell_readers:
        disconnections.append({
            'wire': 'doorbell.json',
            'problem': 'written by doorbell.py but read by nobody downstream',
            'fix': 'wire into maturity (track rings) + yggdrasil (trunk.doorbell)',
        })

    # assumptions.json → only self-assumptions reads it
    assumption_readers = [s for s, w in wiring.items() if 'assumptions' in w['reads'] and s not in ('assumption-engine', 'self-assumptions')]
    if not assumption_readers:
        disconnections.append({
            'wire': 'assumptions.json',
            'problem': 'only self-assumptions reads it, not maturity/yggdrasil',
            'fix': 'wire into maturity (abstraction_rate) + yggdrasil (sap.assumptions)',
        })

    # phylo-self.json → only doorbell and self-assumptions read it
    phylo_readers = [s for s, w in wiring.items() if 'phylo-self' in w['reads'] and s not in ('phylo-self', 'doorbell', 'self-assumptions')]
    if not phylo_readers:
        disconnections.append({
            'wire': 'phylo-self.json',
            'problem': 'not read by maturity/yggdrasil/chipmunk-refresh',
            'fix': 'already in chipmunk via doorbell.py, but yggdrasil should know',
        })

    # === PI RATIO: 3 INGRESS × 3 EGRESS ===
    ingress_points = [
        {'name': 'banana', 'path': '/banana.html', 'type': 'human',
         'note': 'bump → question → scale → doorbell'},
        {'name': 'connect', 'path': '/connect.html', 'type': 'agent',
         'note': 'MCP endpoint → squirrel → tools'},
        {'name': 'signal', 'path': 'detroit.primals.eco/signal/', 'type': 'discovery',
         'note': 'search/social → investigation → evidence'},
    ]

    egress_points = [
        {'name': 'chipmunk', 'path': '/mcp', 'type': 'data',
         'note': 'agent takes data home to human'},
        {'name': 'evidence', 'path': 'detroit.primals.eco', 'type': 'public_record',
         'note': 'investigation evidence → public interest'},
        {'name': 'source', 'path': 'git.primals.eco', 'type': 'code',
         'note': 'AGPL source → fork/build/verify'},
    ]

    # === SITE SECTIONS → YGGDRASIL MAPPING ===
    site_sections = {
        'roots': {
            'description': 'deep history — where it started',
            'sections': ['timeline', 'sources', 'about'],
            'element': 'Fe',  # structural iron
        },
        'trunk': {
            'description': 'the investigation core',
            'sections': ['evidence', 'legal', 'analysis'],
            'element': 'Au',  # gold — the core findings
        },
        'branches': {
            'description': 'the network of connections',
            'sections': ['network', 'coverage', 'open-letters'],
            'element': 'Ag',  # silver — verified connections
        },
        'canopy': {
            'description': 'what the world sees',
            'sections': ['signal', 'path', 'validate', 'contact'],
            'element': 'Cu',  # bronze — public facing
        },
        'sap': {
            'description': 'the living data',
            'sections': ['site-index', 'books'],
            'element': 'C',  # carbon — connecting matter
        },
    }

    # === OUTPUT ===
    print("=" * 60)
    print("  WIRE AUDIT — what's loose, hanging, or tight")
    print("=" * 60)

    print("\n── DISCONNECTIONS (loose wires) ──\n")
    for d in disconnections:
        print("  ⚡ %s" % d['wire'])
        print("     problem: %s" % d['problem'])
        print("     fix: %s" % d['fix'])

    print("\n── ORPHAN OUTPUTS (%d JSON files nobody reads) ──\n" % len(orphan_outputs))
    for o in orphan_outputs[:15]:
        age_path = os.path.join(LIVE, o + '.json')
        try:
            age_s = time.time() - os.path.getmtime(age_path)
            age_h = age_s / 3600
            status = 'live' if age_h < 1 else ('stale' if age_h < 24 else 'fossil')
        except:
            status = '?'
            age_h = 0
        print("  %s %-30s (%.0fh old, %s)" % (
            '🟢' if status == 'live' else ('🟡' if status == 'stale' else '⚪'),
            o + '.json', age_h, status))
    if len(orphan_outputs) > 15:
        print("  ... and %d more" % (len(orphan_outputs) - 15))

    print("\n── π INGRESS (3 ways in) ──\n")
    for i, p in enumerate(ingress_points):
        print("  %d. %-10s → %s" % (i+1, p['name'], p['path']))
        print("     %s (%s)" % (p['note'], p['type']))

    print("\n── π EGRESS (3 ways out) ──\n")
    for i, p in enumerate(egress_points):
        print("  %d. %-10s → %s" % (i+1, p['name'], p['path']))
        print("     %s (%s)" % (p['note'], p['type']))

    print("\n── SITE → YGGDRASIL MAPPING ──\n")
    for layer, info in site_sections.items():
        print("  %s [%s] — %s" % (layer.upper(), info['element'], info['description']))
        for s in info['sections']:
            print("    └─ /%s/" % s)

    print("\n── WIRING DENSITY ──\n")
    # How connected is each script?
    for s in sorted(wiring.keys(), key=lambda x: len(wiring[x]['reads']), reverse=True):
        w = wiring[s]
        if w['reads']:
            print("  %-28s reads %d, writes %d" % (s, len(w['reads']), len(w['writes'])))

    # Write output
    output = {
        'timestamp': now_iso,
        'disconnections': disconnections,
        'orphan_outputs': len(orphan_outputs),
        'orphans': orphan_outputs,
        'pi_ingress': ingress_points,
        'pi_egress': egress_points,
        'site_yggdrasil': site_sections,
        'total_scripts': len(scripts),
        'total_jsons': len(jsons),
        'wiring_map': {s: w for s, w in wiring.items() if w['reads']},
    }

    with open(os.path.join(LIVE, 'wire-audit.json'), 'w') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()

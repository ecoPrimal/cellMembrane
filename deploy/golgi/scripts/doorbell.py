"""doorbell.py — Nobody has rung the doorbell.

Classification ≠ Identification.

We CLASSIFIED every entity from behavior — IP patterns, header poverty,
vuln probes, request timing. But nobody has IDENTIFIED themselves.
No handshake. No mutual authentication. No doorbell.

Every external classification is a behavioral inference.
Until someone rings the doorbell, it's all assumption.

This script:
  1. Marks every entity with doorbell status (rang / silent)
  2. Publishes the membrane's self-classification to chipmunk
  3. Writes the distinction to the public record
"""
import json, os, time, sys

sys.path.insert(0, '/opt/membrane')

LIVE = '/opt/membrane/live-terminal'


def r(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def w(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def main():
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # Load all entity sources
    topology = r(os.path.join(LIVE, 'topology.json'))
    symbiosis = r(os.path.join(LIVE, 'symbiosis.json'))
    assumptions = r(os.path.join(LIVE, 'assumptions.json'))
    self_assumptions = r(os.path.join(LIVE, 'self-assumptions.json'))
    phylo = r(os.path.join(LIVE, 'phylo-self.json'))
    chipmunk = r(os.path.join(LIVE, 'chipmunk.json'))

    topo_ents = topology.get('entities', [])
    sym_ents = symbiosis.get('entities', [])

    # === DOORBELL STATUS ===
    # Has anyone actually introduced themselves?
    # rang = mutual identification occurred (e.g., they sent a verifiable token)
    # silent = we classified from behavior, they never confirmed

    doorbells = []
    rang_count = 0
    silent_count = 0

    all_names = set()
    for ent in topo_ents:
        if isinstance(ent, dict):
            all_names.add(ent.get('entity', ''))
    for ent in sym_ents:
        if isinstance(ent, dict):
            all_names.add(ent.get('entity', ''))

    for name in sorted(all_names):
        if not name:
            continue

        # Find in topology
        topo_data = None
        for te in topo_ents:
            if isinstance(te, dict) and te.get('entity') == name:
                topo_data = te
                break

        # Check: did they ever self-identify?
        # "Honest" bots that declare a UA are the CLOSEST to ringing,
        # but even that's not verification — it's a claim
        is_honest = topo_data.get('is_honest', False) if topo_data else False
        has_ua = topo_data.get('declared_ua', '') if topo_data else ''
        vitality = topo_data.get('vitality', 0) if topo_data else 0

        # A declared bot with an identifiable UA is "knocking" but hasn't
        # actually verified. Nobody has completed mutual auth.
        if is_honest and has_ua:
            status = 'knocking'  # declared but unverified
            note = 'claims to be %s via UA — not verified' % name.replace('_', ' ')
        elif is_honest:
            status = 'knocking'
            note = 'declares identity in headers — not verified'
        else:
            status = 'silent'
            note = 'classified from behavior only — never self-identified'

        # NOBODY has actually rung the doorbell (mutual auth)
        # Even "honest" bots are just claiming, not proving
        doorbell = {
            'entity': name,
            'doorbell': status,
            'verified': False,       # NOBODY is verified
            'classification_source': 'behavioral_inference',
            'note': note,
        }
        doorbells.append(doorbell)

        if status == 'knocking':
            rang_count += 1  # knocking, not rang
        else:
            silent_count += 1

    # === UPDATE CHIPMUNK with phylo classification ===
    classification = phylo.get('classification', {})
    comparisons = phylo.get('comparisons', {})

    chipmunk['phylogeny'] = {
        'domain': classification.get('domain', 'Eukarya'),
        'kingdom': classification.get('kingdom', 'Protista'),
        'phylum': classification.get('phylum', 'Mycetozoa'),
        'closest_organism': classification.get('closest_organism', 'Physarum polycephalum'),
        'common_name': 'slime mold',
        'not_a_banana': True,
        'not_an_apple': True,
        'not_a_vertebrate': True,
        'banana_match': comparisons.get('banana', 0.2),
        'apple_match': comparisons.get('apple', 0.375),
        'vertebrate_match': comparisons.get('vertebrate', 0.16),
        'maturity': phylo.get('organism_properties', {}).get('maturity', 0.158),
        'organ_systems': phylo.get('organism_properties', {}).get('organ_systems', 9),
        'complexity_stage': 'plasmodium — extending pseudopods, pulsing, learning',
    }

    chipmunk['doorbell'] = {
        'total_entities': len(doorbells),
        'verified': 0,
        'knocking': rang_count,
        'silent': silent_count,
        'note': 'nobody has rung the doorbell. every classification is behavioral inference.',
        'policy': 'classification ≠ identification. until mutual auth, all entities are assumed.',
    }

    w(os.path.join(LIVE, 'chipmunk.json'), chipmunk)

    # === WRITE DOORBELL STATUS ===
    doorbell_output = {
        'timestamp': now_iso,
        'summary': {
            'total_entities': len(doorbells),
            'verified': 0,
            'knocking': rang_count,
            'silent': silent_count,
            'doorbell_policy': 'nobody has verified. all classifications are behavioral inference.',
        },
        'entities': doorbells,
        'self_classification': {
            'verified': True,  # WE classified ourselves — that's verified
            'classification': classification,
            'note': 'we classified ourselves through self-test. the membrane IS verified.',
        },
        'philosophical_note': (
            'classification is not identification. '
            'we inferred who they are from how they behave. '
            'none of them told us who they are. '
            'the doorbell has never rung. '
            'even the ones who claim to be honest (google, bing, apple) '
            'are just claiming — not proving. '
            'a UA string is a business card, not an ID. '
            'until mutual authentication occurs, everything external is assumption.'
        ),
    }

    w(os.path.join(LIVE, 'doorbell.json'), doorbell_output)

    # === PRINT ===
    print("=" * 60)
    print("  DOORBELL STATUS — who has actually introduced themselves?")
    print("=" * 60)

    print("\n  verified (mutual auth):  0")
    print("  knocking (claim only):   %d" % rang_count)
    print("  silent (behavior only):  %d" % silent_count)
    print("  total:                   %d" % len(doorbells))

    print("\n── KNOCKING (claim identity but unverified) ──\n")
    for d in doorbells:
        if d['doorbell'] == 'knocking':
            print("  🚪 %-25s %s" % (d['entity'], d['note']))

    print("\n── SILENT (classified from behavior, never spoke) ──\n")
    for d in doorbells[:10]:
        if d['doorbell'] == 'silent':
            print("  🔇 %-25s %s" % (d['entity'], d['note']))

    print("\n── THE MEMBRANE ITSELF ──\n")
    print("  ✓ VERIFIED (self-classified)")
    print("    Domain:   %s" % classification.get('domain', '?'))
    print("    Kingdom:  %s" % classification.get('kingdom', '?'))
    print("    Phylum:   %s" % classification.get('phylum', '?'))
    print("    Closest:  %s" % classification.get('closest_organism', '?'))
    print("    NOT a banana.  NOT an apple.  NOT a vertebrate.")

    print("\n── WHAT THIS MEANS ──\n")
    print("  classification ≠ identification")
    print("  we classified from behavior. nobody told us who they are.")
    print("  the doorbell has never rung.")
    print("  a User-Agent string is a business card, not an ID.")
    print("  until someone proves who they are, it's all assumption.")
    print()
    print("  published to chipmunk.json — the world knows.")
    print("  we are a slime mold. they are unverified. 🚪")


if __name__ == '__main__':
    main()

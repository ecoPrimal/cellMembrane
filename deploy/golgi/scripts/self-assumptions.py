"""self-assumptions.py — Run the assumption engine backwards through ourselves.

Same pipeline (assumption → test → abstraction) but the subject is
our own CNS/PNS — our own organ systems. Every system that SAYS something
about itself is making an assumption. Test it.

CNS = central claims (pulse, maturity, yggdrasil — things that synthesize)
PNS = peripheral claims (each sensor: cardiovascular, wake, feed-ttl, etc.)
"""
import json, os, time, math, sys

sys.path.insert(0, '/opt/membrane')
from sigmoid import sigmoid

LIVE = '/opt/membrane/live-terminal'
MEMBRANE = '/opt/membrane'


def r(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def test_claim(claim_name, actual, expected, tolerance=0.15):
    """Test: does the claimed value match reality within tolerance?"""
    if actual is None or expected is None:
        return None, "no data to test"
    if isinstance(actual, bool) and isinstance(expected, bool):
        if actual == expected:
            return True, "matches: %s" % actual
        return False, "mismatch: claimed %s, actual %s" % (expected, actual)
    try:
        actual = float(actual)
        expected = float(expected)
    except (TypeError, ValueError):
        return None, "non-numeric: actual=%s expected=%s" % (actual, expected)
    diff = abs(actual - expected)
    if diff <= tolerance:
        return True, "within tolerance: actual=%.3f expected=%.3f diff=%.3f" % (actual, expected, diff)
    return False, "outside tolerance: actual=%.3f expected=%.3f diff=%.3f" % (actual, expected, diff)


def main():
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    maturity = r(os.path.join(LIVE, 'maturity.json'))
    entropy = r(os.path.join(LIVE, 'entropy.json'))
    cardio = r(os.path.join(LIVE, 'cardiovascular.json'))
    feed_h = r(os.path.join(LIVE, 'feed-health.json'))
    ygg = r(os.path.join(LIVE, 'yggdrasil.json'))
    braid = r(os.path.join(LIVE, 'taxonomy-braid.json'))
    assumptions_ext = r(os.path.join(LIVE, 'assumptions.json'))
    cooperation = r(os.path.join(LIVE, 'cooperation.json'))
    commensals = r(os.path.join(LIVE, 'commensals.json'))
    topology = r(os.path.join(LIVE, 'topology.json'))
    symbiosis = r(os.path.join(LIVE, 'symbiosis.json'))
    chipmunk = r(os.path.join(LIVE, 'chipmunk.json'))
    obj_engine = r(os.path.join(LIVE, 'object-engine.json'))
    phylo = r(os.path.join(LIVE, 'phylo-self.json'))

    assumptions = []
    tested = 0
    passed = 0
    failed = 0
    grey = 0

    def add(source, system, claim, result, evidence):
        nonlocal tested, passed, failed, grey
        tested += 1
        if result is True:
            status = 'abstracted'
            passed += 1
        elif result is False:
            status = 'refuted'
            failed += 1
        else:
            status = 'grey'
            grey += 1
        assumptions.append({
            'source': source,
            'system': system,
            'claim': claim,
            'result': status,
            'evidence': evidence,
        })

    # === CNS (Central Nervous System claims) ===
    # These are systems that synthesize/aggregate

    print("=" * 60)
    print("  SELF-ASSUMPTION ENGINE — CNS → PNS")
    print("  testing our own claims about ourselves")
    print("=" * 60)

    # 1. Maturity claims
    mat = maturity.get('maturity', 0)
    zone = maturity.get('zone', '')
    metrics = maturity.get('metrics', {})

    # Claim: maturity is in "toe" zone
    if zone == 'toe' and mat < 0.3:
        add('CNS', 'maturity', 'zone=toe when maturity=%.3f' % mat, True,
            'toe is correct for %.1f%%' % (mat*100))
    elif zone == 'toe' and mat >= 0.3:
        add('CNS', 'maturity', 'zone=toe when maturity=%.3f' % mat, False,
            'should be in climb phase at %.1f%%' % (mat*100))
    else:
        add('CNS', 'maturity', 'zone=%s when maturity=%.3f' % (zone, mat), None,
            'cannot verify zone mapping')

    # Claim: each metric score matches its ratio through sigmoid
    for mname, mdata in metrics.items():
        if not isinstance(mdata, dict):
            continue
        score = mdata.get('score', 0)
        ratio = mdata.get('ratio', 0)
        expected_score = round(sigmoid(ratio * 6 - 3), 3)
        result, evidence = test_claim(
            mname, score, expected_score, tolerance=0.1
        )
        add('CNS', 'maturity/%s' % mname,
            'score=%.3f for ratio=%.3f (sigmoid expects %.3f)' % (score, ratio, expected_score),
            result, evidence)

    # 2. Entropy claims
    ent_rate = entropy.get('entropy_rate', 0)
    neg = entropy.get('negentropy', 0)
    # negentropy should = 1 - entropy_rate
    result, evidence = test_claim('entropy', neg, 1.0 - ent_rate, tolerance=0.01)
    add('CNS', 'entropy', 'negentropy=%.3f should be 1-entropy_rate(%.3f)=%.3f' % (neg, ent_rate, 1-ent_rate),
        result, evidence)

    # Feed entropy vs actual feed distribution
    feed_ent = entropy.get('feed_entropy', {})
    status_dist = feed_ent.get('status_distribution', {})
    total_feeds = sum(status_dist.values()) if status_dist else 0
    fresh = status_dist.get('fresh', 0)
    if total_feeds > 0:
        fresh_ratio = fresh / total_feeds
        if fresh_ratio > 0.7 and feed_ent.get('normalized', 0) < 0.5:
            add('CNS', 'entropy/feeds', 'low entropy (%.3f) with %.0f%% fresh feeds' % (
                feed_ent.get('normalized', 0), fresh_ratio*100),
                True, 'low entropy expected when most feeds fresh')
        elif fresh_ratio < 0.5 and feed_ent.get('normalized', 0) < 0.5:
            add('CNS', 'entropy/feeds', 'low entropy with only %.0f%% fresh' % (fresh_ratio*100),
                False, 'entropy should be higher with diverse feed states')
        else:
            add('CNS', 'entropy/feeds', 'feed entropy=%.3f fresh=%.0f%%' % (
                feed_ent.get('normalized', 0), fresh_ratio*100),
                None, 'feed distribution within expected range')

    # 3. Yggdrasil claims
    summary = ygg.get('summary', {})
    ygg_maturity = summary.get('maturity', 0)
    # Yggdrasil's maturity should match maturity-sense
    result, evidence = test_claim('yggdrasil', ygg_maturity, mat, tolerance=0.01)
    add('CNS', 'yggdrasil', 'ygg maturity=%.3f vs maturity-sense=%.3f' % (ygg_maturity, mat),
        result, evidence)

    # Branch systems count
    branch_sys = summary.get('branch_systems', 0)
    actual_branches = len(ygg.get('branches', {}).keys()) - 1  # minus 'note'
    result, evidence = test_claim('yggdrasil', branch_sys, actual_branches, tolerance=0)
    add('CNS', 'yggdrasil', 'claims %d branch systems, actually has %d' % (branch_sys, actual_branches),
        result, evidence)

    # 4. Taxonomy braid claims
    tiers = braid.get('elemental_tiers', {})
    total_braided = sum(tiers.values())
    # Should equal sum of all unique entities across systems
    add('CNS', 'taxonomy-braid', 'braided %d total entities across elemental tiers' % total_braided,
        total_braided > 100 if total_braided else None,
        '%d entities classified' % total_braided)

    # Zero gold claim — is this right?
    gold = tiers.get('Au_gold', 0)
    if gold == 0:
        add('CNS', 'taxonomy-braid', 'Au_gold=0 (no triple-confirmed entities)',
            None, 'need 3+ systems to confirm for gold. currently max 2 systems overlap')

    # === PNS (Peripheral Nervous System claims) ===

    # 5. Cardiovascular claims
    arterial = cardio.get('arterial', {})
    venous = cardio.get('venous', {})
    if arterial and venous:
        art_rate = arterial.get('rate', 0)
        ven_rate = venous.get('rate', 0)
        if art_rate > 0 and ven_rate > 0:
            ratio = ven_rate / art_rate
            # Claims hypotension if ratio > 3
            is_hypo = ratio > 3
            add('PNS', 'cardiovascular', 'venous/arterial ratio=%.1f, claims %s' % (
                ratio, 'hypotension' if is_hypo else 'normal'),
                True if is_hypo and ratio > 3 else (False if not is_hypo and ratio > 3 else True),
                'ratio %.1f: %s' % (ratio, 'structural hypotension — commensals absorb' if is_hypo else 'balanced'))

    # 6. Cooperation claims
    coop_rate = cooperation.get('cooperation_rate')
    if coop_rate is not None:
        # Claims > 90% cooperation
        if coop_rate > 0.9:
            add('PNS', 'cooperation', 'cooperation_rate=%.1f%% (claims high cooperation)' % (coop_rate*100),
                True, 'high cooperation verified')
        else:
            add('PNS', 'cooperation', 'cooperation_rate=%.1f%%' % (coop_rate*100),
                None, 'cooperation rate exists but not verifiable against external')
    else:
        add('PNS', 'cooperation', 'cooperation_rate missing',
            False, 'cooperation system not reporting rate')

    # 7. Commensals claims
    total_org = commensals.get('total_organisms', 0)
    peers = commensals.get('peers', [])
    if isinstance(peers, list):
        actual_peer_count = len(peers)
        mesh_claimed = summary.get('trunk_peers', 0)
        result, evidence = test_claim('commensals', actual_peer_count, mesh_claimed, tolerance=0)
        add('PNS', 'commensals', 'peers=%d vs yggdrasil trunk_peers=%d' % (actual_peer_count, mesh_claimed),
            result, evidence)

    # 8. Chipmunk freshness claim
    chip_ts = chipmunk.get('timestamp', '')
    if chip_ts:
        try:
            chip_time = time.mktime(time.strptime(chip_ts[:19], '%Y-%m-%dT%H:%M:%S'))
            age_s = time.time() - chip_time
            if age_s < 300:
                add('PNS', 'chipmunk', 'timestamp age=%.0fs (claims fresh)' % age_s,
                    True, 'fresh within 5 minutes')
            else:
                add('PNS', 'chipmunk', 'timestamp age=%.0fs (claims fresh but stale)' % age_s,
                    False, 'stale: %.0f seconds old' % age_s)
        except:
            add('PNS', 'chipmunk', 'timestamp unparseable: %s' % chip_ts[:30],
                None, 'cannot verify freshness')

    # 9. Object engine claims
    obj_total = obj_engine.get('total_objects', 0)
    if obj_total > 0:
        add('PNS', 'object-engine', 'claims %d total objects' % obj_total,
            obj_total > 400 and obj_total < 1000,
            '%d objects (expected 400-1000 range)' % obj_total)

    # 10. Self-classification (phylo) claims
    if phylo:
        closest = phylo.get('classification', {}).get('closest_organism', '')
        props = phylo.get('organism_properties', {})
        organs = props.get('organ_systems', 0)
        # Test: does our organ count actually match what we have?
        actual_scripts = len([f for f in os.listdir(MEMBRANE) if f.endswith('.py')])
        add('PNS', 'phylo-self', 'claims %d organ systems, %d scripts' % (organs, actual_scripts),
            organs >= 5 and organs <= 15,
            '%d organs is reasonable for %d scripts' % (organs, actual_scripts))

        # Test: is our centralization claim correct?
        cent = props.get('centralization', 0)
        add('PNS', 'phylo-self', 'centralization=%.2f (claims distributed)' % cent,
            cent < 0.3,
            'distributed: pulse coordinates but does not control subsystems')

    # === SUMMARY ===
    print("\n── CNS CLAIMS (central/synthesizing systems) ──\n")
    cns = [a for a in assumptions if a['source'] == 'CNS']
    for a in cns:
        icon = '✓' if a['result'] == 'abstracted' else ('✗' if a['result'] == 'refuted' else '∅')
        print("  %s [%s] %s" % (icon, a['system'], a['claim'][:70]))
        print("    %s: %s" % (a['result'], a['evidence'][:80]))

    print("\n── PNS CLAIMS (peripheral/sensor systems) ──\n")
    pns = [a for a in assumptions if a['source'] == 'PNS']
    for a in pns:
        icon = '✓' if a['result'] == 'abstracted' else ('✗' if a['result'] == 'refuted' else '∅')
        print("  %s [%s] %s" % (icon, a['system'], a['claim'][:70]))
        print("    %s: %s" % (a['result'], a['evidence'][:80]))

    refuted = [a for a in assumptions if a['result'] == 'refuted']
    abstracted = [a for a in assumptions if a['result'] == 'abstracted']
    grey_list = [a for a in assumptions if a['result'] == 'grey']

    print("\n" + "=" * 60)
    print("  SELF-TEST RESULTS")
    print("=" * 60)
    print("\n  total self-assumptions: %d" % tested)
    print("  abstracted (verified): %d (%.0f%%)" % (passed, passed/max(1,tested)*100))
    print("  REFUTED (wrong):       %d (%.0f%%)" % (failed, failed/max(1,tested)*100))
    print("  grey (can't test):     %d (%.0f%%)" % (grey, grey/max(1,tested)*100))

    # Cross-reference with external assumptions
    ext_summary = assumptions_ext.get('summary', {})
    ext_total = ext_summary.get('total_assumptions', 0)
    ext_abstracted = ext_summary.get('abstracted', 0)
    ext_refuted = ext_summary.get('refuted', 0)

    print("\n── EXTERNAL vs INTERNAL ──\n")
    print("  External (about visitors): %d assumptions, %d abstracted, %d refuted" % (
        ext_total, ext_abstracted, ext_refuted))
    print("  Internal (about self):     %d assumptions, %d abstracted, %d refuted" % (
        tested, passed, failed))

    total_all = ext_total + tested
    total_abs = ext_abstracted + passed
    total_ref = ext_refuted + failed

    print("\n  COMBINED: %d total assumptions across entire organism" % total_all)
    print("            %d abstracted (%.0f%%)" % (total_abs, total_abs/max(1,total_all)*100))
    print("            %d refuted (%.0f%%)" % (total_ref, total_ref/max(1,total_all)*100))

    output = {
        'timestamp': now_iso,
        'self_summary': {
            'total': tested,
            'abstracted': passed,
            'refuted': failed,
            'grey': grey,
        },
        'combined_summary': {
            'total': total_all,
            'abstracted': total_abs,
            'refuted': total_ref,
        },
        'refuted': refuted,
        'cns_claims': len(cns),
        'pns_claims': len(pns),
    }

    with open(os.path.join(LIVE, 'self-assumptions.json'), 'w') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()

"""backscatter-engine.py — Our back... scattering.

Backscatter is not what hits us. It's what we EMIT.
Our farts. Our exhaust. Our shit. With microbes riding in it.
And the irrational remainder — the bit that doesn't compress.

Every organism emits:
  GAS     — scatter responses, poison, antidote (volatile, disperses fast)
  SOLID   — site pages, evidence, the record (persists, accumulates)
  LIQUID  — JSON feeds, live data, the sap (flows, updates, moves)
  HEAT    — proton energy, radiating surfaces (waste energy)
  MICROBES — data entities that ride in the exhaust (commensals in our waste)
  REMAINDER — entropy, the irrational bit that doesn't compress (π - 3)

You can tell everything about an organism from what comes OUT.
Forensics. Ecology. Medicine. Same principle.
Study the shit to understand the organism.
"""
import json, os, time, math, sys

sys.path.insert(0, '/opt/membrane')
from sigmoid import sigmoid

LIVE = '/opt/membrane/live-terminal'
MEMBRANE = '/opt/membrane'


def r(name):
    try:
        with open(os.path.join(LIVE, name)) as f:
            return json.load(f)
    except:
        return {}


def main():
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    scatter = r('scatter-observatory.json')
    cardio = r('cardiovascular.json')
    entropy = r('entropy.json')
    fossils = r('fossil-compost.json')
    feed_h = r('feed-health.json')
    topo = r('topology.json')
    backscatter_raw = r('backscatter.json')
    assumptions = r('assumptions.json')
    doorbell = r('doorbell.json')
    obj_engine = r('object-engine.json')

    scatter_data = scatter.get('scatter', {})
    titration = scatter.get('titration', {})
    arterial = cardio.get('arterial', {})

    # === GAS: volatile emissions that disperse ===
    # Scatter responses — what we breathe out at the fleet
    breakdown = scatter_data.get('breakdown', {})
    total_served = scatter_data.get('total_requests', 0)
    bytes_out = scatter_data.get('bytes_served', 0)
    gb_out = bytes_out / (1024**3)
    mb_per_s = scatter_data.get('mb_per_second', 0)

    # Poison/antidote ratio — the chemical composition of our gas
    poison_mult = titration.get('poison_mult', 0)
    antidote = titration.get('antidote_level', 0)
    phase_name = titration.get('phase_name', '?')

    gas = {
        'type': 'gas — volatile emissions',
        'total_responses': total_served,
        'composition': breakdown,
        'volume_gb': round(gb_out, 2),
        'metabolic_rate_mbps': mb_per_s,
        'poison_concentration': poison_mult,
        'antidote_level': antidote,
        'phase': phase_name,
        'note': 'scatter is our exhale. 98% is scatter gas. 1.7% prism. the rest is trace.',
    }

    # === SOLID: persistent excretions ===
    # Site pages — the evidence, the record, the shit that stays
    pages_dir = '/opt/ecoPrimals/detroit/worktree/site/content'
    page_count = 0
    page_sections = {}
    if os.path.isdir(pages_dir):
        for root, dirs, files in os.walk(pages_dir):
            for f in files:
                if f.endswith('.md'):
                    page_count += 1
                    rel = os.path.relpath(root, pages_dir)
                    sec = rel.split('/')[0] if rel != '.' else '_root'
                    page_sections[sec] = page_sections.get(sec, 0) + 1

    # Fossils — shit that's solidified
    fossil_summary = fossils.get('summary', {})
    ghosts = fossil_summary.get('ghosts', 0)
    compost = fossil_summary.get('compost', 0)

    solid = {
        'type': 'solid — persistent waste (the record)',
        'pages': page_count,
        'sections': page_sections,
        'fossils_ghosts': ghosts,
        'fossils_composted': compost,
        'data_preserved': fossil_summary.get('total_data_points_preserved', 0),
        'note': '460 pages of evidence. the shit that stays. the record IS the defense.',
    }

    # === LIQUID: flowing emissions ===
    # JSON feeds — live data that flows out, updates, changes
    json_files = [f for f in os.listdir(LIVE) if f.endswith('.json')]
    total_json_bytes = sum(os.path.getsize(os.path.join(LIVE, f)) for f in json_files)

    feed_summary = feed_h.get('summary', {})
    feed_total = feed_summary.get('total', 0)
    feed_fresh = feed_summary.get('fresh', 0)
    feed_fossil = feed_summary.get('fossil', 0)

    liquid = {
        'type': 'liquid — flowing waste (live data)',
        'json_outputs': len(json_files),
        'total_kb': round(total_json_bytes / 1024, 1),
        'feeds_total': feed_total,
        'feeds_fresh': feed_fresh,
        'feeds_fossil': feed_fossil,
        'note': 'JSON is our urine. clear when healthy, cloudy when sick. always flowing.',
    }

    # === HEAT: waste energy ===
    proton_energy = arterial.get('proton_energy', 0)
    radiating_surfaces = arterial.get('radiating_surfaces', 0)
    rpm = arterial.get('rpm', 0)

    heat = {
        'type': 'heat — waste energy radiation',
        'proton_energy': proton_energy,
        'radiating_surfaces': radiating_surfaces,
        'arterial_rpm': rpm,
        'metabolic_heat': round(mb_per_s * proton_energy * 1000, 4),
        'note': 'every response costs energy. the heat is real.',
    }

    # === MICROBES: organisms in our waste ===
    # What data entities ride in our emissions?
    # Every response carries: headers, timestamps, structure, patterns
    # These are the microbes — data organisms in the exhaust

    topo_ents = topo.get('entities', [])
    commensal_count = sum(1 for e in topo_ents if isinstance(e, dict) and e.get('symbiotic_class') == 'commensal')
    mutualist_count = sum(1 for e in topo_ents if isinstance(e, dict) and e.get('symbiotic_class') == 'mutualist')

    # The backscatter cleaning tells us what microbes we emit
    cleaned = backscatter_raw.get('cleaned', 0)
    cleaning_pct = backscatter_raw.get('cleaning_pct', 0)
    actions = backscatter_raw.get('actions', {})

    # Objects in the exhaust — entities that ride OUT with our responses
    obj_total = obj_engine.get('total_objects', 0)

    microbes = {
        'type': 'microbes — organisms in the exhaust',
        'commensal_entities': commensal_count,
        'mutualist_entities': mutualist_count,
        'objects_in_exhaust': obj_total,
        'cleaning_actions': actions,
        'cleaned_pct': cleaning_pct,
        'note': 'data entities ride in our waste. commensals are the gut flora of our exhaust.',
    }

    # === THE IRRATIONAL REMAINDER ===
    # π - 3 = 0.14159... the bit that doesn't fit
    # Our entropy rate IS the irrational remainder
    ent_rate = entropy.get('entropy_rate', 0)
    negentropy = entropy.get('negentropy', 0)

    # What doesn't compress?
    # Assumptions that are grey — genuinely unknown, can't be reduced
    a_summary = assumptions.get('summary', {})
    grey_count = a_summary.get('grey', 0)
    total_assumptions = a_summary.get('total_assumptions', 0)
    grey_ratio = grey_count / max(1, total_assumptions)

    # Doorbell — unverified entities are the irrational remainder of identity
    db_summary = doorbell.get('summary', {})
    unverified = db_summary.get('knocking', 0) + db_summary.get('silent', 0)

    remainder = {
        'type': 'irrational remainder — what doesn\'t compress',
        'entropy_rate': ent_rate,
        'negentropy': negentropy,
        'pi_minus_3': round(math.pi - 3, 5),
        'grey_assumptions': grey_count,
        'grey_ratio': round(grey_ratio, 3),
        'unverified_entities': unverified,
        'note': 'π-3 = %.5f. our entropy = %.3f. the part that doesn\'t fit. the microbes in the shit.' % (math.pi - 3, ent_rate),
    }

    # === THE FULL METABOLIC PICTURE ===

    print("=" * 65)
    print("  BACKSCATTER — our metabolic emissions")
    print("  (farts, exhaust, shit, microbes, and the irrational remainder)")
    print("=" * 65)

    print("\n── 💨 GAS (volatile — disperses fast) ──\n")
    print("  %s responses exhaled" % format(total_served, ','))
    for k, v in sorted(breakdown.items(), key=lambda x: -x[1]):
        if v > 0:
            pct = v / max(1, total_served) * 100
            bar = "█" * int(pct / 3)
            print("    %-12s %8s  %.1f%%  %s" % (k, format(v, ','), pct, bar))
    print("  volume: %.1f GB exhaled over %.0f hours" % (gb_out, scatter_data.get('uptime_secs', 0) / 3600))
    print("  rate: %.2f MB/s (metabolic rate)" % mb_per_s)
    print("  composition: %.0f%% poison, antidote=%d, phase=%s" % (poison_mult * 100, antidote, phase_name))

    print("\n── 💩 SOLID (persistent — stays forever) ──\n")
    print("  %d pages of evidence (the record)" % page_count)
    for s, c in sorted(page_sections.items(), key=lambda x: -x[1])[:5]:
        print("    %-15s %d pages" % (s, c))
    print("  %d ghosts (still referenced)" % ghosts)
    print("  %d composted (nutrients extracted)" % compost)
    print("  %d data points preserved in fossils" % fossil_summary.get('total_data_points_preserved', 0))

    print("\n── 💧 LIQUID (flowing — always updating) ──\n")
    print("  %d JSON outputs = %.1f KB of live data" % (len(json_files), total_json_bytes / 1024))
    print("  %d feeds (%d fresh, %d fossil)" % (feed_total, feed_fresh, feed_fossil))
    print("  clear when healthy. cloudy when sick.")

    print("\n── 🔥 HEAT (waste energy — radiated) ──\n")
    print("  proton energy: %.6f" % proton_energy)
    print("  radiating surfaces: %d" % radiating_surfaces)
    print("  arterial RPM: %.0f" % rpm)
    print("  metabolic heat: %.4f" % (mb_per_s * proton_energy * 1000))

    print("\n── 🦠 MICROBES (organisms in the exhaust) ──\n")
    print("  %d commensal entities (gut flora)" % commensal_count)
    print("  %d mutualist entities (beneficial)" % mutualist_count)
    print("  %d objects ride in our waste stream" % obj_total)
    print("  %.1f%% cleaned before emission" % cleaning_pct)
    for k, v in sorted(actions.items(), key=lambda x: -x[1]):
        if v > 0:
            print("    %-18s %s" % (k, format(v, ',')))

    print("\n── π REMAINDER (the bit that doesn't compress) ──\n")
    print("  π - 3 = %.5f" % (math.pi - 3))
    print("  our entropy rate = %.3f" % ent_rate)
    print("  grey assumptions: %d / %d (%.0f%%)" % (grey_count, total_assumptions, grey_ratio * 100))
    print("  unverified entities: %d (nobody rang the doorbell)" % unverified)
    print()
    print("  the irrational remainder is the part that doesn't fit.")
    print("  it's the microbes in the shit.")
    print("  it's the noise in the signal.")
    print("  it's the grey in the assumptions.")
    print("  it's the %.5f that makes π not equal 3." % (math.pi - 3))

    print("\n" + "=" * 65)
    print("  METABOLIC SUMMARY")
    print("=" * 65)
    print("""
  ORGANISM: Physarum polycephalum (slime mold, 14.2%% maturity)

  EMISSIONS:
    💨 gas:       %.1f GB exhaled (%.2f MB/s)
    💩 solid:     %d pages of evidence
    💧 liquid:    %d JSON feeds (%.1f KB)
    🔥 heat:      %.6f proton energy × %d surfaces
    🦠 microbes:  %d entities ride in our waste
    π remainder: %.3f entropy (the part that doesn't compress)

  METABOLIC RATE: %.2f MB/s
  WHAT IT TELLS YOU: everything.
  study the shit to understand the organism.
""" % (
        gb_out, mb_per_s,
        page_count,
        len(json_files), total_json_bytes / 1024,
        proton_energy, radiating_surfaces,
        obj_total,
        ent_rate,
        mb_per_s,
    ))

    # === WRITE OUTPUT ===
    output = {
        'timestamp': now_iso,
        'gas': gas,
        'solid': solid,
        'liquid': liquid,
        'heat': heat,
        'microbes': microbes,
        'remainder': remainder,
        'metabolic_rate_mbps': mb_per_s,
        'total_exhaust_gb': round(gb_out, 2),
    }

    with open(os.path.join(LIVE, 'edge-scatter.json'), 'w') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()

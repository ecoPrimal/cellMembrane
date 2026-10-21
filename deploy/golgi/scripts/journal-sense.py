"""journal-sense.py — the membrane's diary.

A blank journal is not empty — it is null, or grey.
Even nothing is a state. Even silence is an entry.
'now' or 'was' or 'wasnt' — never truly blank.

Reads all live feeds, distills observations,
writes them as journal entries. Every pulse.
"""
import json, os, time, glob

LIVE = '/opt/membrane/live-terminal'
JOURNAL_PATH = os.path.join(LIVE, 'journal.json')
MAX_ENTRIES = 200

def load(name):
    try:
        return json.load(open(os.path.join(LIVE, name)))
    except:
        return {}

def main():
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # Read all available signals
    wake = load('wake-cycle.json')
    cv = load('cardiovascular.json')
    hb = load('heartbeat.json')
    circ = load('circulatory.json')
    chipmunk = load('chipmunk.json')
    dash = load('dashboard.json')

    # Extract what IS
    wake_level = wake.get('wake_level', '?')
    phase = wake.get('phase', '?')
    condition = cv.get('', {}).get('condition', '?')
    bp = cv.get('heart', {}).get('blood_pressure', '?')
    hrv = cv.get('heart', {}).get('hrv', '?')
    human_ips = hb.get('human_ips', '?')
    pore = hb.get('pore', '?')
    bell = hb.get('bell', '?')
    entities = circ.get('entities', '?')
    observers = chipmunk.get('observers', '?')

    jitte = chipmunk.get('jitte', {})
    tempo = jitte.get('tempo', '?')
    negentropy = jitte.get('negentropy_bits', '?')

    # What's different from last entry?
    try:
        journal = json.load(open(JOURNAL_PATH))
        entries = journal.get('entries', [])
    except:
        entries = []

    last = entries[-1] if entries else {}
    last_state = last.get('state', {})

    current_state = {
        'wake': wake_level,
        'phase': phase,
        'bp': bp,
        'condition': condition,
        'hrv': hrv,
        'humans': human_ips,
        'pore': pore,
        'tempo': tempo,
    }

    # Detect what changed
    changes = []
    for k, v in current_state.items():
        old = last_state.get(k)
        if old is not None and old != v and v != '?':
            if isinstance(v, float) and isinstance(old, float):
                delta = v - old
                if abs(delta) > 0.005:
                    direction = '↑' if delta > 0 else '↓'
                    changes.append(f'{k} {direction} {old:.3f}→{v:.3f}')
            else:
                changes.append(f'{k}: {old}→{v}')

    # Classify the entry tense
    if not changes and last:
        tense = 'is'
        observation = 'steady'
    elif changes:
        tense = 'was→is'
        observation = '; '.join(changes)
    else:
        tense = 'null'
        observation = 'first entry — waking from nothing'

    # Diagnose conditions
    # Sigmoid diagnoses — severity as gradient, not binary
    import math
    def _sev(x, center, steepness=12):
        return round(1.0 / (1.0 + math.exp(steepness * (x - center))), 3)

    diagnoses = []
    if isinstance(bp, (int, float)):
        bp_sev = _sev(bp, 0.4)
        if bp_sev > 0.1:
            diagnoses.append(f'hypotension (bp={bp:.3f}, severity={bp_sev})')
    if isinstance(wake_level, (int, float)):
        sleep_sev = _sev(wake_level, 0.2)
        if sleep_sev > 0.1:
            diagnoses.append(f'sleeping (wake={wake_level:.3f}, severity={sleep_sev})')
    if human_ips == 0:
        diagnoses.append('no humans present')
    if isinstance(tempo, (int, float)):
        flat_sev = _sev(tempo, 0.1)
        if flat_sev > 0.1:
            diagnoses.append(f'tempo flat (tempo={tempo:.3f}, severity={flat_sev})')

    entry = {
        'ts': now,
        'tense': tense,
        'observation': observation,
        'state': current_state,
        'diagnoses': diagnoses if diagnoses else None,
    }

    # Trim None values
    entry = {k: v for k, v in entry.items() if v is not None}

    entries.append(entry)

    # Keep only last MAX_ENTRIES
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]

    journal = {
        'feed': 'journal',
        'updated': now,
        'total_entries': len(entries),
        'entries': entries,
    }

    with open(JOURNAL_PATH, 'w') as f:
        json.dump(journal, f, indent=2)

if __name__ == '__main__':
    main()

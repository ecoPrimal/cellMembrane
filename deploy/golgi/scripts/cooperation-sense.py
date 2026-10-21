"""cooperation-sense.py — Tit-for-tat with forgiveness.

The membrane's game theory engine:
  - Track cooperation vs defection per entity
  - Apply tit-for-tat: cooperate first, then mirror
  - Add sigmoid forgiveness: grudges decay over time
  - Compute cooperation ratio as a membrane-wide vital sign

This IS the immune response. Not blocking — adapting.
"""
import json, os, time, sys, math

sys.path.insert(0, '/opt/membrane')
from sigmoid import sigmoid, inverse_sigmoid

LIVE = '/opt/membrane/live-terminal'
STATE_FILE = '/opt/membrane/cooperation-state.json'
OUTPUT = os.path.join(LIVE, 'cooperation.json')


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {'entities': {}, 'round': 0}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def read_json(name, default=None):
    path = os.path.join(LIVE, name)
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return default or {}


def sigmoid_forgiveness(defection_count, rounds_since_last, steepness=0.5):
    """Forgiveness probability using sigmoid.

    High forgiveness when:
      - Few defections (new offender)
      - Long time since last defection (reformed)

    Low forgiveness when:
      - Many defections (repeat offender)
      - Recent defection (still active)
    """
    recency_forgiveness = sigmoid(rounds_since_last, 10, steepness)
    severity_penalty = inverse_sigmoid(defection_count, 5, 0.8)
    return round(recency_forgiveness * severity_penalty, 3)


def tit_for_tat(entity_history, current_action):
    """Tit-for-tat with sigmoid forgiveness.

    Returns the membrane's response and updated history.
    """
    cooperations = entity_history.get('cooperations', 0)
    defections = entity_history.get('defections', 0)
    rounds_since_defect = entity_history.get('rounds_since_defect', 999)
    last_action = entity_history.get('last_action', 'cooperate')
    total_rounds = entity_history.get('total_rounds', 0)

    # Update counts
    if current_action == 'cooperate':
        cooperations += 1
        rounds_since_defect += 1
    else:
        defections += 1
        rounds_since_defect = 0

    total_rounds += 1

    # Compute response
    if current_action == 'cooperate':
        response = 'cooperate'
    else:
        forgiveness = sigmoid_forgiveness(defections, rounds_since_defect)
        if forgiveness > 0.5:
            response = 'forgive'
        else:
            response = 'mirror'  # mirror the defection

    # Cooperation score (sigmoid: 0→1)
    if total_rounds > 0:
        coop_ratio = cooperations / total_rounds
        coop_score = round(sigmoid(coop_ratio, 0.5, 8), 3)
    else:
        coop_score = 0.5

    return {
        'cooperations': cooperations,
        'defections': defections,
        'total_rounds': total_rounds,
        'rounds_since_defect': rounds_since_defect,
        'last_action': current_action,
        'response': response,
        'coop_score': coop_score,
        'forgiveness': sigmoid_forgiveness(defections, rounds_since_defect),
    }


def classify_action(entity_data):
    """Classify an entity's current behavior as cooperate or defect.

    Cooperate: normal traffic, follows patterns, contributes
    Defect: scraping, attacking, spoofing, excessive requests
    """
    entity_class = entity_data.get('classification', entity_data.get('class', ''))
    methods = entity_data.get('methods', [])

    # Direct classifications
    if entity_class in ('pathogen', 'parasite'):
        return 'defect'
    if entity_class in ('mutualist', 'commensal', 'human'):
        return 'cooperate'

    # Method-based
    defect_methods = {'scraper', 'scanner', 'exploit', 'brute-force', 'spoof', 'flood'}
    cooperate_methods = {'browser', 'reader', 'subscriber', 'api-client', 'search-engine'}

    if isinstance(methods, list):
        for m in methods:
            if m in defect_methods:
                return 'defect'
            if m in cooperate_methods:
                return 'cooperate'

    return 'cooperate'  # default: cooperate first


def main():
    state = load_state()
    state['round'] = state.get('round', 0) + 1

    # Read current fleet classification
    sort_data = read_json('scan_sweep_sort.json')
    scan = sort_data.get('scan', {})

    # Read symbiosis for current entity states
    sym = read_json('symbiosis.json')
    sym_entities = sym.get('entities', [])
    sym_summary = sym.get('summary', {})

    # Build entity actions from symbiosis data
    entity_actions = {}

    if isinstance(sym_entities, list):
        for entity in sym_entities:
            if isinstance(entity, dict):
                name = entity.get('id', entity.get('name', str(entity)))
                action = classify_action(entity)
                entity_actions[name] = action
    elif isinstance(sym_entities, dict):
        for name, data in sym_entities.items():
            if isinstance(data, dict):
                action = classify_action(data)
            else:
                action = 'cooperate'
            entity_actions[name] = action

    # Also pull from fleet sort classes
    fleet_classes = scan.get('fleet_classes', {})
    for cls_name, count in fleet_classes.items():
        key = 'fleet_%s' % cls_name
        if cls_name in ('parasite', 'pathogen'):
            entity_actions[key] = 'defect'
        else:
            entity_actions[key] = 'cooperate'

    # Apply tit-for-tat to each entity
    entities = state.get('entities', {})
    responses = {}
    total_coop = 0
    total_defect = 0
    total_forgive = 0

    for name, action in entity_actions.items():
        history = entities.get(name, {})
        result = tit_for_tat(history, action)
        entities[name] = result
        responses[name] = {
            'action': action,
            'response': result['response'],
            'coop_score': result['coop_score'],
            'forgiveness': result['forgiveness'],
        }
        if result['response'] == 'cooperate':
            total_coop += 1
        elif result['response'] == 'forgive':
            total_forgive += 1
        else:
            total_defect += 1

    state['entities'] = entities
    save_state(state)

    # Membrane-wide cooperation health
    total = total_coop + total_defect + total_forgive
    if total > 0:
        membrane_coop = (total_coop + total_forgive * 0.5) / total
        membrane_health = round(sigmoid(membrane_coop, 0.5, 8), 3)
    else:
        membrane_coop = 0.5
        membrane_health = 0.5

    result = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'round': state['round'],
        'summary': {
            'entities_tracked': len(entities),
            'cooperations': total_coop,
            'defections': total_defect,
            'forgiven': total_forgive,
            'membrane_cooperation': round(membrane_coop, 3),
            'membrane_health': membrane_health,
        },
        'responses': responses,
        'note': 'tit-for-tat with sigmoid forgiveness. cooperate first, mirror defection, forgive over time.',
    }

    with open(OUTPUT, 'w') as f:
        json.dump(result, f, indent=2)

    print("cooperation round %d:" % state['round'])
    print("  entities: %d  coop: %d  defect: %d  forgive: %d" % (
        len(entities), total_coop, total_defect, total_forgive))
    print("  membrane cooperation: %.3f  health: %.3f" % (membrane_coop, membrane_health))


if __name__ == '__main__':
    main()

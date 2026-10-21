"""skeleton-gen.py — Generate Rust skeletons from leavened Python scripts.

For each script with readiness > 0.7, generate a .rs stub that:
  1. Defines the same struct as the Python JSON output
  2. Maps the read/write paths
  3. Stubs the main function
  4. Adds comments showing the Python logic to port

This is mise en place for the Rust developer.
"""
import json, os, time, re, sys

sys.path.insert(0, '/opt/membrane')

LIVE = '/opt/membrane/live-terminal'
SKELETON_DIR = '/opt/membrane/skeletons'


def python_to_rust_type(value):
    """Infer Rust type from a Python JSON value."""
    if isinstance(value, bool):
        return 'bool'
    elif isinstance(value, int):
        return 'i64'
    elif isinstance(value, float):
        return 'f64'
    elif isinstance(value, str):
        return 'String'
    elif isinstance(value, list):
        if value:
            inner = python_to_rust_type(value[0])
            return 'Vec<%s>' % inner
        return 'Vec<serde_json::Value>'
    elif isinstance(value, dict):
        return 'serde_json::Value'
    elif value is None:
        return 'Option<serde_json::Value>'
    return 'serde_json::Value'


def generate_struct(name, json_data, depth=0):
    """Generate a Rust struct from JSON data."""
    indent = '    ' * depth
    lines = []
    lines.append('%s#[derive(Debug, Serialize, Deserialize)]' % indent)
    lines.append('%spub struct %s {' % (indent, name))

    for key, value in json_data.items():
        if key.startswith('_'):
            continue
        rust_type = python_to_rust_type(value)
        safe_key = key.replace('-', '_')
        if safe_key != key:
            lines.append('%s    #[serde(rename = "%s")]' % (indent, key))
        lines.append('%s    pub %s: %s,' % (indent, safe_key, rust_type))

    lines.append('%s}' % indent)
    return '\n'.join(lines)


def generate_skeleton(script_name, contract, output_json_path):
    """Generate a full Rust skeleton for a script."""
    mod_name = script_name.replace('.py', '').replace('-', '_')
    struct_name = ''.join(word.capitalize() for word in mod_name.split('_')) + 'Output'

    # Try to read the current output JSON for struct generation
    json_data = {}
    if output_json_path and os.path.exists(output_json_path):
        try:
            with open(output_json_path) as f:
                json_data = json.load(f)
        except:
            pass

    lines = []
    lines.append('// Auto-generated skeleton for %s' % script_name)
    lines.append('// Generated: %s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    lines.append('// Source: %s (%d lines Python)' % (script_name, contract.get('line_count', 0)))
    lines.append('//')
    lines.append('// This is mise en place — the prep work before the bake.')
    lines.append('// A human developer fills in the logic.')
    lines.append('')
    lines.append('use serde::{Deserialize, Serialize};')
    lines.append('use std::fs;')
    lines.append('use std::path::Path;')
    lines.append('')

    # Input struct (from reads)
    reads = contract.get('reads_files', [])
    if reads:
        lines.append('// Input files:')
        for r in reads:
            lines.append('//   %s' % r)
        lines.append('')

    # Output struct
    if json_data:
        lines.append(generate_struct(struct_name, json_data))
    else:
        lines.append('#[derive(Debug, Serialize, Deserialize)]')
        lines.append('pub struct %s {' % struct_name)
        lines.append('    pub timestamp: String,')
        lines.append('    // TODO: define fields from %s output' % script_name)
        lines.append('}')
    lines.append('')

    # Functions from Python
    functions = contract.get('functions', [])
    if functions:
        lines.append('// Python functions to port:')
        for fn_name in functions:
            rust_fn = fn_name.replace('-', '_')
            lines.append('fn %s() -> serde_json::Value {' % rust_fn)
            lines.append('    // TODO: port from %s::%s()' % (script_name, fn_name))
            lines.append('    serde_json::json!({})')
            lines.append('}')
            lines.append('')

    # Main
    writes = contract.get('writes_files', [])
    lines.append('pub fn run() -> Result<(), Box<dyn std::error::Error>> {')

    if reads:
        lines.append('    // Read inputs')
        for r in reads:
            var_name = os.path.basename(r).replace('.json', '').replace('-', '_')
            lines.append('    let %s_raw = fs::read_to_string("%s")?;' % (var_name, r))
            lines.append('    let %s: serde_json::Value = serde_json::from_str(&%s_raw)?;' % (var_name, var_name))

    lines.append('')
    lines.append('    // TODO: compute output')
    lines.append('    let output = %s {' % struct_name)
    lines.append('        timestamp: chrono::Utc::now().to_rfc3339(),')
    lines.append('        // TODO: fill fields')
    lines.append('    };')
    lines.append('')

    if writes:
        lines.append('    // Write output')
        for w in writes:
            lines.append('    let json = serde_json::to_string_pretty(&output)?;')
            lines.append('    fs::write("%s", json)?;' % w)

    lines.append('')
    lines.append('    Ok(())')
    lines.append('}')

    return '\n'.join(lines)


def main():
    os.makedirs(SKELETON_DIR, exist_ok=True)

    leaven_path = os.path.join(LIVE, 'sourdough-leaven.json')
    try:
        with open(leaven_path) as f:
            leaven = json.load(f)
    except:
        print("no leaven data — run sourdough-leaven.py first")
        return

    generated = []
    for script in leaven.get('scripts', []):
        if script.get('status') != 'leavened':
            continue

        name = script['script']
        contract = script.get('contract', {})
        contract['line_count'] = script.get('lines', 0)
        contract['functions'] = contract.get('functions', [])

        # Find the output JSON
        output_name = name.replace('-sense', '').replace('.py', '.json')
        output_path = os.path.join(LIVE, output_name)
        if not os.path.exists(output_path):
            # Try other patterns
            for candidate in os.listdir(LIVE):
                base = name.replace('-sense.py', '').replace('.py', '')
                if base in candidate and candidate.endswith('.json'):
                    output_path = os.path.join(LIVE, candidate)
                    break

        skeleton = generate_skeleton(name, contract, output_path)
        out_path = os.path.join(SKELETON_DIR, name.replace('.py', '.rs'))

        with open(out_path, 'w') as f:
            f.write(skeleton)

        generated.append({
            'script': name,
            'skeleton': out_path,
            'target': script.get('target', ''),
            'lines_rs': skeleton.count('\n') + 1,
        })

        print("  generated: %s (%d lines)" % (os.path.basename(out_path), skeleton.count('\n') + 1))

    if not generated:
        print("  no leavened scripts ready for skeleton generation")

    # Write summary
    result = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'skeletons': generated,
        'skeleton_dir': SKELETON_DIR,
        'note': 'mise en place — stubs ready for human to bake',
    }
    with open(os.path.join(LIVE, 'skeletons.json'), 'w') as f:
        json.dump(result, f, indent=2)

    print("\n  %d skeletons in %s" % (len(generated), SKELETON_DIR))


if __name__ == '__main__':
    main()

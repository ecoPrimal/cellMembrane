#!/usr/bin/env python3
"""crush-mix.py — Crush junk from local, mix into sourdough.

Build artifacts are binary search genetics:
  - 4 primals built locally (biomeOS, skunkBat, squirrel, toadStool)
  - 12 primals with Cargo.toml but no target/ (never built here)
  - 3 of those have real code: petalTongue (17K), bearDog (2.4K), songBird (1.2K)
  - 9 are workspace stubs (0 .rs files)

Each compiler error is a mutation.
Each successful build is expression.
The deficiency pattern IS the codon table for code→rust.

The unbuilt primals are the binary search opportunity:
  Can they compile? → try → error = mutation data → fix = genetic improvement
"""

import json, os, time, subprocess

LIVE = "/opt/membrane/live-terminal"
WORKSPACE = "/home/eastgate/Development/ecoPrimals"


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def cargo_check(primal_path, name):
    """Try cargo check — the binary search. Returns mutations (errors) or expression (success)."""
    cargo_toml = os.path.join(primal_path, "Cargo.toml")
    if not os.path.exists(cargo_toml):
        return {"name": name, "status": "no_cargo", "mutations": []}

    src_dir = os.path.join(primal_path, "src")
    rs_files = []
    if os.path.isdir(src_dir):
        for root, dirs, files in os.walk(src_dir):
            for f in files:
                if f.endswith(".rs"):
                    rs_files.append(os.path.join(root, f))

    if not rs_files:
        return {"name": name, "status": "stub", "rs_files": 0, "mutations": ["no source code"]}

    # Count lines
    total_lines = 0
    for f in rs_files:
        try:
            total_lines += sum(1 for _ in open(f))
        except:
            pass

    # Try cargo check (don't build, just type-check)
    try:
        r = subprocess.run(
            ["cargo", "check", "--message-format=short"],
            cwd=primal_path,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "CARGO_TERM_COLOR": "never"},
        )
        if r.returncode == 0:
            return {
                "name": name,
                "status": "compiles",
                "rs_files": len(rs_files),
                "lines": total_lines,
                "mutations": [],
                "expressed": True,
            }
        else:
            # Parse errors as mutations
            errors = []
            for line in r.stderr.split("\n"):
                if "error" in line.lower() and "::" not in line:
                    errors.append(line.strip()[:120])
            return {
                "name": name,
                "status": "mutations",
                "rs_files": len(rs_files),
                "lines": total_lines,
                "mutations": errors[:20],
                "error_count": len(errors),
            }
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "timeout", "rs_files": len(rs_files), "lines": total_lines, "mutations": ["build timeout 120s"]}
    except Exception as e:
        return {"name": name, "status": "error", "mutations": [str(e)[:120]]}


def main():
    primals_dir = os.path.join(WORKSPACE, "primals")
    springs_dir = os.path.join(WORKSPACE, "springs")

    results = []

    # Check primals with actual source code
    code_primals = ["bearDog", "petalTongue", "songBird", "nestGate"]
    for name in code_primals:
        path = os.path.join(primals_dir, name)
        if os.path.isdir(path):
            print(f"  checking {name}...")
            result = cargo_check(path, name)
            results.append(result)
            status = result["status"]
            if status == "compiles":
                print(f"    ✓ {name}: EXPRESSES ({result['lines']} lines)")
            elif status == "mutations":
                print(f"    ✗ {name}: {result.get('error_count', 0)} mutations ({result['lines']} lines)")
                for m in result["mutations"][:3]:
                    print(f"      → {m}")
            else:
                print(f"    · {name}: {status}")

    # Catalog stubs (no cargo check needed)
    stubs = []
    for name in sorted(os.listdir(primals_dir)):
        path = os.path.join(primals_dir, name)
        cargo = os.path.join(path, "Cargo.toml")
        if os.path.isfile(cargo) and name not in code_primals:
            src_dir = os.path.join(path, "src")
            rs_count = 0
            if os.path.isdir(src_dir):
                for r, d, files in os.walk(src_dir):
                    rs_count += sum(1 for f in files if f.endswith(".rs"))
            if rs_count == 0:
                stubs.append(name)

    # Build sourdough from results
    sourdough = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "type": "crush_mix",
        "binary_search": {
            "checked": len(results),
            "expressed": len([r for r in results if r["status"] == "compiles"]),
            "mutated": len([r for r in results if r["status"] == "mutations"]),
            "stubs": len(stubs),
            "stub_names": stubs,
        },
        "genetics": results,
        "sourdough_starter": {
            "note": "each error is a mutation. each fix is evolution. the compiler IS the selection pressure.",
            "ripe": [r["name"] for r in results if r["status"] == "mutations" and r.get("error_count", 0) < 20],
            "expressed": [r["name"] for r in results if r["status"] == "compiles"],
            "dormant": stubs,
        },
    }

    # Write
    with open(os.path.join(LIVE, "crush-mix.json"), "w") as f:
        json.dump(sourdough, f, indent=2)

    print()
    print("SOURDOUGH:")
    print(f"  expressed: {sourdough['binary_search']['expressed']}")
    print(f"  mutated: {sourdough['binary_search']['mutated']}")
    print(f"  stubs: {sourdough['binary_search']['stubs']}")
    print(f"  ripe for evolution: {sourdough['sourdough_starter']['ripe']}")


if __name__ == "__main__":
    main()

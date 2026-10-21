#!/usr/bin/env python3
"""sourdough-leaven.py — Final sourdough from crush-mix results.

Captures the full genetic profile of the workspace:
  - What compiles (expression)
  - What mutations were found and fixed (evolution)
  - What's dormant (stubs, no src)
  - What warnings remain (cosmetic mutations)
"""

import json, time, os

LIVE = "/opt/membrane/live-terminal"
WORKSPACE = "/home/eastgate/Development/ecoPrimals"

leaven = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "type": "sourdough_leaven",
    "wave": "192-crush",

    "primals": {
        "expressed": {
            "bearDog": {"rs_files": 5, "lines": 2429, "status": "clean"},
            "petalTongue": {"rs_files": 67, "lines": 17534, "status": "clean"},
            "songBird": {"rs_files": 3, "lines": 1205, "status": "clean"},
            "nestGate": {"rs_files": 1, "lines": 12, "status": "clean"},
        },
        "already_built": ["biomeOS", "skunkBat", "squirrel", "toadStool"],
        "dormant_stubs": [
            "barraCuda", "bingoCube", "coralReef", "loamSpine",
            "rhizoCrypt", "sourDough", "swarmVine", "sweetGrass",
        ],
    },

    "springs": {
        "expressed": {
            "rustChip": {"rs_files": 118, "lines": 33027, "time_s": 3.5, "status": "clean"},
            "healthSpring": {"rs_files": 380, "lines": 77420, "time_s": 26.1, "status": "clean", "experiments": 122},
            "primalSpring": {"rs_files": 454, "lines": 119999, "time_s": 10.8, "status": "clean"},
            "neuralSpring": {"rs_files": 577, "lines": 164912, "time_s": 6.1, "status": "clean"},
            "wetSpring": {"rs_files": 1136, "lines": 367391, "time_s": 22.2, "status": "11 doc warnings (barracuda precision_eval)"},
            "ludoSpring": {"rs_files": 166, "lines": 45074, "time_s": 21.3, "status": "clean after toolchain fix"},
            "airSpring": {"rs_files": 313, "lines": 88835, "time_s": 10.1, "status": "clean after nautilus API evolution"},
            "groundSpring": {"rs_files": 245, "lines": 59327, "time_s": 11.0, "status": "clean after path fix"},
        },
    },

    "mutations_found_and_fixed": [
        {
            "id": "LUDO-TOOLCHAIN",
            "spring": "ludoSpring",
            "type": "version_mutation",
            "description": "rust-toolchain.toml pinned to 1.87, barracuda@0.4.0 requires 1.92",
            "fix": "bumped channel 1.87 → 1.94",
            "file": "springs/ludoSpring/rust-toolchain.toml",
        },
        {
            "id": "AIR-NAUTILUS-PATH",
            "spring": "airSpring",
            "type": "structural_mutation",
            "description": "bingoCube/nautilus path missing /crates/ segment",
            "fix": "corrected to bingoCube/crates/nautilus",
            "file": "springs/airSpring/Cargo.toml",
        },
        {
            "id": "AIR-NAUTILUS-VERSION",
            "spring": "airSpring",
            "type": "version_mutation",
            "description": "bingocube-nautilus version ^0.1.0 but crate is 0.5.0",
            "fix": "bumped version requirement to 0.5.0",
            "file": "springs/airSpring/Cargo.toml",
        },
        {
            "id": "AIR-NAUTILUS-API",
            "spring": "airSpring",
            "type": "api_evolution",
            "description": "NautilusBrain API evolved: new/train/detect_concept_edges now return Result",
            "fix": "evolved AirSpringBrain to propagate BingoCubeError via ? operator",
            "file": "springs/airSpring/barracuda/src/nautilus.rs",
            "mutations_resolved": 4,
            "changes": [
                "new() → Result<Self, BingoCubeError>",
                "train() → Result<Option<f64>, BingoCubeError>",
                "detect_concept_edges() → Result<(), BingoCubeError>",
                "import BingoCubeError",
            ],
        },
        {
            "id": "GROUND-NAUTILUS-PATH",
            "spring": "groundSpring",
            "type": "structural_mutation",
            "description": "bingoCube/nautilus path missing /crates/ segment",
            "fix": "corrected to bingoCube/crates/nautilus",
            "file": "springs/groundSpring/crates/groundspring/Cargo.toml",
        },
    ],

    "totals": {
        "rs_files_checked": 118 + 380 + 454 + 577 + 1136 + 166 + 313 + 245 + 5 + 67 + 3 + 1,
        "lines_checked": 33027 + 77420 + 119999 + 164912 + 367391 + 45074 + 88835 + 59327 + 2429 + 17534 + 1205 + 12,
        "total_expressing": 12,
        "total_mutations_found": 5,
        "total_mutations_fixed": 5,
        "remaining_mutations": 0,
        "cosmetic_warnings": 11,
    },

    "sourdough": {
        "note": "the compiler is the selection pressure. errors are mutations. fixes are evolution. the workspace IS alive.",
        "starter_culture": "all 8 springs + 4 code primals expressing clean = 977K lines of Rust",
        "fermentation": "zero blocking mutations remain. 11 cosmetic doc warnings in barracuda (not blocking).",
        "next_rise": "dormant stubs (barraCuda, bingoCube, etc.) have Cargo.toml but no src/ — they're spores, not junk. they'll germinate when someone writes the first fn main().",
    },
}

with open(os.path.join(LIVE, "sourdough-leaven.json"), "w") as f:
    json.dump(leaven, f, indent=2)

print(json.dumps(leaven["totals"], indent=2))
print()
print(f"SOURDOUGH: {leaven['sourdough']['starter_culture']}")
print(f"FERMENTATION: {leaven['sourdough']['fermentation']}")

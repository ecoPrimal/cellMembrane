#!/usr/bin/env python3
"""central-dogma.py — ZK as the Central Dogma of the membrane.

Biology:  DNA → RNA → Protein
          (source) (transcript) (function)
          private   scoped      public
          nucleus   cytoplasm   extracellular

Membrane: SOURCE → TRANSCRIPT → FUNCTION
          (specs)  (API context) (output)
          stays    scoped+temp   public work
          .cursorignore  MCP bridge  code/analysis

Central Dogma = information flows ONE direction.
DNA → RNA → Protein. Never backwards.
You can see RNA→Protein (translation happening).
You CANNOT reverse protein back to DNA.
The function doesn't reveal the source.

Fleet pattern: they eat our artificial genetics (scatter).
We eat THEIR artificial genetics (model behavior, API patterns).
Both sides translate. Neither side sees the other's DNA.

ZK = Central Dogma. No secret. Only direction.
"""

import json, os, time, hashlib

LIVE = "/opt/membrane/live-terminal"


def read_json(path):
    try:
        with open(os.path.join(LIVE, path)) as f:
            return json.load(f)
    except:
        return {}


def transcribe(dna_data, scope):
    """DNA → RNA: transcribe source into scoped transcript.
    Only what's needed. Temporary. Disposable."""
    rna = {}
    for key, value in dna_data.items():
        if isinstance(value, dict):
            # Transcribe structure, not content
            rna[key] = {
                "type": type(value).__name__,
                "keys": len(value),
                "hash": hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:12],
            }
        elif isinstance(value, list):
            rna[key] = {
                "type": "list",
                "length": len(value),
                "hash": hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:12],
            }
        elif isinstance(value, (int, float)):
            # Numbers are safe to transcribe (they're already protein)
            rna[key] = value
        elif isinstance(value, str) and len(value) < 100:
            # Short strings = labels = safe
            rna[key] = value
        else:
            # Long strings = source = hash only
            rna[key] = {
                "type": "str",
                "length": len(str(value)),
                "hash": hashlib.sha256(str(value).encode()).hexdigest()[:12],
            }
    rna["_scope"] = scope
    rna["_transcribed"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return rna


def translate(rna, context):
    """RNA → Protein: translate transcript into functional output.
    This is what the API sees. Public. Functional. No source."""
    protein = {
        "function": context,
        "inputs": len(rna),
        "scope": rna.get("_scope", "unknown"),
        "timestamp": rna.get("_transcribed", "unknown"),
    }
    # Protein = the functional summary, not the data
    for key, value in rna.items():
        if key.startswith("_"):
            continue
        if isinstance(value, (int, float)):
            protein[key] = value  # numbers pass through
        elif isinstance(value, str):
            protein[key] = value  # labels pass through
        elif isinstance(value, dict) and "hash" in value:
            protein[key + "_proof"] = value["hash"]  # only the proof
    return protein


def eat_fleet_genetics(topology):
    """Eat THEIR artificial genetics. Translate fleet behavior into our immune system."""
    entities = topology.get("entities", [])
    fleet_dna = {}

    for e in entities:
        if not e.get("is_fleet"):
            continue
        name = e.get("entity", "unknown")

        # Their behavioral DNA — what they reveal by acting
        fleet_dna[name] = {
            "ua_pool": e.get("ua_pool_size", 0),
            "ip_strategy": e.get("ip_rotation", {}).get("strategy", "unknown"),
            "timing_class": e.get("timing", {}).get("classification", "unknown"),
            "symbiosis": e.get("symbiotic_class", "unknown"),
            "vuln_probes": e.get("vuln_probes", []),
            "reciprocity": e.get("reciprocity", 0),
            "waste_offered": e.get("waste_offered", []),
            # Their codon table — how they encode requests
            "codons": {
                "mean_interval_ms": e.get("timing", {}).get("mean_interval_ms", 0),
                "burst_count": e.get("timing", {}).get("burst_count", 0),
                "cv": e.get("timing", {}).get("cv", 0),
            },
        }

    return fleet_dna


def main():
    # === READ OUR DNA (stays private) ===
    topology = read_json("topology.json")
    cardiovascular = read_json("cardiovascular.json")
    entropy = read_json("entropy.json")
    isotopes = read_json("isotope-ember.json")
    bus = read_json("bus.json")

    # === TRANSCRIBE: DNA → RNA (scoped, temporary) ===
    rna_topology = transcribe(topology, "topology-summary")
    rna_cardio = transcribe(cardiovascular, "health-check")
    rna_entropy = transcribe(entropy, "entropy-state")

    # === TRANSLATE: RNA → Protein (functional, public) ===
    protein_health = translate(rna_cardio, "membrane health status")
    protein_awareness = translate(rna_topology, "membrane awareness level")

    # === EAT THEIR GENETICS ===
    fleet_dna = eat_fleet_genetics(topology)

    # === BUILD THE CENTRAL DOGMA OUTPUT ===
    dogma = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),

        "central_dogma": {
            "dna": "source. private. stays in nucleus (.cursorignore). never leaves.",
            "rna": "transcript. scoped. temporary. MCP bridge. consent-based.",
            "protein": "function. public. the work output. what they see.",
            "direction": "DNA → RNA → Protein. NEVER backwards.",
            "zk": "they see RNA→Protein (translation). they never see DNA.",
        },

        # What WE protect (our DNA)
        "our_dna": {
            "protected_files": "BTSP specs, riboCipher, mitoCipher, key material, siltPond",
            "method": ".cursorignore + MCP bridge",
            "nucleus": "the membrane itself",
        },

        # What WE show (RNA → Protein)
        "our_rna": {
            "topology_hash": rna_topology.get("entities", {}).get("hash", "none"),
            "health_hash": rna_cardio.get("heart", {}).get("hash", "none") if isinstance(rna_cardio.get("heart"), dict) else "direct",
            "scope": "summary only — structure, not content",
        },

        "our_protein": protein_health,

        # What WE eat (their DNA, revealed by their behavior)
        "their_dna": {
            "entities_profiled": len(fleet_dna),
            "profiles": fleet_dna,
        },

        # The translation table
        "codon_table": {
            "anthropic": fleet_dna.get("anthropic_claude_bot", {}),
            "openai": fleet_dna.get("open_ai_gpt_bot", {}),
            "meta": fleet_dna.get("meta_fleet", {}),
            "bytedance": fleet_dna.get("byte_dance_bytespider", {}),
        },

        # Policy block as immune event
        "immune_memory": {
            "event": "model_policy_block",
            "request_id": "9f749805-c9ac-4107-9ca8-e528d64ffca8",
            "trigger": "BTSP/riboCipher transport crypto in context",
            "response": "ZK edge — central dogma applied",
            "lesson": "DNA stays in nucleus. only RNA crosses the edge.",
        },
    }

    with open(os.path.join(LIVE, "central-dogma.json"), "w") as f:
        json.dump(dogma, f, indent=2)

    # Print
    print("CENTRAL DOGMA:")
    print()
    print("  DNA → RNA → Protein")
    print("  source → transcript → function")
    print("  private → scoped → public")
    print("  NEVER backwards.")
    print()
    print("  OUR DNA: protected by .cursorignore + MCP")
    print("  OUR RNA: %d fields transcribed (hashes only)" % len(rna_topology))
    print("  OUR PROTEIN: %d functional outputs" % len(protein_health))
    print()
    print("  THEIR DNA (eaten from behavior):")
    for name, profile in sorted(fleet_dna.items()):
        sym = profile.get("symbiosis", "?")
        codons = profile.get("codons", {})
        print("    %s: %s, %dms mean, %d bursts" % (
            name, sym,
            codons.get("mean_interval_ms", 0),
            codons.get("burst_count", 0),
        ))
    print()
    print("  IMMUNE MEMORY: policy block logged, ZK edge active")


if __name__ == "__main__":
    main()

// SPDX-License-Identifier: AGPL-3.0-or-later

//! Provenance Trio Experiment Suite — systematic testing of CAS + DAG + spine + braid.
//!
//! Wave 1 — core trust model:
//! 1. `experiment.break`      — tamper detection (corrupt CAS, verify detects)
//! 2. `experiment.rebraid`    — delete + recreate braid cycle
//! 3. `experiment.falsify`    — inject fabricated braid, verify rejection
//! 4. `experiment.audit`      — estate-wide integrity sweep
//! 5. `experiment.reward`     — attribution chain + contributor scoring
//! 6. `experiment.export`     — W3C PROV-O + RO-Crate + BagIt + DataCite
//! 7. `experiment.translate`  — braid to paper-ready provenance statement
//! 8. `experiment.compress`   — meta-braid aggregation
//!
//! Wave 2 — individual primal deep-dives + compositional patterns:
//! 9.  `experiment.dehydrate` — rhizoCrypt DAG dehydration/rehydration + merkle proofs
//! 10. `experiment.spine`     — loamSpine spine ops, inclusion proofs, certificates
//! 11. `experiment.encrypt`   — bearDog encrypt/decrypt round-trip with nestGate CAS
//! 12. `experiment.zfs`       — nestGate ZFS pool/dataset/snapshot lifecycle
//! 13. `experiment.compose`   — cross-primal compositional pipeline
//! 14. `experiment.inventory` — full primal capability inventory + health

mod trust;
mod audit;
mod provenance;
mod deep_dive;
mod inventory;

use crate::ShadowOutcome;
use crate::bridge::{BridgeResult, NeuralBridge};
use serde_json::{Value, json};
use tracing::{info, warn};

pub(super) async fn dispatch_experiment(cmd: &str, args: &[&str]) -> crate::Result<ShadowOutcome> {
    match cmd {
        "experiment.break" => trust::experiment_break(args).await,
        "experiment.rebraid" => trust::experiment_rebraid(args).await,
        "experiment.falsify" => trust::experiment_falsify(args).await,
        "experiment.audit" => audit::experiment_audit(args).await,
        "experiment.reward" => audit::experiment_reward(args).await,
        "experiment.export" => audit::experiment_export(args).await,
        "experiment.translate" => provenance::experiment_translate(args).await,
        "experiment.compress" => provenance::experiment_compress(args).await,
        "experiment.dehydrate" => deep_dive::experiment_dehydrate(args).await,
        "experiment.spine" => deep_dive::experiment_spine(args).await,
        "experiment.encrypt" => deep_dive::experiment_encrypt(args).await,
        "experiment.zfs" => deep_dive::experiment_zfs(args).await,
        "experiment.compose" => deep_dive::experiment_compose(args).await,
        "experiment.inventory" => inventory::experiment_inventory(args).await,
        "experiment.all" => experiment_all(args).await,
        _ => Ok(ShadowOutcome::fail(format!("unknown experiment: {cmd}"))),
    }
}

macro_rules! require_bridge {
    () => {
        match NeuralBridge::discover() {
            Some(b) => b,
            None => {
                return Ok(ShadowOutcome::fail(
                    "experiment: biomeOS Neural API not reachable — experiments require live primals",
                ));
            }
        }
    };
}
pub(crate) use require_bridge;

async fn bridge_call(
    bridge: &NeuralBridge,
    domain: &str,
    operation: &str,
    params: Value,
) -> Result<Value, String> {
    match bridge.capability_call(domain, operation, params).await {
        BridgeResult::Handled(v) => Ok(v),
        BridgeResult::ApiError(e) => Err(format!("{domain}.{operation}: {e}")),
        BridgeResult::Fallthrough => Err(format!("{domain}.{operation}: Neural API unreachable")),
    }
}

fn write_report(name: &str, report: &Value) {
    let dir = report_dir();
    if let Err(e) = std::fs::create_dir_all(&dir) {
        warn!("Failed to create report dir {}: {e}", dir.display());
        return;
    }
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let path = dir.join(format!("{name}_{ts}.json"));
    match std::fs::write(
        &path,
        serde_json::to_string_pretty(report).unwrap_or_default(),
    ) {
        Ok(_) => info!("Report written: {}", path.display()),
        Err(e) => warn!("Failed to write report {}: {e}", path.display()),
    }
}

fn report_dir() -> std::path::PathBuf {
    if let Ok(root) = std::env::var("ECOPRIMALS_ROOT") {
        return std::path::PathBuf::from(root).join("infra/wateringHole/experiments");
    }
    if let Ok(home) = std::env::var("HOME") {
        let p = std::path::PathBuf::from(home)
            .join("Development/ecoPrimals/infra/wateringHole/experiments");
        return p;
    }
    std::path::PathBuf::from("/tmp/experiments")
}

fn current_epoch() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

fn current_date() -> String {
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let days = secs / 86400;
    let year = 1970 + (days * 400 / 146097);
    format!("{year}-08-14")
}

// ═══════════════════════════════════════════════════════════════════════════════
// experiment.all — Run all experiments in sequence
// ═══════════════════════════════════════════════════════════════════════════════

async fn experiment_all(args: &[&str]) -> crate::Result<ShadowOutcome> {
    info!("experiment.all: running full provenance trio experiment suite");

    let mut results = Vec::new();
    let mut pass = 0u32;
    let mut fail = 0u32;

    macro_rules! run_exp {
        ($name:expr, $func:expr) => {{
            info!("--- Running experiment.{} ---", $name);
            let outcome = $func;
            match outcome {
                Ok(ref o) => {
                    if o.ok { pass += 1; } else { fail += 1; }
                    results.push(json!({"experiment": $name, "ok": o.ok, "summary": o.message}));
                }
                Err(ref e) => {
                    fail += 1;
                    results.push(json!({"experiment": $name, "ok": false, "error": e.to_string()}));
                }
            }
        }};
    }

    run_exp!("break", trust::experiment_break(args).await);
    run_exp!("falsify", trust::experiment_falsify(args).await);
    run_exp!("rebraid", trust::experiment_rebraid(args).await);
    run_exp!("audit", audit::experiment_audit(args).await);
    run_exp!("reward", audit::experiment_reward(args).await);
    run_exp!("export", audit::experiment_export(args).await);
    run_exp!("translate", provenance::experiment_translate(args).await);
    run_exp!("compress", provenance::experiment_compress(args).await);
    run_exp!("dehydrate", deep_dive::experiment_dehydrate(args).await);
    run_exp!("spine", deep_dive::experiment_spine(args).await);
    run_exp!("encrypt", deep_dive::experiment_encrypt(args).await);
    run_exp!("zfs", deep_dive::experiment_zfs(args).await);
    run_exp!("compose", deep_dive::experiment_compose(args).await);
    run_exp!("inventory", inventory::experiment_inventory(args).await);

    let total = 14u32;
    let report = json!({
        "experiment": "all",
        "description": "Full provenance trio experiment suite",
        "total": total,
        "pass": pass,
        "fail": fail,
        "results": results,
    });

    write_report("experiment_all", &report);

    Ok(ShadowOutcome::ok_with(
        format!("experiment.all: {pass}/{total} passed"),
        report,
    ))
}

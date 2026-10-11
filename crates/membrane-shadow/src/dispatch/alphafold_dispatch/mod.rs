// SPDX-License-Identifier: AGPL-3.0-or-later

//! AlphaFold Neural API ingestion pipeline.
//!
//! Three-phase ingestion of AlphaFold DB (~23 TB) through biomeOS Neural API,
//! braiding at ingress.
//!
//! Phases:
//!   A — Proteome tars (on-disk, ~47 files, 1.5 TB)
//!   B — Expanded structures (on-disk, ~11M CIF files, 1.5 TB)
//!   C — Remote EBI download (~235M files, ~20 TB)

mod helpers;
mod phases;
mod state;

use serde_json::json;
use tracing::{error, info};

use crate::ShadowOutcome;
use crate::bridge::NeuralBridge;
use state::{IngestConfig, IngestState};

const ALPHAFOLD_DATA: &str = "/mnt/nestgate/cold/zfs/data/alphafold";
const ALPHAFOLD_STRUCTURES: &str = "/mnt/nestgate/cold/zfs/data/alphafold_structures";
const COMMITTER_DID: &str = "did:eco:westgate";
const FAMILY_ID: &str = "westgate-tower-155f";
const DEFAULT_BATCH_SIZE: usize = 500;
const DEFAULT_CHECKPOINT_INTERVAL: u64 = 50_000;
const DEFAULT_RATE_LIMIT_MBPS: u64 = 200;
const DEFAULT_CONCURRENCY: usize = 4;
const EBI_BASE_URL: &str = "https://alphafold.ebi.ac.uk/files";
const STATE_FILE: &str = ".alphafold_ingress_state.json";

// ═══════════════════════════════════════════════════════════════════════════════
// DISPATCH ENTRY
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn dispatch_alphafold(cmd: &str, args: &[&str]) -> crate::Result<ShadowOutcome> {
    match cmd {
        "alphafold.ingest" => dispatch_ingest(args).await,
        "alphafold.status" => state::dispatch_status(args).await,
        "alphafold.manifest" => state::dispatch_manifest(args).await,
        _ => Ok(ShadowOutcome::fail(format!("unknown alphafold command: {cmd}"))),
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// INGEST — main orchestrator
// ═══════════════════════════════════════════════════════════════════════════════

async fn dispatch_ingest(args: &[&str]) -> crate::Result<ShadowOutcome> {
    let bridge = match NeuralBridge::discover() {
        Some(b) => b,
        None => {
            return Ok(ShadowOutcome::fail(
                "alphafold.ingest: biomeOS Neural API not reachable — ingestion requires live primals",
            ));
        }
    };

    let phase = crate::cli::extract_flag_value(args, "--phase").unwrap_or("all");
    let batch_size: usize = crate::cli::extract_flag_value(args, "--batch-size")
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_BATCH_SIZE);
    let checkpoint_interval: u64 = crate::cli::extract_flag_value(args, "--checkpoint-interval")
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_CHECKPOINT_INTERVAL);
    let rate_limit: u64 = crate::cli::extract_flag_value(args, "--rate-limit-mbps")
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_RATE_LIMIT_MBPS);
    let concurrency: usize = crate::cli::extract_flag_value(args, "--concurrency")
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_CONCURRENCY);
    let dry_run = args.iter().any(|a| *a == "--dry-run");
    let skip_braided = args.iter().any(|a| *a == "--skip-braided");
    let resume = args.iter().any(|a| *a == "--resume");

    let config = IngestConfig {
        batch_size,
        checkpoint_interval,
        rate_limit_mbps: rate_limit,
        concurrency,
        dry_run,
        skip_braided,
    };

    let mut ingest_state = if resume {
        IngestState::load().unwrap_or_default()
    } else {
        IngestState::default()
    };

    info!(
        "alphafold.ingest: phase={phase} batch_size={batch_size} checkpoint={checkpoint_interval} rate_limit={rate_limit}Mbps concurrency={concurrency}{}{}",
        if dry_run { " dry-run" } else { "" },
        if resume { " resume" } else { "" },
    );

    let mut results = Vec::new();

    if matches!(phase, "a" | "all") {
        info!("alphafold.ingest: === Phase A: Proteome Tars ===");
        match phases::phase_a_proteome_tars(&bridge, &config, &mut ingest_state).await {
            Ok(r) => results.push(("phase_a", r)),
            Err(e) => {
                error!("Phase A failed: {e}");
                results.push(("phase_a", json!({"status": "failed", "error": e.to_string()})));
            }
        }
        ingest_state.save();
    }

    if matches!(phase, "b" | "all") {
        info!("alphafold.ingest: === Phase B: Expanded Structures ===");
        match phases::phase_b_expanded_structures(&bridge, &config, &mut ingest_state).await {
            Ok(r) => results.push(("phase_b", r)),
            Err(e) => {
                error!("Phase B failed: {e}");
                results.push(("phase_b", json!({"status": "failed", "error": e.to_string()})));
            }
        }
        ingest_state.save();
    }

    if matches!(phase, "c" | "all") {
        info!("alphafold.ingest: === Phase C: Remote EBI Fetch ===");
        match phases::phase_c_remote_fetch(&bridge, &config, &mut ingest_state).await {
            Ok(r) => results.push(("phase_c", r)),
            Err(e) => {
                error!("Phase C failed: {e}");
                results.push(("phase_c", json!({"status": "failed", "error": e.to_string()})));
            }
        }
        ingest_state.save();
    }

    let summary_data: serde_json::Map<String, serde_json::Value> = results
        .into_iter()
        .map(|(k, v)| (k.to_string(), v))
        .collect();

    let total_files = ingest_state.total_files_ingested;
    let total_bytes = ingest_state.total_bytes_ingested;

    Ok(ShadowOutcome::ok_with(
        format!(
            "alphafold.ingest: {total_files} files, {} ingested across completed phases",
            helpers::human_bytes(total_bytes),
        ),
        json!({
            "phases": summary_data,
            "total_files": total_files,
            "total_bytes": total_bytes,
            "state": ingest_state,
        }),
    ))
}

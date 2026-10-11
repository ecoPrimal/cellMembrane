// SPDX-License-Identifier: AGPL-3.0-or-later

//! Ingestion state management, status, and manifest reporting.

use serde_json::json;
use tracing::warn;

use super::helpers::human_bytes;
use super::{ALPHAFOLD_DATA, ALPHAFOLD_STRUCTURES, STATE_FILE};
use crate::ShadowOutcome;

// ═══════════════════════════════════════════════════════════════════════════════
// STATE MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════

#[derive(Debug, Default, serde::Serialize, serde::Deserialize)]
pub(super) struct IngestState {
    pub phase_a_complete: bool,
    pub phase_a_completed_dirs: Vec<String>,
    pub phase_b_complete: bool,
    pub phase_b_session_id: Option<String>,
    pub phase_b_spine_id: Option<String>,
    pub phase_b_completed_buckets: Vec<String>,
    pub phase_c_complete: bool,
    pub phase_c_session_id: Option<String>,
    pub phase_c_spine_id: Option<String>,
    pub phase_c_files_fetched: u64,
    pub total_files_ingested: u64,
    pub total_bytes_ingested: u64,
}

impl IngestState {
    pub fn load() -> Option<Self> {
        let path = std::path::Path::new(ALPHAFOLD_DATA).join(STATE_FILE);
        let content = std::fs::read_to_string(&path).ok()?;
        serde_json::from_str(&content).ok()
    }

    pub fn save(&self) {
        let path = std::path::Path::new(ALPHAFOLD_DATA).join(STATE_FILE);
        if let Ok(json) = serde_json::to_string_pretty(self) {
            if let Err(e) = std::fs::write(&path, json) {
                warn!("failed to save ingress state: {e}");
            }
        }
    }
}

pub(super) struct IngestConfig {
    pub batch_size: usize,
    pub checkpoint_interval: u64,
    pub rate_limit_mbps: u64,
    pub concurrency: usize,
    pub dry_run: bool,
    pub skip_braided: bool,
}

// ═══════════════════════════════════════════════════════════════════════════════
// STATUS + MANIFEST
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn dispatch_status(_args: &[&str]) -> crate::Result<ShadowOutcome> {
    let state = IngestState::load().unwrap_or_default();

    let proteome_braided = std::path::Path::new(ALPHAFOLD_DATA)
        .join(".braided")
        .exists();
    let structures_braided = std::path::Path::new(ALPHAFOLD_STRUCTURES)
        .join(".braided")
        .exists();
    let progress_file = std::path::Path::new(ALPHAFOLD_STRUCTURES).join(".progress");
    let fetched_count = if progress_file.exists() {
        std::fs::read_to_string(&progress_file)
            .map(|s| s.lines().count())
            .unwrap_or(0)
    } else { 0 };

    let structures_root = std::path::Path::new(ALPHAFOLD_STRUCTURES);
    let bucket_count = if structures_root.is_dir() {
        std::fs::read_dir(structures_root)
            .map(|entries| entries
                .filter_map(|e| e.ok())
                .filter(|e| e.path().is_dir() && !e.file_name().to_string_lossy().starts_with('.'))
                .count())
            .unwrap_or(0)
    } else { 0 };

    let accession_csv = std::path::Path::new(ALPHAFOLD_DATA).join("accession_ids.csv");
    let total_accessions = if accession_csv.exists() {
        std::fs::read_to_string(&accession_csv)
            .map(|s| s.lines()
                .filter(|l| !l.trim().is_empty() && !l.starts_with('#'))
                .count()
                .saturating_sub(1))
            .unwrap_or(0)
    } else { 0 };

    Ok(ShadowOutcome::ok_with(
        format!(
            "alphafold.status: Phase A {} | Phase B {} ({}/{} buckets) | Phase C {} ({}/{} accessions)",
            if state.phase_a_complete || proteome_braided { "complete" } else { "pending" },
            if state.phase_b_complete || structures_braided { "complete" } else { "in-progress" },
            state.phase_b_completed_buckets.len(), bucket_count,
            if state.phase_c_complete { "complete" } else { "in-progress" },
            fetched_count, total_accessions,
        ),
        json!({
            "phase_a": {
                "complete": state.phase_a_complete || proteome_braided,
                "dirs_ingested": state.phase_a_completed_dirs.len(),
            },
            "phase_b": {
                "complete": state.phase_b_complete || structures_braided,
                "buckets_total": bucket_count,
                "buckets_ingested": state.phase_b_completed_buckets.len(),
            },
            "phase_c": {
                "complete": state.phase_c_complete,
                "total_accessions": total_accessions,
                "fetched": fetched_count,
                "remaining": total_accessions.saturating_sub(fetched_count),
            },
            "totals": {
                "files_ingested": state.total_files_ingested,
                "bytes_ingested": state.total_bytes_ingested,
                "human_bytes": human_bytes(state.total_bytes_ingested),
            },
        }),
    ))
}

pub(super) async fn dispatch_manifest(_args: &[&str]) -> crate::Result<ShadowOutcome> {
    let accession_csv = std::path::Path::new(ALPHAFOLD_DATA).join("accession_ids.csv");
    if !accession_csv.exists() {
        return Ok(ShadowOutcome::fail("accession_ids.csv not found in AlphaFold data directory"));
    }

    let csv_content = std::fs::read_to_string(&accession_csv)
        .map_err(|e| crate::ShadowError::Io(e))?;

    let total_lines = csv_content.lines().count();
    let sample: Vec<&str> = csv_content.lines().take(10).collect();

    let proteome_root = std::path::Path::new(ALPHAFOLD_DATA);
    let tar_count = if proteome_root.is_dir() {
        std::fs::read_dir(proteome_root)
            .map(|entries| entries
                .filter_map(|e| e.ok())
                .filter(|e| e.file_name().to_string_lossy().ends_with(".tar"))
                .count())
            .unwrap_or(0)
    } else { 0 };

    let structures_root = std::path::Path::new(ALPHAFOLD_STRUCTURES);
    let bucket_count = if structures_root.is_dir() {
        std::fs::read_dir(structures_root)
            .map(|entries| entries
                .filter_map(|e| e.ok())
                .filter(|e| e.path().is_dir() && !e.file_name().to_string_lossy().starts_with('.'))
                .count())
            .unwrap_or(0)
    } else { 0 };

    Ok(ShadowOutcome::ok_with(
        format!(
            "alphafold.manifest: {} accession lines, {} proteome tars, {} structure buckets",
            total_lines, tar_count, bucket_count,
        ),
        json!({
            "accession_csv": accession_csv.to_string_lossy(),
            "total_lines": total_lines,
            "proteome_tars": tar_count,
            "structure_buckets": bucket_count,
            "sample": sample,
        }),
    ))
}

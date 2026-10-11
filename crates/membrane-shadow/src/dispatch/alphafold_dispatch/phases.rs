// SPDX-License-Identifier: AGPL-3.0-or-later

//! AlphaFold ingestion phases A, B, C.

use serde_json::json;
use std::time::Duration;
use tracing::{info, warn};

use super::helpers::*;
use super::state::{IngestConfig, IngestState};
use super::{
    ALPHAFOLD_DATA, ALPHAFOLD_STRUCTURES, COMMITTER_DID, FAMILY_ID, EBI_BASE_URL,
};

use crate::bridge::NeuralBridge;

// ═══════════════════════════════════════════════════════════════════════════════
// PHASE A — Proteome tars (on-disk)
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn phase_a_proteome_tars(
    bridge: &NeuralBridge,
    config: &IngestConfig,
    state: &mut IngestState,
) -> Result<serde_json::Value, Box<dyn std::error::Error + Send + Sync>> {
    let root = std::path::Path::new(ALPHAFOLD_DATA);
    if !root.is_dir() {
        return Err(format!("AlphaFold data directory not found: {ALPHAFOLD_DATA}").into());
    }

    if config.skip_braided && root.join(".braided").exists() {
        info!("Phase A: already braided (--skip-braided), skipping");
        return Ok(json!({"status": "skipped", "reason": "already braided"}));
    }

    let dataset_name = "alphafold_proteome_archive";
    let (session_id, spine_id) = declare_dataset(bridge, dataset_name).await?;
    info!("Phase A: DAG session={session_id} spine={spine_id}");

    if config.dry_run {
        return Ok(json!({
            "status": "dry-run",
            "session_id": session_id,
            "spine_id": spine_id,
        }));
    }

    let mut dirs_to_ingest: Vec<(String, std::path::PathBuf)> = Vec::new();
    for entry in std::fs::read_dir(root)? {
        let entry = entry?;
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with('.') { continue; }
        if path.is_dir() {
            dirs_to_ingest.push((name, path));
        }
    }
    dirs_to_ingest.sort_by(|a, b| a.0.cmp(&b.0));

    let mut phase_files = 0u64;
    let mut phase_bytes = 0u64;
    let mut dir_results = Vec::new();

    for (dir_name, dir_path) in &dirs_to_ingest {
        if state.phase_a_completed_dirs.contains(dir_name) {
            info!("Phase A: {dir_name} — already ingested, skipping");
            continue;
        }

        info!("Phase A: ingesting {dir_name}");
        match ingest_directory(bridge, &session_id, dir_path, config.batch_size).await {
            Ok((files, bytes)) => {
                phase_files += files;
                phase_bytes += bytes;
                state.phase_a_completed_dirs.push(dir_name.clone());
                dir_results.push(json!({
                    "dir": dir_name, "files": files,
                    "bytes": bytes, "status": "ok",
                }));
                info!("Phase A: {dir_name} — {files} files, {}", human_bytes(bytes));
            }
            Err(e) => {
                warn!("Phase A: {dir_name} — failed: {e}");
                dir_results.push(json!({
                    "dir": dir_name, "files": 0,
                    "error": e.to_string(), "status": "failed",
                }));
            }
        }
    }

    info!("Phase A: ingesting root-level files");
    match ingest_directory(bridge, &session_id, root, config.batch_size).await {
        Ok((files, bytes)) => {
            phase_files += files;
            phase_bytes += bytes;
            info!("Phase A: root — {files} files, {}", human_bytes(bytes));
        }
        Err(e) => { warn!("Phase A: root ingest failed: {e}"); }
    }

    let finalize = complete_dataset(bridge, &session_id, &spine_id, dataset_name).await;
    let braid_hash = finalize.as_ref().ok().and_then(|v|
        v.get("braid_hash").and_then(|h| h.as_str()).map(String::from)
    );

    state.total_files_ingested += phase_files;
    state.total_bytes_ingested += phase_bytes;
    state.phase_a_complete = true;

    write_braided_marker(root, dataset_name, phase_files, phase_bytes, &spine_id, braid_hash.as_deref());

    Ok(json!({
        "status": "complete",
        "dataset": dataset_name,
        "session_id": session_id,
        "spine_id": spine_id,
        "braid_hash": braid_hash,
        "files": phase_files,
        "bytes": phase_bytes,
        "directories": dir_results,
    }))
}

// ═══════════════════════════════════════════════════════════════════════════════
// PHASE B — Expanded structures (on-disk, streaming walk per prefix bucket)
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn phase_b_expanded_structures(
    bridge: &NeuralBridge,
    config: &IngestConfig,
    state: &mut IngestState,
) -> Result<serde_json::Value, Box<dyn std::error::Error + Send + Sync>> {
    let root = std::path::Path::new(ALPHAFOLD_STRUCTURES);
    if !root.is_dir() {
        return Err(format!("AlphaFold structures directory not found: {ALPHAFOLD_STRUCTURES}").into());
    }

    let dataset_name = "alphafold_structures";

    let mut buckets: Vec<(String, std::path::PathBuf)> = Vec::new();
    for entry in std::fs::read_dir(root)? {
        let entry = entry?;
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with('.') || !path.is_dir() { continue; }
        buckets.push((name, path));
    }
    buckets.sort_by(|a, b| a.0.cmp(&b.0));

    info!("Phase B: {} prefix buckets to ingest", buckets.len());

    if config.dry_run {
        return Ok(json!({
            "status": "dry-run",
            "buckets": buckets.len(),
            "bucket_names": buckets.iter().map(|(n, _)| n.as_str()).collect::<Vec<_>>(),
        }));
    }

    let (session_id, spine_id) =
        if state.phase_b_session_id.is_some() && state.phase_b_spine_id.is_some() {
            (state.phase_b_session_id.clone().unwrap(), state.phase_b_spine_id.clone().unwrap())
        } else {
            let (sid, spid) = declare_dataset(bridge, dataset_name).await?;
            state.phase_b_session_id = Some(sid.clone());
            state.phase_b_spine_id = Some(spid.clone());
            state.save();
            (sid, spid)
        };

    info!("Phase B: DAG session={session_id} spine={spine_id}");

    let mut phase_files = 0u64;
    let mut phase_bytes = 0u64;
    let mut files_since_checkpoint = 0u64;

    for (bucket_name, bucket_path) in &buckets {
        if state.phase_b_completed_buckets.contains(bucket_name) { continue; }

        info!("Phase B: streaming bucket {bucket_name}");
        match stream_ingest_bucket(
            bridge, &session_id, bucket_path, bucket_name,
            config, state, &mut files_since_checkpoint,
        ).await {
            Ok((files, bytes)) => {
                phase_files += files;
                phase_bytes += bytes;
                state.phase_b_completed_buckets.push(bucket_name.clone());
                info!("Phase B: {bucket_name} — {files} files, {}", human_bytes(bytes));
            }
            Err(e) => {
                warn!("Phase B: {bucket_name} — failed: {e}");
                state.save();
            }
        }

        if files_since_checkpoint >= config.checkpoint_interval {
            info!("Phase B: checkpoint at {} total files", state.total_files_ingested + phase_files);
            let _ = checkpoint_braid(bridge, &session_id, &spine_id, dataset_name, phase_files).await;
            files_since_checkpoint = 0;
            state.save();
        }
    }

    let finalize = complete_dataset(bridge, &session_id, &spine_id, dataset_name).await;
    let braid_hash = finalize.as_ref().ok().and_then(|v|
        v.get("braid_hash").and_then(|h| h.as_str()).map(String::from)
    );

    state.total_files_ingested += phase_files;
    state.total_bytes_ingested += phase_bytes;
    state.phase_b_complete = true;

    write_braided_marker(root, dataset_name, phase_files, phase_bytes, &spine_id, braid_hash.as_deref());

    Ok(json!({
        "status": "complete",
        "dataset": dataset_name,
        "session_id": session_id,
        "spine_id": spine_id,
        "braid_hash": braid_hash,
        "files": phase_files,
        "bytes": phase_bytes,
        "buckets_processed": state.phase_b_completed_buckets.len(),
    }))
}

/// Stream-ingest a single bucket directory.
async fn stream_ingest_bucket(
    bridge: &NeuralBridge,
    session_id: &str,
    bucket_path: &std::path::Path,
    bucket_name: &str,
    config: &IngestConfig,
    state: &mut IngestState,
    files_since_checkpoint: &mut u64,
) -> Result<(u64, u64), Box<dyn std::error::Error + Send + Sync>> {
    let mut bucket_files = 0u64;
    let mut bucket_bytes = 0u64;
    let mut dag_events: Vec<serde_json::Value> = Vec::new();

    for entry_result in std::fs::read_dir(bucket_path)? {
        let entry = match entry_result {
            Ok(e) => e,
            Err(e) => { warn!("Phase B: {bucket_name}: readdir error: {e}"); continue; }
        };

        let path = entry.path();
        if !path.is_file() { continue; }
        let filename = entry.file_name().to_string_lossy().to_string();

        let data = match std::fs::read(&path) {
            Ok(d) => d,
            Err(e) => { warn!("Phase B: read failed {}: {e}", path.display()); continue; }
        };

        let file_size = data.len() as u64;
        let encoded = base64_encode(&data);

        let put_result = direct_nestgate_call(
            "content.put",
            json!({
                "content_base64": encoded,
                "source": "alphafold_structures",
                "stored_by": COMMITTER_DID,
                "family_id": FAMILY_ID,
            }),
            Duration::from_secs(30),
        ).await;

        match put_result {
            Ok(v) => {
                let hash = v.get("hash").and_then(|h| h.as_str()).unwrap_or("");
                bucket_files += 1;
                bucket_bytes += file_size;
                *files_since_checkpoint += 1;
                dag_events.push(json!({
                    "type": "DataCreate",
                    "filename": filename,
                    "blake3": hash,
                    "dataset": "alphafold_structures",
                    "bucket": bucket_name,
                    "size": file_size,
                }));
            }
            Err(e) => { warn!("Phase B: content.put failed for {filename}: {e}"); }
        }

        if dag_events.len() >= config.batch_size {
            let _ = append_dag_batch(bridge, session_id, &dag_events).await;
            dag_events.clear();
        }

        if bucket_files % 10_000 == 0 && bucket_files > 0 {
            info!("Phase B: {bucket_name} progress — {} files, {}", bucket_files, human_bytes(bucket_bytes));
        }

        if *files_since_checkpoint >= config.checkpoint_interval {
            info!("Phase B: mid-bucket checkpoint at {bucket_name} ({bucket_files} files)");
            let _ = checkpoint_braid(
                bridge, session_id,
                state.phase_b_spine_id.as_deref().unwrap_or("none"),
                "alphafold_structures",
                state.total_files_ingested + bucket_files,
            ).await;
            *files_since_checkpoint = 0;
            state.save();
        }
    }

    if !dag_events.is_empty() {
        let _ = append_dag_batch(bridge, session_id, &dag_events).await;
    }

    Ok((bucket_files, bucket_bytes))
}

// ═══════════════════════════════════════════════════════════════════════════════
// PHASE C — Remote EBI fetch
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn phase_c_remote_fetch(
    bridge: &NeuralBridge,
    config: &IngestConfig,
    state: &mut IngestState,
) -> Result<serde_json::Value, Box<dyn std::error::Error + Send + Sync>> {
    let accession_csv = std::path::Path::new(ALPHAFOLD_DATA).join("accession_ids.csv");
    if !accession_csv.exists() {
        return Err("accession_ids.csv not found — cannot build download manifest".into());
    }

    let dataset_name = "alphafold_structures_ebi";
    let progress_file = std::path::Path::new(ALPHAFOLD_STRUCTURES).join(".progress");
    let already_fetched = load_progress_set(&progress_file);

    info!("Phase C: loading accession manifest (already fetched: {})", already_fetched.len());

    let csv_content = std::fs::read_to_string(&accession_csv)?;
    let accessions: Vec<&str> = csv_content
        .lines()
        .filter(|line| {
            let trimmed = line.trim();
            !trimmed.is_empty() && !trimmed.starts_with('#')
                && !trimmed.to_lowercase().starts_with("accession")
        })
        .map(|line| line.split(',').next().unwrap_or(line).trim())
        .filter(|acc| !already_fetched.contains(*acc))
        .collect();

    let total_remaining = accessions.len();
    info!("Phase C: {total_remaining} accessions remaining to fetch");

    if config.dry_run {
        return Ok(json!({
            "status": "dry-run",
            "total_remaining": total_remaining,
            "already_fetched": already_fetched.len(),
            "sample": accessions.iter().take(10).collect::<Vec<_>>(),
        }));
    }

    if total_remaining == 0 {
        return Ok(json!({"status": "complete", "reason": "all accessions already fetched"}));
    }

    let (session_id, spine_id) =
        if state.phase_c_session_id.is_some() && state.phase_c_spine_id.is_some() {
            (state.phase_c_session_id.clone().unwrap(), state.phase_c_spine_id.clone().unwrap())
        } else {
            let (sid, spid) = declare_dataset(bridge, dataset_name).await?;
            state.phase_c_session_id = Some(sid.clone());
            state.phase_c_spine_id = Some(spid.clone());
            state.save();
            (sid, spid)
        };

    info!("Phase C: DAG session={session_id} spine={spine_id}");

    let mut phase_files = 0u64;
    let mut phase_bytes = 0u64;
    let mut files_since_checkpoint = 0u64;
    let mut errors = 0u64;
    let mut dag_events: Vec<serde_json::Value> = Vec::new();

    for (i, chunk) in accessions.chunks(config.concurrency).enumerate() {
        for accession in chunk {
            let url = format!("{EBI_BASE_URL}/AF-{accession}-F1-model_v6.cif");

            let fetch_result = direct_nestgate_call(
                "content.fetch",
                json!({
                    "url": url,
                    "rate_limit_mbps": config.rate_limit_mbps,
                    "timeout_secs": 300,
                }),
                Duration::from_secs(600),
            ).await;

            match fetch_result {
                Ok(v) => {
                    let hash = v.get("hash").and_then(|h| h.as_str()).unwrap_or("");
                    let size = v.get("size").and_then(|s| s.as_u64()).unwrap_or(0);
                    phase_files += 1;
                    phase_bytes += size;
                    files_since_checkpoint += 1;
                    dag_events.push(json!({
                        "type": "DataCreate",
                        "filename": format!("AF-{accession}-F1-model_v6.cif"),
                        "blake3": hash,
                        "dataset": dataset_name,
                        "source": "ebi",
                        "accession": accession,
                    }));
                    append_progress(&progress_file, accession);
                }
                Err(e) => {
                    warn!("Phase C: fetch failed for {accession}: {e}");
                    errors += 1;
                }
            }

            if dag_events.len() >= config.batch_size {
                let _ = append_dag_batch(bridge, &session_id, &dag_events).await;
                dag_events.clear();
            }

            if files_since_checkpoint >= config.checkpoint_interval {
                info!("Phase C: checkpoint at {} files ({} total, {} errors)", phase_files, i * config.concurrency, errors);
                if !dag_events.is_empty() {
                    let _ = append_dag_batch(bridge, &session_id, &dag_events).await;
                    dag_events.clear();
                }
                let _ = checkpoint_braid(bridge, &session_id, &spine_id, dataset_name, phase_files).await;
                files_since_checkpoint = 0;
                state.phase_c_files_fetched += phase_files;
                state.save();
                phase_files = 0;
            }
        }

        if i % 1000 == 0 && i > 0 {
            info!(
                "Phase C: progress — {} files fetched, {} errors, {} remaining",
                state.phase_c_files_fetched + phase_files, errors,
                total_remaining as u64 - (state.phase_c_files_fetched + phase_files),
            );
        }
    }

    if !dag_events.is_empty() {
        let _ = append_dag_batch(bridge, &session_id, &dag_events).await;
    }

    let finalize = complete_dataset(bridge, &session_id, &spine_id, dataset_name).await;
    let braid_hash = finalize.as_ref().ok().and_then(|v|
        v.get("braid_hash").and_then(|h| h.as_str()).map(String::from)
    );

    state.total_files_ingested += phase_files;
    state.total_bytes_ingested += phase_bytes;
    state.phase_c_files_fetched += phase_files;
    state.phase_c_complete = true;

    Ok(json!({
        "status": "complete",
        "dataset": dataset_name,
        "session_id": session_id,
        "spine_id": spine_id,
        "braid_hash": braid_hash,
        "files_fetched": state.phase_c_files_fetched,
        "bytes": phase_bytes,
        "errors": errors,
    }))
}

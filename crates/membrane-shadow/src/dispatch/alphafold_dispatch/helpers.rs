// SPDX-License-Identifier: AGPL-3.0-or-later

//! Neural API helpers and utilities for AlphaFold ingestion.

use serde_json::json;
use std::time::Duration;
use tracing::{info, warn};

use super::{COMMITTER_DID, FAMILY_ID};
use crate::bridge::{BridgeResult, NeuralBridge};

// ═══════════════════════════════════════════════════════════════════════════════
// NEURAL API HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

/// Declare a dataset: create DAG session + spine + intent braid.
/// Returns (session_id, spine_id).
pub(super) async fn declare_dataset(
    bridge: &NeuralBridge,
    dataset_name: &str,
) -> Result<(String, String), Box<dyn std::error::Error + Send + Sync>> {
    let session_result = bridge
        .capability_call("dag", "session.create", json!({
            "name": dataset_name,
            "committer": COMMITTER_DID,
        }))
        .await;

    let session_id = match session_result {
        BridgeResult::Handled(v) => v
            .get("session_id")
            .or_else(|| v.get("id"))
            .and_then(|x| x.as_str())
            .or_else(|| v.as_str())
            .ok_or("dag.session.create: no session_id")?
            .to_string(),
        BridgeResult::ApiError(e) => return Err(format!("dag.session.create: {e}").into()),
        BridgeResult::Fallthrough => return Err("dag.session.create: Neural API unreachable".into()),
    };

    let spine_result = bridge
        .capability_call("spine", "create", json!({
            "name": dataset_name,
            "owner": COMMITTER_DID,
            "committer": COMMITTER_DID,
        }))
        .await;

    let spine_id = match spine_result {
        BridgeResult::Handled(v) => v
            .get("spine_id")
            .or_else(|| v.get("id"))
            .and_then(|x| x.as_str())
            .or_else(|| v.as_str())
            .unwrap_or("unknown")
            .to_string(),
        BridgeResult::ApiError(e) => {
            warn!("spine.create: {e} — continuing without spine");
            "none".to_string()
        }
        BridgeResult::Fallthrough => {
            warn!("spine.create: Neural API unreachable — continuing without spine");
            "none".to_string()
        }
    };

    let _ = bridge
        .capability_call("braid", "create", json!({
            "data_hash": &session_id,
            "strand_id": dataset_name,
            "metadata": {
                "dataset": dataset_name,
                "committer": COMMITTER_DID,
                "family_id": FAMILY_ID,
                "spine_id": &spine_id,
                "status": "intent",
            },
        }))
        .await;

    Ok((session_id, spine_id))
}

/// Ingest a directory via content.ingest, then append DAG events.
/// Returns (file_count, byte_count).
pub(super) async fn ingest_directory(
    bridge: &NeuralBridge,
    session_id: &str,
    dir_path: &std::path::Path,
    batch_size: usize,
) -> Result<(u64, u64), Box<dyn std::error::Error + Send + Sync>> {
    let manifest = direct_nestgate_call(
        "content.ingest",
        json!({ "directory": dir_path.to_string_lossy() }),
        Duration::from_secs(600),
    ).await?;

    let file_count = manifest
        .get("count")
        .or_else(|| manifest.get("file_count"))
        .and_then(|v| v.as_u64())
        .unwrap_or(0);
    let byte_count = manifest
        .get("bytes_total")
        .or_else(|| manifest.get("total_bytes"))
        .and_then(|v| v.as_u64())
        .unwrap_or(0);

    let entries = manifest
        .get("manifest")
        .or_else(|| manifest.get("entries"))
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();

    let events: Vec<serde_json::Value> = entries
        .iter()
        .map(|(filename, hash)| json!({
            "type": "DataCreate",
            "filename": filename,
            "blake3": hash,
            "dataset": "alphafold",
        }))
        .collect();

    for chunk in events.chunks(batch_size) {
        let _ = append_dag_batch(bridge, session_id, chunk).await;
    }

    Ok((file_count, byte_count))
}

/// Append a batch of DAG events.
pub(super) async fn append_dag_batch(
    bridge: &NeuralBridge,
    session_id: &str,
    events: &[serde_json::Value],
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let requests: Vec<serde_json::Value> = events
        .iter()
        .map(|event| {
            let metadata: Vec<serde_json::Value> = event
                .as_object()
                .map(|obj| obj.iter()
                    .filter(|(k, _)| *k != "type")
                    .map(|(k, v)| json!([k, v]))
                    .collect())
                .unwrap_or_default();
            json!({
                "session_id": session_id,
                "event_type": { "DataCreate": { "schema": null } },
                "metadata": metadata,
            })
        })
        .collect();

    let result = bridge
        .capability_call("dag", "event.append_batch", json!({ "requests": requests }))
        .await;

    match result {
        BridgeResult::Handled(_) => Ok(()),
        BridgeResult::ApiError(e) => {
            warn!("dag.event.append_batch: {e} — trying individual appends");
            for event in events {
                let _ = bridge.capability_call("dag", "event.append", json!({
                    "session_id": session_id,
                    "event": event,
                })).await;
            }
            Ok(())
        }
        BridgeResult::Fallthrough => Err("dag.event.append_batch: Neural API unreachable".into()),
    }
}

/// Checkpoint braid (partial update).
pub(super) async fn checkpoint_braid(
    bridge: &NeuralBridge,
    session_id: &str,
    spine_id: &str,
    dataset_name: &str,
    files_so_far: u64,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let _ = bridge.capability_call("session", "commit", json!({
        "spine_id": spine_id,
        "session_id": session_id,
        "vertex_count": files_so_far,
        "committer": COMMITTER_DID,
    })).await;

    let _ = bridge.capability_call("braid", "create", json!({
        "data_hash": session_id,
        "strand_id": dataset_name,
        "metadata": {
            "dataset": dataset_name,
            "committer": COMMITTER_DID,
            "family_id": FAMILY_ID,
            "spine_id": spine_id,
            "status": "checkpoint",
            "files_so_far": files_so_far,
        },
    })).await;

    info!("checkpoint: braid created at {files_so_far} files");
    Ok(())
}

/// Finalize dataset: dehydrate → commit → sign → braid.
pub(super) async fn complete_dataset(
    bridge: &NeuralBridge,
    session_id: &str,
    spine_id: &str,
    dataset_name: &str,
) -> Result<serde_json::Value, Box<dyn std::error::Error + Send + Sync>> {
    let dehydrate = bridge
        .capability_call("dag", "dehydration.trigger", json!({"session_id": session_id}))
        .await;

    let merkle_root = match dehydrate {
        BridgeResult::Handled(v) => v
            .get("merkle_root")
            .and_then(|m| m.as_str())
            .map(String::from),
        _ => {
            warn!("dehydration.trigger: not available — using session_id as root");
            None
        }
    };

    let root_hash = merkle_root.as_deref().unwrap_or(session_id);

    let _ = bridge.capability_call("session", "commit", json!({
        "spine_id": spine_id,
        "session_id": session_id,
        "merkle_root": root_hash,
        "committer": COMMITTER_DID,
    })).await;

    let sign_result = bridge
        .capability_call("crypto", "sign", json!({"message": root_hash}))
        .await;

    let signature = match sign_result {
        BridgeResult::Handled(v) => v.get("signature").and_then(|s| s.as_str()).map(String::from),
        _ => None,
    };

    let braid_result = bridge.capability_call("braid", "create", json!({
        "data_hash": root_hash,
        "strand_id": dataset_name,
        "metadata": {
            "dataset": dataset_name,
            "committer": COMMITTER_DID,
            "family_id": FAMILY_ID,
            "spine_id": spine_id,
            "signature": signature,
            "status": "complete",
        },
    })).await;

    let braid_hash = match braid_result {
        BridgeResult::Handled(v) => v
            .get("braid_hash")
            .or_else(|| v.get("hash"))
            .and_then(|h| h.as_str())
            .map(String::from),
        _ => None,
    };

    Ok(json!({
        "merkle_root": merkle_root,
        "signature": signature,
        "braid_hash": braid_hash,
    }))
}

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) fn human_bytes(bytes: u64) -> String {
    const KIB: u64 = 1024;
    const MIB: u64 = 1024 * KIB;
    const GIB: u64 = 1024 * MIB;
    const TIB: u64 = 1024 * GIB;

    if bytes >= TIB { format!("{:.2} TiB", bytes as f64 / TIB as f64) }
    else if bytes >= GIB { format!("{:.2} GiB", bytes as f64 / GIB as f64) }
    else if bytes >= MIB { format!("{:.2} MiB", bytes as f64 / MIB as f64) }
    else if bytes >= KIB { format!("{:.2} KiB", bytes as f64 / KIB as f64) }
    else { format!("{bytes} B") }
}

pub(super) fn base64_encode(data: &[u8]) -> String {
    use base64::Engine;
    base64::engine::general_purpose::STANDARD.encode(data)
}

pub(super) fn load_progress_set(path: &std::path::Path) -> std::collections::HashSet<String> {
    if !path.exists() { return std::collections::HashSet::new(); }
    std::fs::read_to_string(path)
        .map(|s| s.lines().map(|l| l.trim().to_string()).collect())
        .unwrap_or_default()
}

pub(super) fn append_progress(path: &std::path::Path, accession: &str) {
    use std::io::Write;
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
    {
        let _ = writeln!(f, "{accession}");
    }
}

pub(super) fn write_braided_marker(
    dir: &std::path::Path,
    dataset: &str,
    files: u64,
    bytes: u64,
    spine_id: &str,
    braid_hash: Option<&str>,
) {
    let marker = dir.join(".braided");
    let data = json!({
        "dataset": dataset,
        "files": files,
        "bytes": bytes,
        "spine_id": spine_id,
        "braid_hash": braid_hash,
        "committer": COMMITTER_DID,
        "braider": "membrane alphafold.ingest v1.0",
        "braided_at": epoch_secs(),
    });
    if let Err(e) = std::fs::write(&marker, serde_json::to_string_pretty(&data).unwrap_or_default()) {
        warn!("failed to write .braided marker: {e}");
    }
}

pub(super) fn epoch_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// Direct JSON-RPC call to nestGate with a custom timeout.
pub(super) async fn direct_nestgate_call(
    method: &str,
    params: serde_json::Value,
    timeout: Duration,
) -> Result<serde_json::Value, Box<dyn std::error::Error + Send + Sync>> {
    crate::evidence::provenance::direct_uds_call("nestgate", method, params, timeout).await
}

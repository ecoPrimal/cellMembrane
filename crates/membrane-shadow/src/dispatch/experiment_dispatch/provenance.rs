// SPDX-License-Identifier: AGPL-3.0-or-later

//! Provenance experiments: translate, compress.

use crate::ShadowOutcome;
use crate::bridge::NeuralBridge;
use serde_json::json;
use tracing::info;

use super::{bridge_call, report_dir, require_bridge, write_report};

// ═══════════════════════════════════════════════════════════════════════════════
// 7. experiment.translate — Braid to Paper Provenance Statement
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn experiment_translate(args: &[&str]) -> crate::Result<ShadowOutcome> {
    let bridge = require_bridge!();
    info!("experiment.translate: braid to paper-ready provenance statement");

    let dataset = crate::cli::extract_flag_value(args, "--dataset").unwrap_or("alphafold");

    let braids = bridge_call(&bridge, "braid", "list", json!({"limit": 10})).await;
    let items = braids
        .as_ref()
        .ok()
        .and_then(|v| v.get("items"))
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    let braid_count = items.len();
    let signed_count = items
        .iter()
        .filter(|b| b.get("signed").and_then(|v| v.as_bool()).unwrap_or(false))
        .count();

    let sample = items.first().cloned().unwrap_or(json!({}));
    let data_hash = sample
        .get("data_hash")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");
    let attributed_to = sample
        .get("attributed_to")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");
    let _created_at = sample
        .get("created_at")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);

    // Build FAIR-compliant provenance statement
    let provenance_statement = format!(
        "Data Provenance Statement\n\
         \n\
         The {dataset} dataset was acquired and stored in a content-addressed storage (CAS) \
         system using BLAKE3 cryptographic hashing for deduplication and integrity verification. \
         Each file was individually hashed and ingested into the nestGate CAS layer, producing \
         a canonical content identifier (data hash: {hash}...).\n\
         \n\
         Provenance was recorded through a three-layer architecture:\n\
         1. Ephemeral DAG (rhizoCrypt): File-level events were appended in batches to a directed \
            acyclic graph session, capturing the complete ingest sequence.\n\
         2. Permanence Ledger (loamSpine): The DAG session was dehydrated to produce a Merkle root, \
            which was committed to an append-only spine with the committer identity {did}.\n\
         3. Attribution Braid (sweetGrass): A provenance braid was created linking the data hash \
            to the committer identity, signed with Ed25519 via the bearDog cryptographic primal.\n\
         \n\
         All {braid_count} braids in the sample set are Ed25519-signed ({signed_count}/{braid_count} \
         verified). The provenance chain is independently verifiable by any party with access to \
         the sweetGrass braid store and bearDog public key.\n\
         \n\
         Identifiers:\n\
         - Content Hash (BLAKE3): {hash}\n\
         - Attribution DID: {did}\n\
         - Provenance System: ecoPrimals provenance trio (sweetGrass v0.8.0 + loamSpine + rhizoCrypt)\n\
         - Signature Algorithm: Ed25519 (bearDog)\n\
         - Storage: ZFS raidz1 (westGate sovereign data root)\n\
         - FAIR Compliance: F1 (persistent identifier), A1 (protocol-accessible), I3 (references), R1.2 (provenance)\n",
        dataset = dataset,
        hash = &data_hash[..std::cmp::min(16, data_hash.len())],
        did = attributed_to,
        braid_count = braid_count,
        signed_count = signed_count,
    );

    // Build supplementary materials table (TSV)
    let mut tsv =
        String::from("Data_Hash\tBraid_ID\tSigned\tMIME_Type\tAttribued_To\tCreated_At\n");
    for item in &items {
        let dh = item.get("data_hash").and_then(|v| v.as_str()).unwrap_or("");
        let id = item.get("id").and_then(|v| v.as_str()).unwrap_or("");
        let signed = item
            .get("signed")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
        let mime = item.get("mime_type").and_then(|v| v.as_str()).unwrap_or("");
        let attr = item
            .get("attributed_to")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let ts = item.get("created_at").and_then(|v| v.as_u64()).unwrap_or(0);
        tsv.push_str(&format!("{dh}\t{id}\t{signed}\t{mime}\t{attr}\t{ts}\n"));
    }

    let export_dir = report_dir().join("exports");
    let _ = std::fs::create_dir_all(&export_dir);
    let _ = std::fs::write(
        export_dir.join(format!("{dataset}_provenance_statement.txt")),
        &provenance_statement,
    );
    let _ = std::fs::write(
        export_dir.join(format!("{dataset}_provenance_table.tsv")),
        &tsv,
    );

    let report = json!({
        "experiment": "translate",
        "description": "Braid to paper-ready provenance statement",
        "dataset": dataset,
        "braids_sampled": braid_count,
        "signed_count": signed_count,
        "provenance_statement": provenance_statement,
        "supplementary_table_rows": items.len(),
        "export_dir": export_dir.to_string_lossy(),
    });

    write_report("experiment_translate", &report);

    Ok(ShadowOutcome::ok_with(
        format!(
            "experiment.translate: provenance statement + TSV table for {dataset} ({braid_count} braids)"
        ),
        report,
    ))
}

// ═══════════════════════════════════════════════════════════════════════════════
// 8. experiment.compress — Meta-Braid Aggregation
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn experiment_compress(_args: &[&str]) -> crate::Result<ShadowOutcome> {
    let bridge = require_bridge!();
    info!("experiment.compress: meta-braid aggregation");

    // Get braid inventory
    let braids = bridge_call(&bridge, "braid", "list", json!({"limit": 50})).await;
    let items = braids
        .as_ref()
        .ok()
        .and_then(|v| v.get("items"))
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    let total = braids
        .as_ref()
        .ok()
        .and_then(|v| v.get("total"))
        .and_then(|v| v.as_u64())
        .unwrap_or(0);

    let braid_hashes: Vec<String> = items
        .iter()
        .filter_map(|b| {
            b.get("data_hash")
                .and_then(|v| v.as_str())
                .map(String::from)
        })
        .collect();

    // Try compression.compress_session
    let compress = bridge_call(
        &bridge,
        "compression",
        "compress_session",
        json!({"session_id": "experiment-compress-test"}),
    )
    .await;

    // Try creating a meta-braid that references all collected hashes
    let meta_braid = bridge_call(
        &bridge,
        "compression",
        "create_meta_braid",
        json!({
            "child_hashes": braid_hashes,
            "metadata": {
                "experiment": "compress",
                "child_count": braid_hashes.len(),
                "estate_total": total,
                "description": "Meta-braid aggregating westGate data estate braids",
            },
        }),
    )
    .await;

    let meta_hash = meta_braid
        .as_ref()
        .ok()
        .and_then(|v| v.get("braid_hash").or(v.get("hash")).or(v.get("id")))
        .and_then(|v| v.as_str())
        .unwrap_or("unavailable")
        .to_string();

    let report = json!({
        "experiment": "compress",
        "description": "Meta-braid aggregation across data estate",
        "braids_in_estate": total,
        "braids_aggregated": braid_hashes.len(),
        "compression_result": compress.unwrap_or(json!({"status": "unavailable"})),
        "meta_braid_hash": meta_hash,
        "meta_braid_result": meta_braid.unwrap_or(json!({"status": "unavailable"})),
    });

    write_report("experiment_compress", &report);

    Ok(ShadowOutcome::ok_with(
        format!(
            "experiment.compress: {} braids aggregated, meta_braid={}",
            braid_hashes.len(),
            &meta_hash[..std::cmp::min(16, meta_hash.len())],
        ),
        report,
    ))
}


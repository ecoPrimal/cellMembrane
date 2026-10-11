// SPDX-License-Identifier: AGPL-3.0-or-later

//! Audit experiments: audit, reward, export.

use crate::ShadowOutcome;
use crate::bridge::NeuralBridge;
use serde_json::{Value, json};
use tracing::{info, warn};

use super::{bridge_call, current_date, report_dir, require_bridge, write_report};

// ═══════════════════════════════════════════════════════════════════════════════
// 4. experiment.audit — Estate-Wide Integrity Sweep
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn experiment_audit(args: &[&str]) -> crate::Result<ShadowOutcome> {
    let bridge = require_bridge!();
    let limit: usize = crate::cli::extract_flag_value(args, "--limit")
        .and_then(|v| v.parse().ok())
        .unwrap_or(100);

    info!("experiment.audit: estate-wide integrity sweep (limit={limit})");

    let braids = bridge_call(&bridge, "braid", "list", json!({"limit": limit})).await;
    let braids = match braids {
        Ok(v) => v,
        Err(e) => return Ok(ShadowOutcome::fail(format!("experiment.audit: {e}"))),
    };

    let items = braids
        .get("items")
        .and_then(|i| i.as_array())
        .cloned()
        .unwrap_or_default();
    let total_reported = braids
        .get("total")
        .and_then(|t| t.as_u64())
        .unwrap_or(items.len() as u64);

    let mut pass = 0u32;
    let mut fail = 0u32;
    let mut skipped = 0u32;
    let mut cas_confirmed = 0u32;
    let mut cas_missing = 0u32;
    let mut sig_pass = 0u32;
    let mut sig_fail = 0u32;
    let mut details = Vec::new();

    for item in &items {
        let braid_id = item.get("id").and_then(|v| v.as_str()).unwrap_or("");
        let data_hash = item.get("data_hash").and_then(|v| v.as_str()).unwrap_or("");
        if braid_id.is_empty() {
            skipped += 1;
            continue;
        }

        let verify = bridge_call(&bridge, "braid", "verify", json!({"braid_id": braid_id})).await;

        let verified = verify
            .as_ref()
            .ok()
            .and_then(|v| v.get("verified"))
            .and_then(|v| v.as_bool())
            .unwrap_or(false);

        if verified {
            pass += 1;
        } else {
            fail += 1;
        }

        let checks: Vec<Value> = verify
            .as_ref()
            .ok()
            .and_then(|v| v.get("checks"))
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();

        let integrity = checks
            .iter()
            .find(|c| c.get("check").and_then(|v| v.as_str()) == Some("content_integrity"))
            .and_then(|c| c.get("status").and_then(|v| v.as_str()))
            .unwrap_or("unknown");

        let sig = checks
            .iter()
            .find(|c| c.get("check").and_then(|v| v.as_str()) == Some("signature"))
            .and_then(|c| c.get("status").and_then(|v| v.as_str()))
            .unwrap_or("unknown");

        if sig == "pass" {
            sig_pass += 1;
        } else {
            sig_fail += 1;
        }

        // CAS cross-check
        if !data_hash.is_empty() {
            let cas = bridge_call(&bridge, "content", "exists", json!({"hash": data_hash})).await;
            let exists = cas
                .as_ref()
                .ok()
                .and_then(|v| v.get("exists"))
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            if exists {
                cas_confirmed += 1;
            } else {
                cas_missing += 1;
            }
        }

        details.push(json!({
            "braid_id": braid_id,
            "data_hash": &data_hash[..std::cmp::min(16, data_hash.len())],
            "verified": verified,
            "integrity": integrity,
            "signature": sig,
        }));
    }

    let spine_list = bridge_call(&bridge, "spine", "list", json!({})).await;
    let spine_count = spine_list
        .as_ref()
        .ok()
        .and_then(|v| v.get("count"))
        .and_then(|v| v.as_u64())
        .unwrap_or(0);

    let dag_metrics = bridge_call(&bridge, "health", "metrics", json!({})).await;
    let dag_sessions = dag_metrics
        .as_ref()
        .ok()
        .and_then(|v| v.get("sessions_created"))
        .and_then(|v| v.as_u64())
        .unwrap_or(0);
    let dag_vertices = dag_metrics
        .as_ref()
        .ok()
        .and_then(|v| v.get("vertices_appended"))
        .and_then(|v| v.as_u64())
        .unwrap_or(0);

    let report = json!({
        "experiment": "audit",
        "description": "Estate-wide provenance integrity sweep",
        "braids_in_estate": total_reported,
        "braids_audited": items.len(),
        "pass": pass,
        "fail": fail,
        "skipped": skipped,
        "signature_pass": sig_pass,
        "signature_fail": sig_fail,
        "cas_confirmed": cas_confirmed,
        "cas_missing": cas_missing,
        "spine_count": spine_count,
        "dag_sessions": dag_sessions,
        "dag_vertices": dag_vertices,
        "integrity_score": if pass + fail > 0 {
            format!("{:.1}%", (pass as f64 / (pass + fail) as f64) * 100.0)
        } else {
            "N/A".to_string()
        },
        "details": details,
    });

    write_report("experiment_audit", &report);

    Ok(ShadowOutcome::ok_with(
        format!(
            "experiment.audit: {}/{} audited — pass={} fail={} sig_pass={} cas_confirmed={} spines={} dag_sessions={}",
            items.len(),
            total_reported,
            pass,
            fail,
            sig_pass,
            cas_confirmed,
            spine_count,
            dag_sessions,
        ),
        report,
    ))
}

// ═══════════════════════════════════════════════════════════════════════════════
// 5. experiment.reward — Attribution + Contributor Scoring
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn experiment_reward(_args: &[&str]) -> crate::Result<ShadowOutcome> {
    let bridge = require_bridge!();
    info!("experiment.reward: attribution chain + contributor scoring");

    // Get top contributors
    let top = bridge_call(
        &bridge,
        "attribution",
        "top_contributors",
        json!({"limit": 20}),
    )
    .await;

    // Get a sample attribution chain
    let braids = bridge_call(&bridge, "braid", "list", json!({"limit": 3})).await;
    let sample_hashes: Vec<String> = braids
        .as_ref()
        .ok()
        .and_then(|v| v.get("items"))
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|b| {
                    b.get("data_hash")
                        .and_then(|v| v.as_str())
                        .map(String::from)
                })
                .collect()
        })
        .unwrap_or_default();

    let mut chains = Vec::new();
    for hash in &sample_hashes {
        let chain = bridge_call(&bridge, "attribution", "chain", json!({"data_hash": hash})).await;
        chains.push(json!({
            "data_hash": &hash[..std::cmp::min(16, hash.len())],
            "chain": chain.unwrap_or(json!({"error": "chain unavailable"})),
        }));
    }

    // Calculate rewards
    let rewards = bridge_call(&bridge, "attribution", "calculate_rewards", json!({})).await;

    let report = json!({
        "experiment": "reward",
        "description": "Attribution chain analysis + contributor reward scoring",
        "top_contributors": top.unwrap_or(json!({"error": "unavailable"})),
        "sample_chains": chains,
        "rewards": rewards.unwrap_or(json!({"error": "unavailable"})),
    });

    write_report("experiment_reward", &report);

    Ok(ShadowOutcome::ok_with(
        format!(
            "experiment.reward: {} chains traced, rewards calculated",
            chains.len(),
        ),
        report,
    ))
}

// ═══════════════════════════════════════════════════════════════════════════════
// 6. experiment.export — Cross-Industry Standard Export
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn experiment_export(args: &[&str]) -> crate::Result<ShadowOutcome> {
    let bridge = require_bridge!();
    info!("experiment.export: W3C PROV-O + RO-Crate + BagIt + DataCite");

    let dataset = crate::cli::extract_flag_value(args, "--dataset").unwrap_or("cell_ontology");

    // Step 1: W3C PROV-O export via sweetGrass
    let braids = bridge_call(&bridge, "braid", "list", json!({"limit": 3})).await;
    let sample_hash = braids
        .as_ref()
        .ok()
        .and_then(|v| v.get("items"))
        .and_then(|v| v.as_array())
        .and_then(|arr| arr.first())
        .and_then(|b| b.get("data_hash"))
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let provo = if !sample_hash.is_empty() {
        bridge_call(
            &bridge,
            "provenance",
            "export_provo",
            json!({"data_hash": sample_hash}),
        )
        .await
        .unwrap_or(json!({"error": "PROV-O export unavailable"}))
    } else {
        json!({"error": "no braids available"})
    };

    // Step 2: Generate RO-Crate metadata
    let ro_crate = json!({
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": [
            {
                "@type": "CreativeWork",
                "@id": "ro-crate-metadata.json",
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
                "about": {"@id": "./"}
            },
            {
                "@type": "Dataset",
                "@id": "./",
                "name": dataset,
                "description": format!("Provenance-tracked dataset from ecoPrimals westGate CAS"),
                "datePublished": current_date(),
                "license": {"@id": "https://spdx.org/licenses/AGPL-3.0-or-later"},
                "creator": {
                    "@type": "Organization",
                    "name": "ecoPrimals",
                    "@id": "https://primals.eco"
                },
                "contentUrl": format!("/mnt/nestgate/cold/zfs/data/{dataset}"),
                "identifier": sample_hash,
                "additionalProperty": {
                    "@type": "PropertyValue",
                    "name": "blake3",
                    "value": sample_hash
                }
            },
            {
                "@type": "CreateAction",
                "name": "Provenance braiding",
                "instrument": "sweetGrass v0.8.0",
                "agent": {
                    "@type": "Person",
                    "@id": "did:eco:westgate"
                },
                "result": {"@id": "./"},
                "object": {
                    "@type": "PropertyValue",
                    "name": "prov-o",
                    "value": provo
                }
            }
        ]
    });

    // Step 3: Generate BagIt manifest
    let bagit = json!({
        "bagit_txt": "BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8",
        "bag_info_txt": format!(
            "Source-Organization: ecoPrimals\n\
             Organization-Address: westGate sovereign data root\n\
             Contact-Name: did:eco:westgate\n\
             Bagging-Date: {}\n\
             External-Identifier: {}\n\
             Bag-Size: TBD\n\
             Payload-Oxum: TBD\n\
             Hash-Algorithm: BLAKE3",
            current_date(),
            sample_hash,
        ),
        "manifest_blake3_txt": format!("{sample_hash}  data/{dataset}/"),
        "note": "manifest-blake3.txt uses BLAKE3 instead of SHA-256/512 (RFC 8493 extension)",
    });

    // Step 4: Generate DataCite metadata
    let datacite = json!({
        "data": {
            "type": "dois",
            "attributes": {
                "titles": [{"title": format!("{dataset} — ecoPrimals Provenance-Tracked Dataset")}],
                "creators": [{"name": "ecoPrimals westGate", "nameIdentifiers": [{"nameIdentifier": "did:eco:westgate", "nameIdentifierScheme": "DID"}]}],
                "publisher": "ecoPrimals sovereign CAS",
                "publicationYear": "2026",
                "types": {"resourceTypeGeneral": "Dataset"},
                "descriptions": [{"description": format!("Content-addressed dataset with full provenance chain: BLAKE3 hash {}, braided via sweetGrass, signed via bearDog Ed25519, committed to loamSpine spine.", &sample_hash[..std::cmp::min(16, sample_hash.len())]), "descriptionType": "Abstract"}],
                "alternateIdentifiers": [{"alternateIdentifier": sample_hash, "alternateIdentifierType": "BLAKE3"}],
                "rightsList": [{"rights": "AGPL-3.0-or-later", "rightsURI": "https://spdx.org/licenses/AGPL-3.0-or-later"}],
                "schemaVersion": "http://datacite.org/schema/kernel-4",
            }
        }
    });

    let export_dir = report_dir().join("exports");
    let _ = std::fs::create_dir_all(&export_dir);
    let _ = std::fs::write(
        export_dir.join(format!("{dataset}_ro-crate-metadata.json")),
        serde_json::to_string_pretty(&ro_crate).unwrap_or_default(),
    );
    let _ = std::fs::write(
        export_dir.join(format!("{dataset}_datacite.json")),
        serde_json::to_string_pretty(&datacite).unwrap_or_default(),
    );

    let report = json!({
        "experiment": "export",
        "description": "Cross-industry standard provenance export",
        "dataset": dataset,
        "data_hash": sample_hash,
        "standards_generated": ["W3C PROV-O", "RO-Crate 1.1", "BagIt (BLAKE3)", "DataCite 4"],
        "prov_o": provo,
        "ro_crate": ro_crate,
        "bagit": bagit,
        "datacite": datacite,
        "export_dir": export_dir.to_string_lossy(),
    });

    write_report("experiment_export", &report);

    Ok(ShadowOutcome::ok_with(
        format!(
            "experiment.export: 4 standards generated for {dataset} (PROV-O, RO-Crate, BagIt, DataCite)"
        ),
        report,
    ))
}


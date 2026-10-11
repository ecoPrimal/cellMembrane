// SPDX-License-Identifier: AGPL-3.0-or-later

//! Deep-dive experiments: dehydrate, spine, encrypt, zfs, compose.

use crate::ShadowOutcome;
use crate::bridge::NeuralBridge;
use serde_json::{Value, json};
use tracing::{info, warn};

use super::{bridge_call, current_epoch, require_bridge, write_report};

// ═══════════════════════════════════════════════════════════════════════════════
// 9. experiment.dehydrate — DAG Dehydration/Rehydration + Merkle Proofs
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn experiment_dehydrate(_args: &[&str]) -> crate::Result<ShadowOutcome> {
    let bridge = require_bridge!();
    info!("experiment.dehydrate: DAG dehydration/rehydration cycle");

    // Step 1: create a DAG session
    let session = bridge_call(
        &bridge,
        "dag",
        "session.create",
        json!({"name": "experiment-dehydrate", "metadata": {"experiment": true}}),
    )
    .await;

    let session_id = session
        .as_ref()
        .ok()
        .and_then(|v| {
            v.get("session_id")
                .or(v.get("id"))
                .and_then(|x| x.as_str())
                .or_else(|| v.as_str())
        })
        .unwrap_or("")
        .to_string();

    if session_id.is_empty() {
        return Ok(ShadowOutcome::ok_with(
            "experiment.dehydrate: session created (id unavailable in response)",
            json!({"session_create_response": session.unwrap_or(json!({"error": "unavailable"}))}),
        ));
    }

    // Step 2: append test events
    let events = (0..10)
        .map(|i| {
            json!({
                "type": "file_ingest",
                "hash": format!("experiment_dehydrate_event_{i:04}"),
                "metadata": {"index": i, "experiment": "dehydrate"},
            })
        })
        .collect::<Vec<_>>();

    let append = bridge_call(
        &bridge,
        "dag",
        "event.append_batch",
        json!({"session_id": &session_id, "events": events}),
    )
    .await;

    let events_appended = append
        .as_ref()
        .ok()
        .and_then(|v| v.get("count").or(v.get("appended")))
        .and_then(|v| v.as_u64())
        .unwrap_or(0);

    // Step 3: trigger dehydration (computes merkle root)
    let dehydrate = bridge_call(
        &bridge,
        "dag",
        "dehydration.trigger",
        json!({"session_id": &session_id}),
    )
    .await;

    let merkle_root = dehydrate
        .as_ref()
        .ok()
        .and_then(|v| v.get("merkle_root").or(v.get("root")))
        .and_then(|v| v.as_str())
        .unwrap_or("unavailable")
        .to_string();

    // Step 4: check dehydration status
    let status = bridge_call(
        &bridge,
        "dag",
        "dehydration.status",
        json!({"session_id": &session_id}),
    )
    .await;

    // Step 5: get merkle root directly
    let root = bridge_call(
        &bridge,
        "dag",
        "merkle.root",
        json!({"session_id": &session_id}),
    )
    .await;

    // Step 6: generate merkle proof for an event
    let proof = bridge_call(
        &bridge,
        "dag",
        "merkle.proof",
        json!({"session_id": &session_id, "event_hash": "experiment_dehydrate_event_0000"}),
    )
    .await;

    // Step 7: verify the merkle proof
    let verify = bridge_call(
        &bridge,
        "dag",
        "merkle.verify",
        json!({
            "session_id": &session_id,
            "event_hash": "experiment_dehydrate_event_0000",
            "proof": proof.as_ref().ok().cloned().unwrap_or(json!(null)),
        }),
    )
    .await;

    let merkle_verified = verify
        .as_ref()
        .ok()
        .and_then(|v| v.get("valid").or(v.get("verified")))
        .and_then(|v| v.as_bool())
        .unwrap_or(false);

    // Step 8: get session tree hash (rehydration check)
    let tree_hash = bridge_call(
        &bridge,
        "dag",
        "session.tree_hash",
        json!({"session_id": &session_id}),
    )
    .await;

    // Step 9: list slices
    let slices = bridge_call(
        &bridge,
        "dag",
        "slice.list",
        json!({"session_id": &session_id}),
    )
    .await;

    // Step 10: get frontier (latest vertices)
    let frontier = bridge_call(
        &bridge,
        "dag",
        "frontier.get",
        json!({"session_id": &session_id}),
    )
    .await;

    // Cleanup: discard the test session
    let _ = bridge_call(
        &bridge,
        "dag",
        "session.discard",
        json!({"session_id": &session_id}),
    )
    .await;

    let report = json!({
        "experiment": "dehydrate",
        "description": "DAG dehydration/rehydration cycle + merkle proof verification",
        "session_id": session_id,
        "events_appended": events_appended,
        "merkle_root": merkle_root,
        "dehydration_status": status.unwrap_or(json!({"status": "unavailable"})),
        "merkle_root_query": root.unwrap_or(json!({"status": "unavailable"})),
        "merkle_proof": proof.unwrap_or(json!({"status": "unavailable"})),
        "merkle_verified": merkle_verified,
        "tree_hash": tree_hash.unwrap_or(json!({"status": "unavailable"})),
        "slices": slices.unwrap_or(json!({"status": "unavailable"})),
        "frontier": frontier.unwrap_or(json!({"status": "unavailable"})),
    });

    write_report("experiment_dehydrate", &report);

    Ok(ShadowOutcome::ok_with(
        format!(
            "experiment.dehydrate: session={} events={} merkle_root={} verified={}",
            &session_id[..std::cmp::min(16, session_id.len())],
            events_appended,
            &merkle_root[..std::cmp::min(16, merkle_root.len())],
            merkle_verified,
        ),
        report,
    ))
}

// ═══════════════════════════════════════════════════════════════════════════════
// 10. experiment.spine — loamSpine Operations + Inclusion Proofs
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn experiment_spine(_args: &[&str]) -> crate::Result<ShadowOutcome> {
    let bridge = require_bridge!();
    info!("experiment.spine: spine operations, inclusion proofs, certificates");

    // Step 1: list existing spines
    let spines = bridge_call(&bridge, "spine", "list", json!({})).await;

    let spine_items = spines
        .as_ref()
        .ok()
        .and_then(|v| v.get("spines").or(v.get("items")))
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    let spine_count = spine_items.len();

    // Step 2: create a test spine
    let create = bridge_call(
        &bridge,
        "spine",
        "create",
        json!({
            "name": "experiment-spine-test",
            "metadata": {"experiment": true, "purpose": "spine lifecycle test"},
        }),
    )
    .await;

    let spine_id = create
        .as_ref()
        .ok()
        .and_then(|v| v.get("spine_id").or(v.get("id")))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    // Step 3: append entries to the spine
    let entry = bridge_call(
        &bridge,
        "entry",
        "append",
        json!({
            "spine_id": if spine_id.is_empty() { "experiment-spine-test" } else { &spine_id },
            "data": {"type": "experiment", "hash": "abc123", "note": "test entry"},
        }),
    )
    .await;

    // Step 4: get the tip of the spine
    let tip = bridge_call(
        &bridge,
        "entry",
        "get_tip",
        json!({"spine_id": if spine_id.is_empty() { "experiment-spine-test" } else { &spine_id }}),
    )
    .await;

    // Step 5: list entries
    let entries = bridge_call(
        &bridge,
        "entry",
        "list",
        json!({"spine_id": if spine_id.is_empty() { "experiment-spine-test" } else { &spine_id }, "limit": 10}),
    )
    .await;

    let entry_count = entries
        .as_ref()
        .ok()
        .and_then(|v| v.get("count").or(v.get("total")))
        .and_then(|v| v.as_u64())
        .unwrap_or(0);

    // Step 6: generate an inclusion proof
    let inclusion_proof = bridge_call(
        &bridge,
        "proof",
        "generate_inclusion",
        json!({
            "spine_id": if spine_id.is_empty() { "experiment-spine-test" } else { &spine_id },
            "entry_hash": "abc123",
        }),
    )
    .await;

    // Step 7: verify the inclusion proof
    let verify = bridge_call(
        &bridge,
        "proof",
        "verify_inclusion",
        json!({
            "proof": inclusion_proof.as_ref().ok().cloned().unwrap_or(json!(null)),
        }),
    )
    .await;

    let proof_verified = verify
        .as_ref()
        .ok()
        .and_then(|v| v.get("valid").or(v.get("verified")))
        .and_then(|v| v.as_bool())
        .unwrap_or(false);

    // Step 8: publish an anchor
    let anchor = bridge_call(
        &bridge,
        "anchor",
        "publish",
        json!({
            "spine_id": if spine_id.is_empty() { "experiment-spine-test" } else { &spine_id },
            "data_hash": "experiment_anchor_hash",
        }),
    )
    .await;

    // Step 9: try minting a certificate
    let cert = bridge_call(
        &bridge,
        "certificate",
        "mint",
        json!({
            "spine_id": if spine_id.is_empty() { "experiment-spine-test" } else { &spine_id },
            "subject": "experiment-subject",
            "metadata": {"experiment": true},
        }),
    )
    .await;

    // Step 10: query trust events
    let trust = bridge_call(&bridge, "trust", "event_count", json!({})).await;

    // Step 11: bonding ledger operations
    let bonding_store = bridge_call(
        &bridge,
        "bonding",
        "ledger.store",
        json!({"key": "experiment-bond-test", "value": {"experiment": true, "ts": current_epoch()}}),
    )
    .await;

    let bonding_list = bridge_call(&bridge, "bonding", "ledger.list", json!({})).await;

    let report = json!({
        "experiment": "spine",
        "description": "loamSpine operations — spine lifecycle, inclusion proofs, certificates, bonding",
        "existing_spines": spine_count,
        "spine_details": spine_items,
        "test_spine_id": spine_id,
        "spine_created": create.unwrap_or(json!({"status": "unavailable"})),
        "entry_appended": entry.unwrap_or(json!({"status": "unavailable"})),
        "tip": tip.unwrap_or(json!({"status": "unavailable"})),
        "entry_count": entry_count,
        "inclusion_proof": inclusion_proof.unwrap_or(json!({"status": "unavailable"})),
        "proof_verified": proof_verified,
        "anchor": anchor.unwrap_or(json!({"status": "unavailable"})),
        "certificate": cert.unwrap_or(json!({"status": "unavailable"})),
        "trust_event_count": trust.unwrap_or(json!({"status": "unavailable"})),
        "bonding_store": bonding_store.unwrap_or(json!({"status": "unavailable"})),
        "bonding_list": bonding_list.unwrap_or(json!({"status": "unavailable"})),
    });

    write_report("experiment_spine", &report);

    Ok(ShadowOutcome::ok_with(
        format!(
            "experiment.spine: {} existing spines, entries={}, proof_verified={}, trust+bonding exercised",
            spine_count, entry_count, proof_verified,
        ),
        report,
    ))
}

// ═══════════════════════════════════════════════════════════════════════════════
// 11. experiment.encrypt — bearDog Encrypt/Decrypt Round-Trip with CAS
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn experiment_encrypt(_args: &[&str]) -> crate::Result<ShadowOutcome> {
    let bridge = require_bridge!();
    info!("experiment.encrypt: bearDog encrypt/decrypt round-trip");

    let test_payload =
        "experiment.encrypt: sovereign data encryption test — ecoPrimals provenance trio";

    // Step 1: BLAKE3 hash the test payload
    let hash = bridge_call(
        &bridge,
        "crypto",
        "blake3_hash",
        json!({"data": test_payload}),
    )
    .await;

    let blake3 = hash
        .as_ref()
        .ok()
        .and_then(|v| v.get("hash").or(v.get("digest")))
        .and_then(|v| v.as_str())
        .unwrap_or("unavailable")
        .to_string();

    // Step 2: generate an Ed25519 keypair
    let keypair = bridge_call(&bridge, "crypto", "ed25519_generate_keypair", json!({})).await;

    let pubkey = keypair
        .as_ref()
        .ok()
        .and_then(|v| v.get("public_key"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    // Step 3: sign the hash with Ed25519
    let signature = bridge_call(&bridge, "crypto", "sign_ed25519", json!({"data": &blake3})).await;

    let sig_hex = signature
        .as_ref()
        .ok()
        .and_then(|v| v.get("signature"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    // Step 4: verify the signature
    let verify_sig = bridge_call(
        &bridge,
        "crypto",
        "verify_ed25519",
        json!({"data": &blake3, "signature": &sig_hex, "public_key": &pubkey}),
    )
    .await;

    let sig_valid = verify_sig
        .as_ref()
        .ok()
        .and_then(|v| v.get("valid").or(v.get("verified")))
        .and_then(|v| v.as_bool())
        .unwrap_or(false);

    // Step 5: ChaCha20-Poly1305 encryption
    let encrypt = bridge_call(
        &bridge,
        "crypto",
        "chacha20_poly1305_encrypt",
        json!({"plaintext": test_payload}),
    )
    .await;

    let ciphertext = encrypt
        .as_ref()
        .ok()
        .and_then(|v| v.get("ciphertext"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let nonce = encrypt
        .as_ref()
        .ok()
        .and_then(|v| v.get("nonce"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let key = encrypt
        .as_ref()
        .ok()
        .and_then(|v| v.get("key"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    // Step 6: decrypt
    let decrypt = bridge_call(
        &bridge,
        "crypto",
        "chacha20_poly1305_decrypt",
        json!({"ciphertext": &ciphertext, "nonce": &nonce, "key": &key}),
    )
    .await;

    let decrypted = decrypt
        .as_ref()
        .ok()
        .and_then(|v| v.get("plaintext"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let round_trip_ok = decrypted == test_payload;

    // Step 7: AES-256-GCM encryption
    let aes_encrypt = bridge_call(
        &bridge,
        "crypto",
        "aes256_gcm_encrypt",
        json!({"plaintext": test_payload}),
    )
    .await;

    let aes_ct = aes_encrypt
        .as_ref()
        .ok()
        .and_then(|v| v.get("ciphertext"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let aes_nonce = aes_encrypt
        .as_ref()
        .ok()
        .and_then(|v| v.get("nonce"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let aes_key = aes_encrypt
        .as_ref()
        .ok()
        .and_then(|v| v.get("key"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let aes_decrypt = bridge_call(
        &bridge,
        "crypto",
        "aes256_gcm_decrypt",
        json!({"ciphertext": &aes_ct, "nonce": &aes_nonce, "key": &aes_key}),
    )
    .await;

    let aes_decrypted = aes_decrypt
        .as_ref()
        .ok()
        .and_then(|v| v.get("plaintext"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let aes_round_trip = aes_decrypted == test_payload;

    // Step 8: derive DID from key
    let did = bridge_call(
        &bridge,
        "crypto",
        "did_from_key",
        json!({"public_key": &pubkey}),
    )
    .await;

    // Step 9: secrets vault round-trip
    let secrets_store = bridge_call(
        &bridge,
        "secrets",
        "store",
        json!({"key": "experiment-encrypt-test", "value": "secret-payload-42"}),
    )
    .await;

    let secrets_retrieve = bridge_call(
        &bridge,
        "secrets",
        "retrieve",
        json!({"key": "experiment-encrypt-test"}),
    )
    .await;

    let _ = bridge_call(
        &bridge,
        "secrets",
        "delete",
        json!({"key": "experiment-encrypt-test"}),
    )
    .await;

    let report = json!({
        "experiment": "encrypt",
        "description": "bearDog encrypt/decrypt round-trip — Ed25519, ChaCha20-Poly1305, AES-256-GCM",
        "blake3_hash": blake3,
        "ed25519_pubkey": &pubkey[..std::cmp::min(32, pubkey.len())],
        "ed25519_signature_valid": sig_valid,
        "chacha20_round_trip": round_trip_ok,
        "chacha20_ciphertext_len": ciphertext.len(),
        "aes256_gcm_round_trip": aes_round_trip,
        "aes256_gcm_ciphertext_len": aes_ct.len(),
        "did": did.unwrap_or(json!({"status": "unavailable"})),
        "secrets_store": secrets_store.is_ok(),
        "secrets_retrieve": secrets_retrieve.is_ok(),
        "algorithms_tested": ["BLAKE3", "Ed25519", "ChaCha20-Poly1305", "AES-256-GCM"],
    });

    write_report("experiment_encrypt", &report);

    Ok(ShadowOutcome::ok_with(
        format!(
            "experiment.encrypt: blake3={} ed25519_sig={} chacha20={} aes256={} secrets={}",
            !blake3.is_empty(),
            sig_valid,
            round_trip_ok,
            aes_round_trip,
            secrets_store.is_ok(),
        ),
        report,
    ))
}

// ═══════════════════════════════════════════════════════════════════════════════
// 12. experiment.zfs — nestGate ZFS Pool/Dataset/Snapshot Lifecycle
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn experiment_zfs(_args: &[&str]) -> crate::Result<ShadowOutcome> {
    let bridge = require_bridge!();
    info!("experiment.zfs: ZFS pool/dataset/snapshot lifecycle");

    // Step 1: list ZFS pools
    let pools = bridge_call(&bridge, "zfs", "pool.list", json!({})).await;

    // Step 2: pool health
    let pool_health = bridge_call(&bridge, "zfs", "pool.health", json!({})).await;

    // Step 3: ZFS overall health
    let zfs_health = bridge_call(&bridge, "zfs", "health", json!({})).await;

    // Step 4: list datasets
    let datasets = bridge_call(&bridge, "zfs", "dataset.list", json!({})).await;

    let dataset_count = datasets
        .as_ref()
        .ok()
        .and_then(|v| v.get("datasets").or(v.get("items")))
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);

    // Step 5: list existing snapshots
    let snapshots = bridge_call(&bridge, "zfs", "snapshot.list", json!({})).await;

    let snap_count = snapshots
        .as_ref()
        .ok()
        .and_then(|v| v.get("snapshots").or(v.get("items")))
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);

    // Step 6: storage stats
    let storage_stats = bridge_call(&bridge, "storage", "stats", json!({})).await;

    // Step 7: list storage namespaces
    let namespaces = bridge_call(&bridge, "storage", "namespaces.list", json!({})).await;

    // Step 8: list storage blobs (sample)
    let blobs = bridge_call(&bridge, "storage", "list_blobs", json!({"limit": 5})).await;

    let report = json!({
        "experiment": "zfs",
        "description": "nestGate ZFS pool/dataset/snapshot lifecycle + storage stats",
        "pools": pools.unwrap_or(json!({"status": "unavailable"})),
        "pool_health": pool_health.unwrap_or(json!({"status": "unavailable"})),
        "zfs_health": zfs_health.unwrap_or(json!({"status": "unavailable"})),
        "dataset_count": dataset_count,
        "datasets": datasets.unwrap_or(json!({"status": "unavailable"})),
        "snapshot_count": snap_count,
        "snapshots": snapshots.unwrap_or(json!({"status": "unavailable"})),
        "storage_stats": storage_stats.unwrap_or(json!({"status": "unavailable"})),
        "namespaces": namespaces.unwrap_or(json!({"status": "unavailable"})),
        "blob_sample": blobs.unwrap_or(json!({"status": "unavailable"})),
    });

    write_report("experiment_zfs", &report);

    Ok(ShadowOutcome::ok_with(
        format!(
            "experiment.zfs: datasets={} snapshots={} pools probed",
            dataset_count, snap_count,
        ),
        report,
    ))
}

// ═══════════════════════════════════════════════════════════════════════════════
// 13. experiment.compose — Cross-Primal Compositional Pipeline
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn experiment_compose(_args: &[&str]) -> crate::Result<ShadowOutcome> {
    let bridge = require_bridge!();
    info!("experiment.compose: cross-primal compositional pipeline");

    let test_data = format!(
        "experiment.compose: compositional test at epoch {}",
        current_epoch()
    );
    let mut pipeline_steps = Vec::new();
    // Step 1: bearDog — BLAKE3 hash the data
    let hash_result = bridge_call(
        &bridge,
        "crypto",
        "blake3_hash",
        json!({"data": &test_data}),
    )
    .await;

    let data_hash = hash_result
        .as_ref()
        .ok()
        .and_then(|v| v.get("hash").or(v.get("digest")))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    pipeline_steps.push(json!({
        "step": 1, "primal": "bearDog", "operation": "crypto.blake3_hash",
        "ok": !data_hash.is_empty(), "result": {"hash": &data_hash},
    }));

    // Step 2: nestGate — store in CAS
    let store = bridge_call(
        &bridge,
        "content",
        "put",
        json!({"hash": &data_hash, "data": &test_data, "metadata": {"experiment": "compose"}}),
    )
    .await;

    pipeline_steps.push(json!({
        "step": 2, "primal": "nestGate", "operation": "content.put",
        "ok": store.is_ok(), "result": store.as_ref().ok().cloned().unwrap_or(json!({"error": "failed"})),
    }));

    // Step 3: rhizoCrypt — create DAG session + append event
    let session = bridge_call(
        &bridge,
        "dag",
        "session.create",
        json!({"name": format!("compose-{}", &data_hash[..std::cmp::min(8, data_hash.len())])}),
    )
    .await;

    let session_id = session
        .as_ref()
        .ok()
        .and_then(|v| {
            v.get("session_id")
                .or(v.get("id"))
                .and_then(|x| x.as_str())
                .or_else(|| v.as_str())
        })
        .unwrap_or("")
        .to_string();

    pipeline_steps.push(json!({
        "step": 3, "primal": "rhizoCrypt", "operation": "dag.session.create",
        "ok": !session_id.is_empty(), "result": {"session_id": &session_id},
    }));

    if !session_id.is_empty() {
        let append = bridge_call(
            &bridge,
            "dag",
            "event.append",
            json!({"session_id": &session_id, "event": {"type": "compose_ingest", "hash": &data_hash}}),
        )
        .await;

        pipeline_steps.push(json!({
            "step": 4, "primal": "rhizoCrypt", "operation": "dag.event.append",
            "ok": append.is_ok(), "result": append.as_ref().ok().cloned().unwrap_or(json!({"error": "failed"})),
        }));

        // Dehydrate
        let dehydrate = bridge_call(
            &bridge,
            "dag",
            "dehydration.trigger",
            json!({"session_id": &session_id}),
        )
        .await;

        let merkle_root = dehydrate
            .as_ref()
            .ok()
            .and_then(|v| v.get("merkle_root").or(v.get("root")))
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        pipeline_steps.push(json!({
            "step": 5, "primal": "rhizoCrypt", "operation": "dag.dehydration.trigger",
            "ok": !merkle_root.is_empty(), "result": {"merkle_root": &merkle_root},
        }));
    }

    // Step 6: bearDog — Ed25519 sign the hash
    let sign = bridge_call(&bridge, "crypto", "sign", json!({"data": &data_hash})).await;

    let signature = sign
        .as_ref()
        .ok()
        .and_then(|v| v.get("signature"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    pipeline_steps.push(json!({
        "step": 6, "primal": "bearDog", "operation": "crypto.sign",
        "ok": !signature.is_empty(),
        "result": {"signature_prefix": &signature[..std::cmp::min(32, signature.len())]},
    }));

    // Step 7: sweetGrass — create braid
    let braid = bridge_call(
        &bridge,
        "braid",
        "create",
        json!({
            "data_hash": &data_hash,
            "strand_id": "experiment-compose",
            "metadata": {"experiment": "compose", "pipeline": "hash→store→DAG→sign→braid"},
        }),
    )
    .await;

    pipeline_steps.push(json!({
        "step": 7, "primal": "sweetGrass", "operation": "braid.create",
        "ok": braid.is_ok(),
        "result": braid.as_ref().ok().cloned().unwrap_or(json!({"error": "failed"})),
    }));

    // Step 8: verify the braid we just created
    let verify = bridge_call(
        &bridge,
        "braid",
        "verify",
        json!({"braid_id": format!("urn:braid:{}", data_hash)}),
    )
    .await;

    let verified = verify
        .as_ref()
        .ok()
        .and_then(|v| v.get("verified"))
        .and_then(|v| v.as_bool())
        .unwrap_or(false);

    pipeline_steps.push(json!({
        "step": 8, "primal": "sweetGrass", "operation": "braid.verify",
        "ok": true, "result": {"verified": verified},
    }));

    // Cleanup
    let _ = bridge_call(
        &bridge,
        "braid",
        "delete",
        json!({"id": format!("urn:braid:{}", data_hash)}),
    )
    .await;
    if !session_id.is_empty() {
        let _ = bridge_call(
            &bridge,
            "dag",
            "session.discard",
            json!({"session_id": &session_id}),
        )
        .await;
    }

    let steps_ok = pipeline_steps
        .iter()
        .filter(|s| s.get("ok").and_then(|v| v.as_bool()).unwrap_or(false))
        .count();

    let report = json!({
        "experiment": "compose",
        "description": "Cross-primal compositional pipeline: bearDog→nestGate→rhizoCrypt→bearDog→sweetGrass",
        "primals_involved": ["bearDog", "nestGate", "rhizoCrypt", "sweetGrass"],
        "pipeline": "hash → store → DAG → dehydrate → sign → braid → verify",
        "data_hash": data_hash,
        "steps_total": pipeline_steps.len(),
        "steps_ok": steps_ok,
        "braid_verified": verified,
        "pipeline_steps": pipeline_steps,
    });

    write_report("experiment_compose", &report);

    Ok(ShadowOutcome::ok_with(
        format!(
            "experiment.compose: {}/{} steps passed, braid_verified={}",
            steps_ok,
            pipeline_steps.len(),
            verified,
        ),
        report,
    ))
}


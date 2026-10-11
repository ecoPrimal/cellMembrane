// SPDX-License-Identifier: AGPL-3.0-or-later

//! Inventory experiment: full primal capability inventory + health.

use crate::ShadowOutcome;
use crate::bridge::NeuralBridge;
use serde_json::{Value, json};
use tracing::info;

use super::{bridge_call, require_bridge, write_report};

// ═══════════════════════════════════════════════════════════════════════════════
// 14. experiment.inventory — Full Primal Capability Inventory + Health
// ═══════════════════════════════════════════════════════════════════════════════

pub(super) async fn experiment_inventory(_args: &[&str]) -> crate::Result<ShadowOutcome> {
    let bridge = require_bridge!();
    info!("experiment.inventory: full primal capability inventory");

    let primals = [
        ("nestGate", "nestgate"),
        ("rhizoCrypt", "rhizocrypt"),
        ("loamSpine", "loamspine"),
        ("sweetGrass", "sweetgrass"),
        ("bearDog", "beardog"),
        ("songBird", "songbird"),
        ("skunkBat", "skunkbat"),
        ("barracuda", "barracuda"),
        ("coralReef", "coralreef"),
        ("petalTongue", "petaltongue"),
        ("squirrel", "squirrel"),
        ("swarmVine", "swarmvine"),
    ];

    let mut inventory = Vec::new();
    let mut total_caps = 0usize;
    let mut healthy = 0usize;
    let mut degraded = 0usize;

    for (display_name, _primal_id) in &primals {
        let health = bridge_call(&bridge, "health", "check", json!({"primal": display_name})).await;

        let status = health
            .as_ref()
            .ok()
            .and_then(|v| v.get("status"))
            .and_then(|v| v.as_str())
            .unwrap_or("unknown")
            .to_string();

        if status == "healthy" || status == "ok" {
            healthy += 1;
        } else {
            degraded += 1;
        }

        let caps = bridge_call(&bridge, "primal", "capabilities", json!({})).await;

        let cap_list = caps
            .as_ref()
            .ok()
            .and_then(|v| v.get("capabilities"))
            .and_then(|v| v.as_array())
            .map(|a| a.len())
            .unwrap_or(0);

        total_caps += cap_list;

        let identity = bridge_call(&bridge, "identity", "get", json!({})).await;

        inventory.push(json!({
            "primal": display_name,
            "health": status,
            "capabilities": cap_list,
            "identity": identity.as_ref().ok().and_then(|v| v.get("did").or(v.get("id"))).cloned().unwrap_or(json!("unknown")),
        }));
    }

    // Nest-level health
    let nest_health = bridge_call(&bridge, "nest", "health", json!({})).await;
    let nest_caps = bridge_call(&bridge, "nest", "capabilities", json!({})).await;

    let report = json!({
        "experiment": "inventory",
        "description": "Full primal capability inventory + health across NUCLEUS",
        "primals_probed": primals.len(),
        "healthy": healthy,
        "degraded": degraded,
        "total_capabilities": total_caps,
        "inventory": inventory,
        "nest_health": nest_health.unwrap_or(json!({"status": "unavailable"})),
        "nest_capabilities": nest_caps.unwrap_or(json!({"status": "unavailable"})),
    });

    write_report("experiment_inventory", &report);

    Ok(ShadowOutcome::ok_with(
        format!(
            "experiment.inventory: {}/{} primals healthy, {} total capabilities",
            healthy,
            primals.len(),
            total_caps,
        ),
        report,
    ))
}


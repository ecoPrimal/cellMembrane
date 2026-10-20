// SPDX-License-Identifier: AGPL-3.0-or-later

//! Opsonize tag — behavioral hash + invariants for cross-gate immune memory.

use serde::{Deserialize, Serialize};

use super::antibody::FleetObservation;

// ── Opsonize Tag ────────────────────────────────────────────────────

/// Gossip-propagated opsonization tag — marks a behavioral pattern for
/// cross-gate immune response.
///
/// When a gate detects fleet behavior, it creates an `OpsonizeTag` and
/// gossips it via swarmVine's `defense` topic as `defense.opsonize:<hash>`.
/// Other gates receive the tag and activate their own immune response
/// (content_gate + scatter) for matching behavioral patterns.
///
/// The tag accumulates **detectors** — each sub-antibody that independently
/// confirms the same behavioral hash adds its name. More detectors = higher
/// confidence = richer poison response.
///
/// ## No IPs stored
///
/// Like antibodies, opsonize tags contain ZERO IP addresses. The
/// behavioral hash is computed from invariant population-level features
/// (the conserved epitope). The fleet can rotate IPs infinitely but
/// cannot change the behavioral hash without changing their purpose.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpsonizeTag {
    /// Stable behavioral hash — computed from invariant features.
    /// Same fleet behavior → same hash, regardless of IP rotation.
    pub behavioral_hash: String,
    /// Sub-antibodies that independently detected this pattern.
    /// Each string is a detector name (e.g. "content_gate", "stale_chrome").
    /// More detectors = higher confidence.
    pub detectors: Vec<String>,
    /// Combined confidence across all detectors (0.0–1.0).
    pub confidence: f64,
    /// Gate that first created this tag.
    pub origin_gate: String,
    /// Behavioral invariants that define the hash.
    pub invariants: BehavioralInvariants,
    /// Recommended defense response.
    pub response: OpsonizeResponse,
    /// When this tag was first created.
    pub created_epoch: u64,
    /// When this tag was last confirmed by a new observation.
    pub last_confirmed_epoch: u64,
    /// Total observation windows that matched this hash.
    pub match_count: u64,
}

/// Quantized behavioral invariants — the conserved epitope.
///
/// These values are bucketed into bands so that minor observation-to-
/// observation variation doesn't change the hash. The fleet can't change
/// these without changing their purpose.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BehavioralInvariants {
    /// Whether deep content paths dominate (commit, src, raw, etc.).
    pub deep_content_dominant: bool,
    /// Whether session cookies are absent from the population.
    pub cookieless: bool,
    /// Single-page session ratio band: "high" (>0.8), "medium" (0.4-0.8), "low" (<0.4).
    pub session_depth: String,
    /// UA diversity band: "narrow" (1-5), "moderate" (6-20), "diverse" (21+).
    pub ua_diversity: String,
    /// IP rotation pattern: "rotating" (>0.8 single-use), "sticky" (<0.3), "mixed".
    pub ip_pattern: String,
    /// Primary deception signals active.
    pub deception_flags: Vec<String>,
}

/// Recommended response for opsonized requests.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OpsonizeResponse {
    /// Serve scatter (poison) content at the given ratio.
    Scatter {
        /// Fraction of content to scatter (0.0–1.0).
        ratio: f32,
    },
    /// Abort the connection (zero signal).
    Abort,
    /// Full vanish — connection reset, no trace.
    Vanish,
}

/// Compute a stable behavioral hash from a fleet observation.
///
/// The hash is computed from **quantized** invariant features so that
/// minor variations between observation windows don't change it. This
/// is the conserved epitope — the behavioral constant that persists
/// across IP rotation, UA changes, and timing drift.
///
/// No IPs are included in the hash computation.
#[must_use]
pub fn behavioral_hash(obs: &FleetObservation) -> String {
    use std::hash::{Hash, Hasher};

    // Quantize continuous values into discrete bands
    let commit_band = quantize_pct(obs.path_pattern.commit_url_pct);
    let single_page_band = quantize_pct(obs.path_pattern.single_page_pct);
    let referrer_band = quantize_pct(obs.path_pattern.has_referrer_pct);
    let ua_band = quantize_ua_count(obs.ua_fingerprint.ua_count);
    let top_ua_band = quantize_pct(obs.ua_fingerprint.top_ua_pct);
    let cv_band = quantize_cv(obs.timing.interval_cv);

    // Hash the quantized invariants
    let mut hasher = std::hash::DefaultHasher::new();
    commit_band.hash(&mut hasher);
    single_page_band.hash(&mut hasher);
    referrer_band.hash(&mut hasher);
    ua_band.hash(&mut hasher);
    top_ua_band.hash(&mut hasher);
    cv_band.hash(&mut hasher);
    obs.deception.hides_identity.hash(&mut hasher);
    obs.deception.rotates_ips.hash(&mut hasher);
    obs.deception.ignores_rejection.hash(&mut hasher);
    obs.deception.encoding_uniform.hash(&mut hasher);
    obs.deception.chrome_impersonation.hash(&mut hasher);
    obs.deception.header_poverty.hash(&mut hasher);
    obs.deception.stale_chrome.hash(&mut hasher);
    obs.deception.accept_monoculture.hash(&mut hasher);
    obs.deception.connection_absent.hash(&mut hasher);
    obs.deception.blame_ratio.hash(&mut hasher);
    obs.deception.pagination_walk.hash(&mut hasher);

    format!("{:016x}", hasher.finish())
}

/// Extract behavioral invariants from a fleet observation.
#[must_use]
pub fn extract_invariants(obs: &FleetObservation) -> BehavioralInvariants {
    let mut deception_flags = Vec::new();
    if obs.deception.hides_identity { deception_flags.push("hides_identity".to_string()); }
    if obs.deception.rotates_ips { deception_flags.push("rotates_ips".to_string()); }
    if obs.deception.ignores_rejection { deception_flags.push("ignores_rejection".to_string()); }
    if obs.deception.encoding_uniform { deception_flags.push("encoding_uniform".to_string()); }
    if obs.deception.chrome_impersonation { deception_flags.push("chrome_impersonation".to_string()); }
    if obs.deception.header_poverty { deception_flags.push("header_poverty".to_string()); }
    if obs.deception.stale_chrome { deception_flags.push("stale_chrome".to_string()); }
    if obs.deception.accept_monoculture { deception_flags.push("accept_monoculture".to_string()); }
    if obs.deception.connection_absent { deception_flags.push("connection_absent".to_string()); }
    if obs.deception.blame_ratio { deception_flags.push("blame_ratio".to_string()); }
    if obs.deception.pagination_walk { deception_flags.push("pagination_walk".to_string()); }

    BehavioralInvariants {
        deep_content_dominant: obs.path_pattern.commit_url_pct > 0.5,
        cookieless: obs.path_pattern.has_referrer_pct < 0.1,
        session_depth: if obs.path_pattern.single_page_pct > 0.8 {
            "high".to_string()
        } else if obs.path_pattern.single_page_pct > 0.4 {
            "medium".to_string()
        } else {
            "low".to_string()
        },
        ua_diversity: if obs.ua_fingerprint.ua_count <= 5 {
            "narrow".to_string()
        } else if obs.ua_fingerprint.ua_count <= 20 {
            "moderate".to_string()
        } else {
            "diverse".to_string()
        },
        ip_pattern: if obs.path_pattern.single_page_pct > 0.8 && obs.unique_ips > 10 {
            "rotating".to_string()
        } else if obs.path_pattern.single_page_pct < 0.3 {
            "sticky".to_string()
        } else {
            "mixed".to_string()
        },
        deception_flags,
    }
}

/// Quantize a percentage (0.0-1.0) into 5 bands.
fn quantize_pct(v: f32) -> u8 {
    match v {
        x if x < 0.1 => 0,
        x if x < 0.3 => 1,
        x if x < 0.6 => 2,
        x if x < 0.8 => 3,
        _ => 4,
    }
}

/// Quantize UA count into 3 bands.
fn quantize_ua_count(count: u8) -> u8 {
    match count {
        0..=5 => 0,
        6..=20 => 1,
        _ => 2,
    }
}

/// Quantize coefficient of variation into 3 bands.
fn quantize_cv(cv: f32) -> u8 {
    match cv {
        x if x < 0.3 => 0,  // metronomic
        x if x < 1.0 => 1,  // moderate
        _ => 2,              // organic
    }
}

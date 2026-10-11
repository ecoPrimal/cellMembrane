// SPDX-License-Identifier: AGPL-3.0-or-later

//! Fleet antibody — behavioral fingerprint matching.

use serde::{Deserialize, Serialize};

use super::posture::*;

// ── Fleet Antibody ──────────────────────────────────────────────────

/// A behavioral fingerprint that recognizes a pathogenic fleet pattern.
///
/// The antibody does not store IPs — it stores the **shape** of the
/// fleet's behavior. Same UA distribution + same timing + same path
/// pattern = same fleet, even from entirely new IPs.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FleetAntibody {
    /// Deterministic hash of the pattern components.
    pub id: String,
    /// UA distribution signature across the fleet population.
    pub ua_fingerprint: UaFingerprint,
    /// Timing regularity of requests.
    pub timing: TimingSignature,
    /// Path access pattern.
    pub path_pattern: PathPattern,
    /// What makes this pathogenic, not commensal.
    pub deception: DeceptionSignals,
    /// Detection confidence (0.0–1.0). Decays over time without matches.
    pub confidence: f64,
    /// When this antibody was first created.
    pub first_seen_epoch: u64,
    /// When this antibody last matched a request.
    pub last_matched_epoch: u64,
    /// Total number of times this antibody has matched.
    pub match_count: u64,

    // ── Escalation state (tit-for-tat + forgive-1) ──────────────

    /// Current defense posture for this antibody's behavioral shape.
    #[serde(default)]
    pub escalation: DefensePosture,
    /// When the last defection (matched observation) occurred.
    #[serde(default)]
    pub last_defection_epoch: u64,
    /// Consecutive observation windows with a match (resets on forgive).
    #[serde(default)]
    pub defection_count: u32,
    /// Seconds of silence before de-escalating one level.
    #[serde(default = "default_forgive_window")]
    pub forgive_window_secs: u64,
}

fn default_forgive_window() -> u64 {
    DEFAULT_FORGIVE_WINDOW_SECS
}

/// What distinguishes a pathogen from a commensal.
///
/// A commensal identifies itself honestly. A pathogen hides.
/// These signals are the basis for antibody generation — if none
/// are true, the system is commensal and should be guided, not blocked.
///
/// ## Header Poverty Signal (Wave 165f)
///
/// Real Chrome 145+ sends 11+ headers per request (Sec-Ch-Ua, Sec-Fetch-*,
/// Priority, Accept-Language, etc.). The fleet sends only 3 (Accept,
/// Accept-Encoding, User-Agent). `header_poverty = true` when >80% of
/// a Chrome-UA population is missing mandatory browser headers.
///
/// ## Chrome Impersonation Signal
///
/// `chrome_impersonation = true` when the population claims Chrome UA
/// but is missing Sec-Fetch-Mode and/or Sec-Ch-Ua — headers that Chrome
/// has sent since versions 76 and 89 respectively. This is the definitive
/// proof that the HTTP client is not Chrome.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[allow(clippy::struct_excessive_bools)]
pub struct DeceptionSignals {
    /// Uses human-mimicking UA strings (no bot identifier in UA).
    pub hides_identity: bool,
    /// Population shows many IPs each hitting 1 page (rotating pool).
    pub rotates_ips: bool,
    /// Continues hitting after receiving 403/429 responses.
    pub ignores_rejection: bool,
    /// Entire population has near-identical Accept-Encoding/Language.
    pub encoding_uniform: bool,
    /// Population with Chrome UAs missing mandatory Sec-Fetch-Mode / Sec-Ch-Ua
    /// headers — definitive proof of HTTP client impersonating Chrome.
    #[serde(default)]
    pub chrome_impersonation: bool,
    /// >80% of requests have fewer than 6 distinct header types — the
    /// population is using a bare HTTP library, not a browser.
    #[serde(default)]
    pub header_poverty: bool,
    /// >80% of Chrome-UA population uses a version 5+ behind current
    /// stable. Real Chrome auto-updates — hardcoded UA string.
    #[serde(default)]
    pub stale_chrome: bool,
    /// Entire population uses ≤2 distinct Accept header values (e.g.
    /// universal `*/*`). Real browsers vary Accept per resource type.
    #[serde(default)]
    pub accept_monoculture: bool,
    /// >80% of requests lack a Connection header. Real Chrome always
    /// sends `Connection: keep-alive`. Absence = bare HTTP client.
    #[serde(default)]
    pub connection_absent: bool,
    /// >10% of requests target `/blame/` paths — author attribution
    /// intelligence gathering. Normal browsing has <1% blame access.
    #[serde(default)]
    pub blame_ratio: bool,
    /// Requests include `?page=N` with N > 50 — systematic commit
    /// history enumeration. No human paginates through 50+ pages.
    #[serde(default)]
    pub pagination_walk: bool,
}

/// UA distribution signature across a fleet population.
///
/// Real human traffic has diverse UAs. Fleets use 2-4 UAs split
/// nearly evenly. The fingerprint captures this population shape.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UaFingerprint {
    /// Number of distinct UA strings in the population.
    pub ua_count: u8,
    /// Fraction of requests using the most common UA (0.0–1.0).
    pub top_ua_pct: f32,
    /// Platform distribution: `[mac_pct, windows_pct, linux_pct]`.
    pub platform_split: [f32; 3],
}

/// Timing regularity of fleet requests.
///
/// Human browsing has high variance in inter-arrival times.
/// Fleets have metronomic regularity (low coefficient of variation).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimingSignature {
    /// Mean interval between requests in milliseconds.
    pub mean_interval_ms: u32,
    /// Coefficient of variation of inter-arrival times.
    /// < 0.3 is suspiciously regular (metronomic).
    pub interval_cv: f32,
}

/// Path access pattern of a fleet.
///
/// Fleets systematically walk commit-level URLs. Humans browse
/// current-branch content with referrers from navigation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathPattern {
    /// Fraction of requests targeting commit-hash URLs (0.0–1.0).
    pub commit_url_pct: f32,
    /// Fraction of sessions that visit exactly one page (0.0–1.0).
    pub single_page_pct: f32,
    /// Fraction of requests carrying a Referer header (0.0–1.0).
    pub has_referrer_pct: f32,
}

// ── Fleet Observation ───────────────────────────────────────────────

/// Population-level fleet observation emitted by skunky-ingest.
///
/// Unlike `Observation` (per-IP), this captures the statistical
/// properties of the entire traffic population in a time window.
/// The `FleetDetector` in skunkBat uses these to create antibodies.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FleetObservation {
    /// Timestamp of the observation window end.
    pub timestamp_epoch: u64,
    /// Total requests in the window (across all IPs).
    pub total_requests: u64,
    /// Number of unique source IPs.
    pub unique_ips: u32,
    /// UA distribution across all requests.
    pub ua_fingerprint: UaFingerprint,
    /// Timing regularity across the population.
    pub timing: TimingSignature,
    /// Path access pattern across all requests.
    pub path_pattern: PathPattern,
    /// Deception signals observed in the population.
    pub deception: DeceptionSignals,
    /// Per-IP request count distribution: `[1-page, 2-3, 4-10, 11+]`.
    pub depth_distribution: [u32; 4],
    /// Number of IPs that received only 403/429 responses.
    pub rejected_ips: u32,
}

impl FleetAntibody {
    /// Check whether this antibody matches a fleet observation.
    ///
    /// Matching is fuzzy — the observation's fingerprint must be
    /// "close enough" to the antibody's stored pattern. Each dimension
    /// contributes a similarity score; the overall match requires
    /// all dimensions above threshold.
    #[must_use]
    pub fn matches_observation(&self, obs: &FleetObservation) -> bool {
        if self.confidence < 0.1 {
            return false;
        }

        let ua_match = ua_similarity(&self.ua_fingerprint, &obs.ua_fingerprint) > 0.6;
        let timing_match = timing_similarity(&self.timing, &obs.timing) > 0.5;
        let path_match = path_similarity(&self.path_pattern, &obs.path_pattern) > 0.6;
        let deception_match = deception_overlap(&self.deception, &obs.deception) >= 2;

        ua_match && path_match && (timing_match || deception_match)
    }

    /// Apply confidence decay. Call periodically (e.g. daily).
    /// Antibodies that haven't matched recently lose confidence
    /// and eventually become inert.
    pub fn decay(&mut self, decay_factor: f64) {
        self.confidence *= decay_factor;
    }

    /// Tick the escalation state machine.
    ///
    /// Call once per observation window with `matched = true` if this
    /// antibody matched any observation in the window, `false` otherwise.
    ///
    /// Returns the previous posture if it changed (for audit logging).
    pub fn tick_escalation(&mut self, matched: bool, now_epoch: u64) -> Option<DefensePosture> {
        let prev = self.escalation;

        if matched {
            self.last_defection_epoch = now_epoch;
            self.defection_count = self.defection_count.saturating_add(1);

            let new = match self.escalation {
                DefensePosture::Observe => DefensePosture::WarnRoute,
                DefensePosture::WarnRoute => {
                    if self.deception.ignores_rejection
                        || self.defection_count >= ESCALATE_TO_SLOW
                    {
                        DefensePosture::SlowDegrade
                    } else {
                        DefensePosture::WarnRoute
                    }
                }
                DefensePosture::SlowDegrade => {
                    if self.defection_count >= ESCALATE_TO_SCATTER {
                        DefensePosture::Scatter
                    } else {
                        DefensePosture::SlowDegrade
                    }
                }
                DefensePosture::Scatter => {
                    if self.defection_count >= ESCALATE_TO_VANISH {
                        DefensePosture::Vanish
                    } else {
                        DefensePosture::Scatter
                    }
                }
                DefensePosture::Vanish => {
                    if self.defection_count >= ESCALATE_TO_DISPERSE {
                        DefensePosture::Disperse
                    } else {
                        DefensePosture::Vanish
                    }
                }
                DefensePosture::Disperse => DefensePosture::Disperse,
            };

            self.escalation = new;
        } else {
            // Forgive-1: de-escalate if silent for forgive_window
            let silence = now_epoch.saturating_sub(self.last_defection_epoch);
            if silence >= self.forgive_window_secs && self.escalation != DefensePosture::Observe {
                self.escalation = self.escalation.deescalate();
                self.defection_count = 0;
                // Reset the timer so next forgive needs another full window
                self.last_defection_epoch = now_epoch;
            }
        }

        if self.escalation != prev {
            Some(prev)
        } else {
            None
        }
    }
}

/// Cosine-like similarity between two UA fingerprints.
fn ua_similarity(a: &UaFingerprint, b: &UaFingerprint) -> f32 {
    let count_sim = 1.0 - (f32::from(a.ua_count).max(1.0) - f32::from(b.ua_count).max(1.0)).abs()
        / f32::from(a.ua_count).max(f32::from(b.ua_count)).max(1.0);
    let pct_sim = 1.0 - (a.top_ua_pct - b.top_ua_pct).abs();
    let platform_sim: f32 = a
        .platform_split
        .iter()
        .zip(b.platform_split.iter())
        .map(|(pa, pb)| 1.0 - (pa - pb).abs())
        .sum::<f32>()
        / 3.0;
    (count_sim + pct_sim + platform_sim) / 3.0
}

/// Similarity between timing signatures.
fn timing_similarity(a: &TimingSignature, b: &TimingSignature) -> f32 {
    let interval_sim = 1.0
        - (a.mean_interval_ms as f32 - b.mean_interval_ms as f32).abs()
            / a.mean_interval_ms.max(b.mean_interval_ms).max(1) as f32;
    let cv_sim = 1.0 - (a.interval_cv - b.interval_cv).abs();
    (interval_sim + cv_sim) / 2.0
}

/// Similarity between path patterns.
fn path_similarity(a: &PathPattern, b: &PathPattern) -> f32 {
    let commit_sim = 1.0 - (a.commit_url_pct - b.commit_url_pct).abs();
    let single_sim = 1.0 - (a.single_page_pct - b.single_page_pct).abs();
    let ref_sim = 1.0 - (a.has_referrer_pct - b.has_referrer_pct).abs();
    (commit_sim + single_sim + ref_sim) / 3.0
}

/// Count of overlapping deception signals.
fn deception_overlap(a: &DeceptionSignals, b: &DeceptionSignals) -> u8 {
    let mut overlap = 0u8;
    if a.hides_identity && b.hides_identity {
        overlap += 1;
    }
    if a.rotates_ips && b.rotates_ips {
        overlap += 1;
    }
    if a.ignores_rejection && b.ignores_rejection {
        overlap += 1;
    }
    if a.encoding_uniform && b.encoding_uniform {
        overlap += 1;
    }
    if a.chrome_impersonation && b.chrome_impersonation {
        overlap += 1;
    }
    if a.header_poverty && b.header_poverty {
        overlap += 1;
    }
    if a.stale_chrome && b.stale_chrome {
        overlap += 1;
    }
    if a.accept_monoculture && b.accept_monoculture {
        overlap += 1;
    }
    if a.connection_absent && b.connection_absent {
        overlap += 1;
    }
    if a.blame_ratio && b.blame_ratio {
        overlap += 1;
    }
    if a.pagination_walk && b.pagination_walk {
        overlap += 1;
    }
    overlap
}


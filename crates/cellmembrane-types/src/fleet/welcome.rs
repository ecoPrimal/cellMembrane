// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2025-2026 ecoPrimal <ecoPrimal@pm.me>

//! Welcome posture — the Klein bottle's positive side.
//!
//! Defense posture escalates with defection: observe → warn → scatter → vanish.
//! Welcome posture escalates with **cooperation**: observe → notice → learn → incorporate.
//!
//! The Klein bottle: the outside surface (non-self behavior) teaches
//! the inside surface (self knowledge). A commensal that reads our
//! papers IS our peer review. A mutualist that links back IS our
//! immune memory. The boundary between self and non-self is topological,
//! not binary.
//!
//! # What commensals teach us
//!
//! 5,049 dev_readers walk through the membrane every day. They choose
//! which pages to read, how long to dwell, what to come back to.
//! That behavioral data is a **free focus group**. We tag them and
//! stop there. The learning loop was missing.
//!
//! # Positive opsonization
//!
//! In immunology, opsonization marks pathogens for destruction.
//! But the immune system also has **positive selection** — in the thymus,
//! T-cells that recognize self-MHC are SELECTED FOR, not destroyed.
//! Commensals that recognize our content honestly are positively selected.
//! Their behavior teaches us what's valuable.
//!
//! # The Klein bottle closes here
//!
//! ```text
//!   non-self reads content
//!     → content learning: what they cluster on = what matters
//!       → membrane adjusts what it serves / emphasizes
//!         → non-self reads different content (path changes)
//!           → content learning cycles (Klein bottle: outside teaches inside)
//! ```
//!
//! This is the missing half. Antibodies are the immune response.
//! Welcome posture is the immune *education*.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

// ── Welcome Posture ─────────────────────────────────────────────────

/// Positive counterpart to `DefensePosture`.
///
/// Escalates with cooperation, not defection. The membrane doesn't
/// just block threats — it LEARNS from friends.
///
/// ```text
///   Observe    → entity is new, we're watching
///   Notice     → entity shows cooperative signals (honest ID, reading pauses)
///   Learn      → entity's behavior teaches us something (which content matters)
///   Incorporate → entity is part of the membrane's knowledge (their patterns feed our model)
///   Mutualize  → entity benefits us AND we benefit them (links, attribution, ecosystem)
///   Entangle   → entity is braided into the membrane — their self and our self overlap
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WelcomePosture {
    /// W0: New entity, not enough signal. Same as defense Observe.
    Observe,
    /// W1: Cooperative signals detected. Honest identification, reading pauses.
    /// The membrane notices them — they're not noise.
    Notice,
    /// W2: Their behavior teaches us. Which pages they read, how long they dwell,
    /// what they come back to. This is free peer review / focus group data.
    Learn,
    /// W3: Their behavioral patterns are incorporated into the membrane's model.
    /// What commensals cluster on = what matters. Their reading IS our quality signal.
    Incorporate,
    /// W4: Mutual benefit established. They get content, we get signal.
    /// Attribution, links, ecosystem effects flow both ways.
    Mutualize,
    /// W5: Entangled — their self and our self overlap. Not visitors anymore.
    /// Think: the gut microbiome isn't "non-self" — it's part of you.
    Entangle,
}

impl WelcomePosture {
    /// Welcome one level (capped at Entangle).
    #[must_use]
    pub const fn welcome(self) -> Self {
        match self {
            Self::Observe => Self::Notice,
            Self::Notice => Self::Learn,
            Self::Learn => Self::Incorporate,
            Self::Incorporate => Self::Mutualize,
            Self::Mutualize => Self::Entangle,
            Self::Entangle => Self::Entangle,
        }
    }

    /// Cool one level on inactivity (capped at Observe).
    #[must_use]
    pub const fn cool(self) -> Self {
        match self {
            Self::Observe => Self::Observe,
            Self::Notice => Self::Observe,
            Self::Learn => Self::Notice,
            Self::Incorporate => Self::Learn,
            Self::Mutualize => Self::Incorporate,
            Self::Entangle => Self::Mutualize,
        }
    }

    /// Numeric level (0–5) for threshold comparisons.
    #[must_use]
    pub const fn level(self) -> u8 {
        match self {
            Self::Observe => 0,
            Self::Notice => 1,
            Self::Learn => 2,
            Self::Incorporate => 3,
            Self::Mutualize => 4,
            Self::Entangle => 5,
        }
    }

    /// Human-readable description.
    pub fn description(&self) -> &'static str {
        match self {
            Self::Observe => "observing — not enough signal yet",
            Self::Notice => "noticed — cooperative signals detected",
            Self::Learn => "learning — their behavior teaches us what matters",
            Self::Incorporate => "incorporated — their patterns feed our model",
            Self::Mutualize => "mutualist — both benefit, ecosystem effects flow",
            Self::Entangle => "entangled — their self and our self overlap",
        }
    }
}

impl Default for WelcomePosture {
    fn default() -> Self {
        Self::Observe
    }
}

// ── Content Learning ────────────────────────────────────────────────

/// What a commensal/mutualist teaches the membrane by reading.
///
/// This is the Klein bottle's data: non-self behavior → self knowledge.
/// Every honest reader is a free focus group participant.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContentLearning {
    /// Which pages they clustered on (path → visit count).
    pub page_heat: BTreeMap<String, u64>,
    /// Which hosts they visited (host → visit count).
    pub host_heat: BTreeMap<String, u64>,
    /// Average dwell time in seconds (0 = vacuum, high = reading).
    pub avg_dwell_secs: f64,
    /// How many times they returned (0 = one-shot, high = engaged).
    pub return_visits: u64,
    /// What content type they wanted (source, papers, legal, etc).
    pub content_appetite: Vec<String>,
    /// The signal: what's valuable to non-self = what we should amplify.
    pub value_signal: f64,
}

/// Aggregated learning across all commensals — the membrane's focus group.
///
/// This is the output of positive opsonization: not "what to block"
/// but "what to amplify". The Klein bottle closes when this data
/// feeds back into content serving decisions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregateLearning {
    /// When this snapshot was generated.
    pub generated: String,
    /// Total commensals that contributed to this learning.
    pub contributors: u64,
    /// Pages ranked by aggregate heat (most visited by commensals).
    pub hot_pages: Vec<PageHeat>,
    /// Hosts ranked by aggregate traffic.
    pub hot_hosts: Vec<HostHeat>,
    /// Content types ranked by appetite.
    pub appetite_ranking: Vec<AppetiteRank>,
    /// The Klein bottle signal: what non-self values, self should amplify.
    pub amplification_signal: Vec<AmplificationSignal>,
}

/// A single page's heat score from commensal reading behavior.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PageHeat {
    /// The page path.
    pub path: String,
    /// Total visits from commensals.
    pub visits: u64,
    /// Average dwell time on this page.
    pub avg_dwell_secs: f64,
    /// Number of unique commensals that visited.
    pub unique_visitors: u64,
    /// Heat score: visits × dwell × uniqueness.
    pub heat: f64,
}

/// A host's aggregate traffic from commensals.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HostHeat {
    /// The hostname.
    pub host: String,
    /// Total visits.
    pub visits: u64,
    /// Unique commensal visitors.
    pub unique_visitors: u64,
}

/// Content appetite ranking.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppetiteRank {
    /// Content type (source_diffs, scientific_papers, legal_documents, etc).
    pub content_type: String,
    /// How many commensals wanted this.
    pub demand: u64,
    /// Fraction of all commensal appetite.
    pub fraction: f64,
}

/// The Klein bottle output: what to amplify based on non-self behavior.
///
/// This is the positive opsonization result — not "destroy this"
/// but "make more of this". The membrane learns what matters
/// by watching what honest visitors read.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AmplificationSignal {
    /// What to amplify (a path, a content type, a host).
    pub target: String,
    /// Signal strength (0.0–1.0). Higher = more non-self interest.
    pub strength: f64,
    /// Where the signal came from (commensal reading, mutualist linking, etc).
    pub source: String,
    /// How this should feed back: "serve_more", "link_prominently", "campfire_story".
    pub feedback_action: String,
}

// ── Positive Opsonization Tag ───────────────────────────────────────

/// The positive counterpart to `OpsonizeTag`.
///
/// Where OpsonizeTag says "this behavioral shape is pathogenic, apply friction",
/// WelcomeTag says "this behavioral shape is cooperative, apply welcome".
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WelcomeTag {
    /// Behavioral hash of the cooperative pattern.
    pub behavioral_hash: String,
    /// What made this pattern cooperative (honest_id, reading_pauses, diverse_paths...).
    pub cooperation_signals: Vec<String>,
    /// Current welcome level.
    pub posture: WelcomePosture,
    /// What this entity's behavior teaches us.
    pub learning: ContentLearning,
    /// When first welcomed.
    pub first_welcomed_epoch: u64,
    /// When last seen cooperating.
    pub last_cooperation_epoch: u64,
    /// Total cooperation observations.
    pub cooperation_count: u64,
}

impl WelcomeTag {
    /// Tick the welcome state machine. Call with `cooperated = true`
    /// when entity shows cooperative behavior in the observation window.
    ///
    /// Returns the previous posture if it changed.
    pub fn tick(&mut self, cooperated: bool, now_epoch: u64) -> Option<WelcomePosture> {
        let prev = self.posture;

        if cooperated {
            self.last_cooperation_epoch = now_epoch;
            self.cooperation_count += 1;

            // Escalate welcome based on sustained cooperation
            let new = match self.posture {
                WelcomePosture::Observe => {
                    if self.cooperation_count >= 1 {
                        WelcomePosture::Notice
                    } else {
                        WelcomePosture::Observe
                    }
                }
                WelcomePosture::Notice => {
                    if self.cooperation_count >= 3 {
                        WelcomePosture::Learn
                    } else {
                        WelcomePosture::Notice
                    }
                }
                WelcomePosture::Learn => {
                    if self.cooperation_count >= 10 && !self.learning.page_heat.is_empty() {
                        WelcomePosture::Incorporate
                    } else {
                        WelcomePosture::Learn
                    }
                }
                WelcomePosture::Incorporate => {
                    if self.cooperation_count >= 30 && self.learning.return_visits >= 3 {
                        WelcomePosture::Mutualize
                    } else {
                        WelcomePosture::Incorporate
                    }
                }
                WelcomePosture::Mutualize => {
                    if self.cooperation_count >= 100 {
                        WelcomePosture::Entangle
                    } else {
                        WelcomePosture::Mutualize
                    }
                }
                WelcomePosture::Entangle => WelcomePosture::Entangle,
            };

            self.posture = new;
        } else {
            // Cool on inactivity (longer window than defense de-escalation)
            let silence = now_epoch.saturating_sub(self.last_cooperation_epoch);
            let cool_window = 86400 * 7; // 7 days of silence before cooling
            if silence >= cool_window && self.posture != WelcomePosture::Observe {
                self.posture = self.posture.cool();
            }
        }

        if self.posture != prev {
            Some(prev)
        } else {
            None
        }
    }
}

// ── Tests ───────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn welcome_escalation_ladder() {
        assert_eq!(WelcomePosture::Observe.welcome(), WelcomePosture::Notice);
        assert_eq!(WelcomePosture::Notice.welcome(), WelcomePosture::Learn);
        assert_eq!(WelcomePosture::Learn.welcome(), WelcomePosture::Incorporate);
        assert_eq!(WelcomePosture::Incorporate.welcome(), WelcomePosture::Mutualize);
        assert_eq!(WelcomePosture::Mutualize.welcome(), WelcomePosture::Entangle);
        assert_eq!(WelcomePosture::Entangle.welcome(), WelcomePosture::Entangle);
    }

    #[test]
    fn welcome_cooling_ladder() {
        assert_eq!(WelcomePosture::Entangle.cool(), WelcomePosture::Mutualize);
        assert_eq!(WelcomePosture::Mutualize.cool(), WelcomePosture::Incorporate);
        assert_eq!(WelcomePosture::Incorporate.cool(), WelcomePosture::Learn);
        assert_eq!(WelcomePosture::Learn.cool(), WelcomePosture::Notice);
        assert_eq!(WelcomePosture::Notice.cool(), WelcomePosture::Observe);
        assert_eq!(WelcomePosture::Observe.cool(), WelcomePosture::Observe);
    }

    #[test]
    fn level_ordering() {
        assert!(WelcomePosture::Observe < WelcomePosture::Notice);
        assert!(WelcomePosture::Notice < WelcomePosture::Learn);
        assert!(WelcomePosture::Learn < WelcomePosture::Incorporate);
        assert!(WelcomePosture::Incorporate < WelcomePosture::Mutualize);
        assert!(WelcomePosture::Mutualize < WelcomePosture::Entangle);
    }

    #[test]
    fn default_is_observe() {
        assert_eq!(WelcomePosture::default(), WelcomePosture::Observe);
    }

    #[test]
    fn levels_monotonic() {
        let postures = [
            WelcomePosture::Observe,
            WelcomePosture::Notice,
            WelcomePosture::Learn,
            WelcomePosture::Incorporate,
            WelcomePosture::Mutualize,
            WelcomePosture::Entangle,
        ];
        for i in 0..postures.len() - 1 {
            assert!(
                postures[i].level() < postures[i + 1].level(),
                "{:?} level ({}) should be < {:?} level ({})",
                postures[i], postures[i].level(), postures[i + 1], postures[i + 1].level(),
            );
        }
    }

    #[test]
    fn tick_welcome_from_observe() {
        let mut tag = WelcomeTag {
            behavioral_hash: "test".into(),
            cooperation_signals: vec!["honest_id".into()],
            posture: WelcomePosture::Observe,
            learning: ContentLearning {
                page_heat: BTreeMap::new(),
                host_heat: BTreeMap::new(),
                avg_dwell_secs: 0.0,
                return_visits: 0,
                content_appetite: vec![],
                value_signal: 0.0,
            },
            first_welcomed_epoch: 1000,
            last_cooperation_epoch: 1000,
            cooperation_count: 0,
        };

        let prev = tag.tick(true, 2000);
        assert_eq!(prev, Some(WelcomePosture::Observe));
        assert_eq!(tag.posture, WelcomePosture::Notice);
    }

    #[test]
    fn tick_cool_on_silence() {
        let mut tag = WelcomeTag {
            behavioral_hash: "test".into(),
            cooperation_signals: vec![],
            posture: WelcomePosture::Learn,
            learning: ContentLearning {
                page_heat: BTreeMap::new(),
                host_heat: BTreeMap::new(),
                avg_dwell_secs: 0.0,
                return_visits: 0,
                content_appetite: vec![],
                value_signal: 0.0,
            },
            first_welcomed_epoch: 1000,
            last_cooperation_epoch: 1000,
            cooperation_count: 5,
        };

        // 7 days of silence
        let prev = tag.tick(false, 1000 + 86400 * 7);
        assert_eq!(prev, Some(WelcomePosture::Learn));
        assert_eq!(tag.posture, WelcomePosture::Notice);
    }
}

// SPDX-License-Identifier: AGPL-3.0-or-later

//! Defense posture — tit-for-tat escalation.

use serde::{Deserialize, Serialize};

// ── Defense Posture ─────────────────────────────────────────────────

/// Tit-for-tat escalation posture for fleet defense.
///
/// Ordered from least to most aggressive. The immune system starts at
/// `Observe` and escalates on repeat defection (same behavioral shape
/// returning after rejection). De-escalates one level per `forgive_window`
/// of silence.
///
/// The ordering is significant: `PartialOrd`/`Ord` derive means
/// `Observe < WarnRoute < SlowDegrade < Scatter < Vanish < Disperse`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DefensePosture {
    /// P0: Normal traffic, antibodies watch but do not intervene.
    Observe,
    /// P1: 403 + warning page + redirect to external membrane (GitHub).
    WarnRoute,
    /// P2: Tarpit — artificial delays, partial content, randomized timing.
    /// Wastes attacker compute without revealing they are detected.
    SlowDegrade,
    /// P3: Plausible-but-wrong content. Poisons training data.
    /// Anti-AI defense: the shape looks correct, the content is garbage.
    Scatter,
    /// P4: Connection reset / abort. The membrane vanishes.
    /// Real humans still see everything — only antibody-matched shapes disappear.
    Vanish,
    /// P5: Active confusion — skunk spray. Maximally-wrong responses that
    /// waste attacker compute and poison any downstream processing.
    /// Wrong MIME types, garbled structure, fake auth flows, random redirects.
    /// Friendly systems (WireGuard, authenticated) bypass via recognition.
    Disperse,
}

impl DefensePosture {
    /// Escalate one level (capped at Disperse).
    #[must_use]
    pub const fn escalate(self) -> Self {
        match self {
            Self::Observe => Self::WarnRoute,
            Self::WarnRoute => Self::SlowDegrade,
            Self::SlowDegrade => Self::Scatter,
            Self::Scatter => Self::Vanish,
            Self::Vanish => Self::Disperse,
            Self::Disperse => Self::Disperse,
        }
    }

    /// De-escalate one level (capped at Observe).
    #[must_use]
    pub const fn deescalate(self) -> Self {
        match self {
            Self::Observe => Self::Observe,
            Self::WarnRoute => Self::Observe,
            Self::SlowDegrade => Self::WarnRoute,
            Self::Scatter => Self::SlowDegrade,
            Self::Vanish => Self::Scatter,
            Self::Disperse => Self::Vanish,
        }
    }

    /// Numeric level (0-5) for threshold comparisons.
    #[must_use]
    pub const fn level(self) -> u8 {
        match self {
            Self::Observe => 0,
            Self::WarnRoute => 1,
            Self::SlowDegrade => 2,
            Self::Scatter => 3,
            Self::Vanish => 4,
            Self::Disperse => 5,
        }
    }
}

impl Default for DefensePosture {
    fn default() -> Self {
        Self::Observe
    }
}

/// Trust descriptor for bearDog ecosystem mapping.
///
/// Provides the semantic bridge between defense postures and the bearDog
/// trust spectrum. bearDog's ecosystem evolution engine consumes these
/// values to construct its own `EcosystemMembership` variants.
#[derive(Debug, Clone, PartialEq)]
pub struct TrustDescriptor {
    /// Trust level on bearDog's 0.0–1.0 spectrum.
    pub trust_level: f64,
    /// Which `EcosystemMembership` variant this maps to.
    pub membership_hint: &'static str,
    /// Which `SymbiosisType` this implies.
    pub symbiosis_hint: &'static str,
    /// Whether healing/restoration is available.
    pub restoration_available: bool,
}

impl DefensePosture {
    /// Map this posture to a bearDog trust descriptor.
    ///
    /// The descriptor tells bearDog's ecosystem evolution engine what
    /// trust level and membership category to assign to traffic matching
    /// this posture's antibody.
    ///
    /// # Mapping
    ///
    /// | Posture      | Trust  | Membership              | Symbiosis     |
    /// |--------------|--------|-------------------------|---------------|
    /// | Observe      | 0.7    | `ActiveContributor`     | Commensal     |
    /// | WarnRoute    | 0.45   | `CautiousInteraction`   | Commensal     |
    /// | SlowDegrade  | 0.25   | `CautiousInteraction`   | Competitive   |
    /// | Scatter      | 0.10   | `EcosystemProtection`   | Protective    |
    /// | Vanish       | 0.0    | `EcosystemProtection`   | Protective    |
    #[must_use]
    pub const fn trust_descriptor(&self) -> TrustDescriptor {
        match self {
            Self::Observe => TrustDescriptor {
                trust_level: 0.7,
                membership_hint: "ActiveContributor",
                symbiosis_hint: "Commensal",
                restoration_available: true,
            },
            Self::WarnRoute => TrustDescriptor {
                trust_level: 0.45,
                membership_hint: "CautiousInteraction",
                symbiosis_hint: "Commensal",
                restoration_available: true,
            },
            Self::SlowDegrade => TrustDescriptor {
                trust_level: 0.25,
                membership_hint: "CautiousInteraction",
                symbiosis_hint: "Competitive",
                restoration_available: true,
            },
            Self::Scatter => TrustDescriptor {
                trust_level: 0.10,
                membership_hint: "EcosystemProtection",
                symbiosis_hint: "Protective",
                restoration_available: true,
            },
            Self::Vanish => TrustDescriptor {
                trust_level: 0.0,
                membership_hint: "EcosystemProtection",
                symbiosis_hint: "Protective",
                restoration_available: false,
            },
            Self::Disperse => TrustDescriptor {
                trust_level: 0.0,
                membership_hint: "EcosystemProtection",
                symbiosis_hint: "ActiveDefense",
                restoration_available: false,
            },
        }
    }
}

impl std::fmt::Display for DefensePosture {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Observe => write!(f, "observe"),
            Self::WarnRoute => write!(f, "warn_route"),
            Self::SlowDegrade => write!(f, "slow_degrade"),
            Self::Scatter => write!(f, "scatter"),
            Self::Vanish => write!(f, "vanish"),
            Self::Disperse => write!(f, "disperse"),
        }
    }
}

/// Default forgive window: 4 hours (14400 seconds).
pub const DEFAULT_FORGIVE_WINDOW_SECS: u64 = 14_400;

/// Escalation thresholds: consecutive defection windows to trigger each level.
pub const ESCALATE_TO_SLOW: u32 = 1;    // P1→P2: came back after 403
/// Consecutive defection windows to escalate from P2 to P3.
pub const ESCALATE_TO_SCATTER: u32 = 3; // P2→P3: persists despite tarpit
/// Consecutive defection windows to escalate from P3 to P4.
pub const ESCALATE_TO_VANISH: u32 = 6;  // P3→P4: persists despite scatter
/// Cumulative defection count to escalate from P4 to P5 (skunk spray).
/// With ignores_rejection=true, reaching Vanish takes ~11 defections,
/// so 20 means ~9 more windows of persistence at Vanish before Disperse.
pub const ESCALATE_TO_DISPERSE: u32 = 20; // P4→P5: persists despite vanish


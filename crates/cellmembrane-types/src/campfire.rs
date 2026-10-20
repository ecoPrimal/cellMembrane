// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2025-2026 ecoPrimal <ecoPrimal@pm.me>

//! Campfire types — the storytelling IS the epitope sort (Wave 173).
//!
//! Two layers of classification, both derived from the same traffic signal:
//!
//! - **[`VisitorClass`]** (in [`crate::visitor`]) answers WHAT: human, bot, fleet.
//! - **[`VisitorArchetype`]** answers HOW: explorer, watcher, scholar, scout.
//!
//! `VisitorClass` is the immune sort — friend or foe. `VisitorArchetype` is
//! the campfire sort — what shape does this friend cast in the firelight?
//!
//! Also defines the four membrane primitives (Paper 62 §4):
//! [`MembraneOp`] — IN, OUT, NEXT-TO, REQUIRE.
//!
//! # Privacy
//!
//! No IP addresses, no cookies, no sessions. Shape only.
//! The membrane knows your shape but not your name.

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

// ── Visitor Archetype ───────────────────────────────────────────────

/// Behavioral archetype — the shape of the visit, not the entity type.
///
/// `VisitorClass` (visitor.rs) asks "WHAT are you?" — human, bot, fleet.
/// `VisitorArchetype` asks "HOW do you move?" — explorer, watcher, teacher.
///
/// Both are epitope sorts. One sorts friend from foe. The other sorts
/// friend from friend — because not all friends come for the same reason.
///
/// Derived from surface coverage, polling frequency, navigation depth,
/// visit duration, and content domain affinity. See Paper 62 §2 (the Y
/// intersection) for the theoretical framework.
///
/// # Examples
///
/// ```
/// use cellmembrane_types::campfire::VisitorArchetype;
///
/// let arch = VisitorArchetype::Explorer;
/// assert_eq!(arch.description(), "Walks the full membrane. Studies the architecture.");
/// assert!(!arch.is_passive());
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum VisitorArchetype {
    /// Wide surface coverage, systematic exploration, high d_eff.
    /// Walks the immune honeycomb, maps corridors, touches many surfaces.
    Explorer,
    /// Low surface count, high poll frequency. Watches the dashboard/billboard.
    /// Patient. Present. Sees every change.
    Watcher,
    /// Reads source code, git commits, issue trackers. Understands by reading.
    Scholar,
    /// Quick perimeter check, short duration, multiple surfaces.
    /// Maps the shape and moves on. May return.
    Scout,
    /// Goes straight to evidence, reads purposefully. Here for the record.
    Witness,
    /// Reads papers, methodology, science. Connects evidence to framework.
    /// Understands the why, not just the what.
    Teacher,
    /// Brief touch. A few pages, a few seconds. Testing the surface.
    /// The membrane noticed.
    Probe,
    /// Came, looked, left a braid. The genome remembers.
    Visitor,
}

impl VisitorArchetype {
    /// Human-readable description of this archetype.
    #[must_use]
    pub const fn description(self) -> &'static str {
        match self {
            Self::Explorer => "Walks the full membrane. Studies the architecture.",
            Self::Watcher => "Watches the organism breathe. Patient. Present.",
            Self::Scholar => "Reads the source. Understands by reading what was built.",
            Self::Scout => "Quick perimeter check. Maps the shape. May return.",
            Self::Witness => "Reads the evidence. Here for the record.",
            Self::Teacher => "Reads the papers. Connects evidence to science.",
            Self::Probe => "Brief touch. Testing the surface. The membrane noticed.",
            Self::Visitor => "Came, looked, left a braid. The genome remembers.",
        }
    }

    /// Whether this archetype is primarily passive (watching/polling vs exploring).
    #[must_use]
    pub const fn is_passive(self) -> bool {
        matches!(self, Self::Watcher | Self::Probe | Self::Visitor)
    }

    /// Campfire icon for rendering.
    #[must_use]
    pub const fn icon(self) -> &'static str {
        match self {
            Self::Explorer => "\u{1f9ed}", // 🧭
            Self::Watcher => "\u{1f441}",  // 👁
            Self::Scholar => "\u{1f4da}",  // 📚
            Self::Scout => "\u{26a1}",     // ⚡
            Self::Witness => "\u{2696}",   // ⚖
            Self::Teacher => "\u{1f52c}",  // 🔬
            Self::Probe => "\u{1f4a0}",    // 💠
            Self::Visitor => "\u{1f30a}",  // 🌊
        }
    }
}

impl std::fmt::Display for VisitorArchetype {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Explorer => write!(f, "explorer"),
            Self::Watcher => write!(f, "watcher"),
            Self::Scholar => write!(f, "scholar"),
            Self::Scout => write!(f, "scout"),
            Self::Witness => write!(f, "witness"),
            Self::Teacher => write!(f, "teacher"),
            Self::Probe => write!(f, "probe"),
            Self::Visitor => write!(f, "visitor"),
        }
    }
}

// ── Membrane Operations ─────────────────────────────────────────────

/// The four primitive membrane operations (Paper 62 §4, §8).
///
/// Every selective boundary — biological, digital, social — decomposes
/// into these four primitives. They are to membranes what +, -, ×, ÷
/// are to arithmetic: the irreducible basis set.
///
/// The campfire demonstrates all four in their most ancient form:
/// - **In**: sit down, face the fire, enter the circle of light.
/// - **Out**: stand up, turn away, walk into the darkness.
/// - **NextTo**: who is on your left, who is on your right.
/// - **Require**: participation — the fire rewards those who feed it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MembraneOp {
    /// Entity crosses boundary → interior (approach, consent, warmth).
    In,
    /// Entity crosses boundary → exterior (withdrawal, departure, cold).
    Out,
    /// Entity relates to adjacent entity (companionship, topology).
    NextTo,
    /// Boundary demands condition from entity (a story, a key, a shape).
    Require,
}

impl std::fmt::Display for MembraneOp {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::In => write!(f, "in"),
            Self::Out => write!(f, "out"),
            Self::NextTo => write!(f, "next_to"),
            Self::Require => write!(f, "require"),
        }
    }
}

// ── Mirror Message ──────────────────────────────────────────────────

/// Anonymous words left at the campfire mirror.
///
/// No IP stored. No name. No session. No cookies.
/// Just words, a timestamp, and the shape they make.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MirrorMessage {
    /// UTC timestamp of when the words were left.
    pub ts: String,
    /// The words themselves — raw text, max 2000 chars.
    pub words: String,
    /// Word count (pre-computed for rendering).
    pub word_count: usize,
}

impl MirrorMessage {
    /// Create a new mirror message from raw text.
    ///
    /// Trims whitespace and truncates to 2000 characters.
    #[must_use]
    pub fn new(words: &str) -> Self {
        let trimmed = words.trim();
        let truncated = if trimmed.len() > 2000 {
            &trimmed[..2000]
        } else {
            trimmed
        };
        let word_count = truncated.split_whitespace().count();
        Self {
            ts: String::new(), // set by caller
            words: truncated.to_string(),
            word_count,
        }
    }

    /// Whether the message is empty or too short to be meaningful.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.words.len() < 2
    }
}

// ── Page Mirror ─────────────────────────────────────────────────────

/// Surface self-awareness — what each surface knows about itself.
///
/// The other side of the braid: not "what did visitors do" but
/// "what does the knowledge know about itself." Each surface is its
/// own epitope on the OTHER membrane.
///
/// The value of knowledge is a matter of perspective.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurfaceMirror {
    /// Surface hostname (e.g. "git", "detroit", "cytokine").
    pub surface: String,
    /// Human-readable name.
    pub name: String,
    /// Total hits from human visitors.
    pub hits: u64,
    /// Number of distinct visitor shapes.
    pub visitor_count: usize,
    /// Number of distinct pages touched.
    pub unique_pages: usize,
    /// Which archetypes this surface attracts and in what proportion.
    pub archetype_attraction: BTreeMap<String, usize>,
    /// Shape of the surface's knowledge topology.
    pub shape: SurfaceShape,
    /// When this surface is most active.
    pub temporal_character: TemporalCharacter,
    /// Content domain this surface belongs to.
    pub domain: ContentDomain,
}

/// Shape of a surface's knowledge topology — breadth vs depth.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SurfaceShape {
    /// Many pages, high avg depth.
    DeepAndWide,
    /// Many pages, low avg depth.
    WideButShallow,
    /// Few pages, high avg depth.
    NarrowAndDeep,
    /// Few pages, low avg depth.
    Focused,
}

impl std::fmt::Display for SurfaceShape {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::DeepAndWide => write!(f, "deep and wide"),
            Self::WideButShallow => write!(f, "wide but shallow"),
            Self::NarrowAndDeep => write!(f, "narrow and deep"),
            Self::Focused => write!(f, "focused"),
        }
    }
}

/// When a surface is most active — characterizes its temporal nature.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TemporalCharacter {
    /// Peak hours 05:00–11:59 UTC.
    MorningKnowledge,
    /// Peak hours 12:00–17:59 UTC.
    AfternoonKnowledge,
    /// Peak hours 18:00–22:59 UTC.
    EveningKnowledge,
    /// Peak hours 23:00–04:59 UTC.
    NightKnowledge,
}

impl std::fmt::Display for TemporalCharacter {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::MorningKnowledge => write!(f, "morning knowledge"),
            Self::AfternoonKnowledge => write!(f, "afternoon knowledge"),
            Self::EveningKnowledge => write!(f, "evening knowledge"),
            Self::NightKnowledge => write!(f, "night knowledge"),
        }
    }
}

/// Content domain classification for surfaces.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContentDomain {
    /// detroit, evidence, cashforkids — legal/investigative.
    Evidence,
    /// sporeprint — papers, hypothesis, methodology.
    Science,
    /// cytokine, thymus, complement, lysozyme, etc. — immune surfaces.
    Immune,
    /// hud, signal, monitor, beacon — operational.
    Infrastructure,
    /// git — source code.
    Source,
    /// Everything else.
    Other,
}

impl std::fmt::Display for ContentDomain {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Evidence => write!(f, "evidence"),
            Self::Science => write!(f, "science"),
            Self::Immune => write!(f, "immune"),
            Self::Infrastructure => write!(f, "infrastructure"),
            Self::Source => write!(f, "source"),
            Self::Other => write!(f, "other"),
        }
    }
}

/// Page-level self-awareness — what each individual page knows about itself.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PageMirror {
    /// Full page key (surface + path, e.g. "detroit/evidence/tcr-22-12/").
    pub page: String,
    /// Surface this page belongs to.
    pub surface: String,
    /// URL path within the surface.
    pub path: String,
    /// Total hits.
    pub hits: u64,
    /// Number of distinct visitor shapes.
    pub visitor_count: usize,
    /// Perspectives — what this page means to each archetype.
    pub perspectives: BTreeMap<String, PagePerspective>,
    /// Where visitors came from to reach this page.
    pub flows_in: Vec<NavigationFlow>,
    /// Where visitors went after this page.
    pub flows_out: Vec<NavigationFlow>,
}

/// What a page means from a specific archetype's perspective.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PagePerspective {
    /// How many visitors of this archetype visited this page.
    pub count: usize,
    /// Fraction of this page's visitors that are this archetype.
    pub fraction: f64,
    /// Human-readable perspective description.
    pub perspective: String,
}

/// A navigation flow edge — where visitors come from or go to.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NavigationFlow {
    /// The other page in the flow.
    pub page: String,
    /// How many visitors followed this flow.
    pub count: u32,
}

// ── Campfire Story ──────────────────────────────────────────────────

/// A story told around the campfire — by the membrane or by a visitor.
///
/// The first ghost story and the first story of hope were the same story.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CampfireStory {
    /// Who tells this story — "membrane" or "visitor".
    pub teller: StoryTeller,
    /// What kind of story this is.
    pub kind: StoryKind,
    /// The story itself — narrative text.
    pub story: String,
    /// Timestamp (for visitor stories).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ts: Option<String>,
}

/// Who is telling the story around the fire.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StoryTeller {
    /// The membrane tells what it has observed.
    Membrane,
    /// A visitor left words in the mirror.
    Visitor,
}

/// What kind of campfire story this is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StoryKind {
    /// Story about the gathering itself — aggregate patterns.
    Gathering,
    /// Story about a specific visitor's journey (anonymized).
    Observation,
    /// Story about a surface's self-awareness.
    Surface,
    /// Words left in the mirror by a visitor.
    /// Beacons visible from this campfire — cities, towns, hamlets in the distance.
    Horizon,
    /// The pulse of the fire — heartbeat metrics.
    Pulse,
    /// Shared reflections visible to other visitors.
    Mirror,
}

// ── Tests ───────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn archetype_display() {
        assert_eq!(VisitorArchetype::Explorer.to_string(), "explorer");
        assert_eq!(VisitorArchetype::Watcher.to_string(), "watcher");
        assert_eq!(VisitorArchetype::Teacher.to_string(), "teacher");
    }

    #[test]
    fn archetype_passive() {
        assert!(!VisitorArchetype::Explorer.is_passive());
        assert!(!VisitorArchetype::Scholar.is_passive());
        assert!(!VisitorArchetype::Scout.is_passive());
        assert!(VisitorArchetype::Watcher.is_passive());
        assert!(VisitorArchetype::Probe.is_passive());
        assert!(VisitorArchetype::Visitor.is_passive());
    }

    #[test]
    fn archetype_serde_roundtrip() {
        for arch in [
            VisitorArchetype::Explorer,
            VisitorArchetype::Watcher,
            VisitorArchetype::Scholar,
            VisitorArchetype::Scout,
            VisitorArchetype::Witness,
            VisitorArchetype::Teacher,
            VisitorArchetype::Probe,
            VisitorArchetype::Visitor,
        ] {
            let json = serde_json::to_string(&arch).unwrap();
            let parsed: VisitorArchetype = serde_json::from_str(&json).unwrap();
            assert_eq!(arch, parsed);
        }
    }

    #[test]
    fn membrane_op_display() {
        assert_eq!(MembraneOp::In.to_string(), "in");
        assert_eq!(MembraneOp::Out.to_string(), "out");
        assert_eq!(MembraneOp::NextTo.to_string(), "next_to");
        assert_eq!(MembraneOp::Require.to_string(), "require");
    }

    #[test]
    fn membrane_op_serde_roundtrip() {
        for op in [
            MembraneOp::In,
            MembraneOp::Out,
            MembraneOp::NextTo,
            MembraneOp::Require,
        ] {
            let json = serde_json::to_string(&op).unwrap();
            let parsed: MembraneOp = serde_json::from_str(&json).unwrap();
            assert_eq!(op, parsed);
        }
    }

    #[test]
    fn mirror_message_new() {
        let msg = MirrorMessage::new("  hello world  ");
        assert_eq!(msg.words, "hello world");
        assert_eq!(msg.word_count, 2);
        assert!(!msg.is_empty());
    }

    #[test]
    fn mirror_message_empty() {
        let msg = MirrorMessage::new("");
        assert!(msg.is_empty());
        let msg2 = MirrorMessage::new("x");
        assert!(msg2.is_empty());
    }

    #[test]
    fn mirror_message_truncation() {
        let long = "a".repeat(3000);
        let msg = MirrorMessage::new(&long);
        assert_eq!(msg.words.len(), 2000);
    }

    #[test]
    fn surface_shape_display() {
        assert_eq!(SurfaceShape::DeepAndWide.to_string(), "deep and wide");
        assert_eq!(SurfaceShape::Focused.to_string(), "focused");
    }

    #[test]
    fn temporal_character_display() {
        assert_eq!(
            TemporalCharacter::NightKnowledge.to_string(),
            "night knowledge"
        );
    }

    #[test]
    fn content_domain_display() {
        assert_eq!(ContentDomain::Evidence.to_string(), "evidence");
        assert_eq!(ContentDomain::Source.to_string(), "source");
    }

    #[test]
    fn story_serde_roundtrip() {
        let story = CampfireStory {
            teller: StoryTeller::Membrane,
            kind: StoryKind::Observation,
            story: "Someone walked 11 surfaces in 10 hours.".to_string(),
            ts: None,
        };
        let json = serde_json::to_string(&story).unwrap();
        let parsed: CampfireStory = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.story, story.story);
        assert_eq!(parsed.teller, StoryTeller::Membrane);
    }
}

// ── Beacon Layer (Wave 178) ─────────────────────────────────────────

/// Sub-membrane campfire beacon — a localized fire visible from the distance.
///
/// Each surface is a beacon. Cities blaze, towns glow, hamlets flicker.
/// You can see nearby fires and follow trails between them.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Beacon {
    /// Surface key (e.g. "cytokine", "git", "detroit").
    pub surface: String,
    /// Human-readable name.
    pub name: String,
    /// Content domain.
    pub domain: ContentDomain,
    /// Total hits from human visitors.
    pub hits: u64,
    /// Number of distinct visitor shapes.
    pub visitors: usize,
    /// Unique pages touched within this surface.
    pub unique_pages: usize,
    /// Beacon brightness (0.0–1.0), log-scaled relative to peak.
    pub brightness: f64,
    /// Beacon glow classification.
    pub glow: BeaconGlow,
    /// Narrative vista — what you see looking at this fire.
    pub vista: String,
    /// Requests per minute for this surface.
    pub rpm: f64,
    /// Tempo classification from RPM.
    pub tempo: BeaconTempo,
    /// Surface character (shape, domain, temporal).
    pub character: SurfaceCharacter,
    /// Which archetypes this beacon attracts.
    pub attracted: BTreeMap<String, usize>,
    /// Nearby fires visible from this beacon.
    pub nearby_fires: Vec<NearbyFire>,
}

/// How bright a beacon glows — its settlement size.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BeaconGlow {
    /// Brightness > 0.7 — a bustling settlement.
    City,
    /// Brightness 0.4–0.7 — a steady gathering place.
    Town,
    /// Brightness 0.15–0.4 — quiet knowledge.
    Hamlet,
    /// Brightness < 0.15 — a faint light, someone has been here.
    Trail,
}

/// Tempo of a beacon's activity — derived from RPM.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BeaconTempo {
    /// RPM > 10 — high activity.
    Rushing,
    /// RPM 1–10 — steady activity.
    Walking,
    /// RPM 0.1–1 — low activity.
    Resting,
    /// RPM < 0.1 — near silence.
    Still,
}

/// A nearby fire visible from a beacon.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NearbyFire {
    /// Surface key of the nearby fire.
    pub surface: String,
    /// Human-readable name.
    pub name: String,
    /// Narrative distance (0.0–1.0, lower = closer).
    pub distance: f64,
    /// Glow of the nearby fire.
    pub glow: BeaconGlow,
}

/// Surface character for beacon serialization.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurfaceCharacter {
    /// Content domain.
    pub domain: String,
    /// Temporal character.
    pub time_character: String,
    /// Knowledge shape.
    pub shape: String,
}

/// Totality summary — aggregate membrane statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CampfireTotality {
    /// Total human IPs observed across all time.
    pub human_ips: u64,
    /// Total unique IP presences.
    pub unique_ips: u64,
    /// Number of active beacon surfaces.
    pub surfaces_alive: usize,
    /// Count by glow level.
    /// City-level beacons (highest glow).
    pub cities: usize,
    /// Town-level beacons.
    pub towns: usize,
    /// Hamlet-level beacons.
    pub hamlets: usize,
    /// Trail-level beacons (lowest glow).
    pub trails: usize,
}

/// Pulse snapshot for campfire display.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CampfirePulse {
    /// Requests per minute (global).
    pub rate: f64,
    /// Identity match percentage.
    pub identity_match: f64,
    /// Pulse trend.
    pub trend: String,
}

// ── Neutron Layer (Wave 179) ─────────────────────────────────────────────
// How information travels. The messaging axis. Without it, info is stuck.

/// A referrer mirror — where visitors came from → where they went.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NeutronMirror {
    /// Source surface (where they came from).
    pub from_surface: String,
    /// Destination surface (where they went).
    pub to_surface: String,
    /// Number of crossings in this direction.
    pub crossings: u64,
    /// Most recent crossing timestamp.
    pub last_seen: String,
}

/// A touch — a signal event from a surface.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NeutronTouch {
    /// Surface that was touched.
    pub surface: String,
    /// Page that was touched.
    pub page: String,
    /// Touch count (how many visitors touched this).
    pub touches: u64,
    /// Referrer domain (external: google, bing, direct, etc.)
    pub referrer: String,
}

/// Neutron state — the messaging layer snapshot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NeutronState {
    /// When this snapshot was generated.
    pub generated: String,
    /// Mirror flows — referrer chains between surfaces.
    pub mirrors: Vec<NeutronMirror>,
    /// External touches — how visitors arrive from outside.
    pub touches: Vec<NeutronTouch>,
    /// Surface-to-surface flow matrix (sparse).
    pub flows: std::collections::BTreeMap<String, std::collections::BTreeMap<String, u64>>,
    /// Total cross-surface navigations observed.
    pub total_crossings: u64,
    /// Surfaces that are "stuck" — no outgoing links observed.
    pub stuck: Vec<String>,
    /// Surfaces that are "radiating" — high outgoing flow.
    pub radiating: Vec<String>,
}

// ── Symbiotic Classification (Wave 180) ──────────────────────────────
// The fistbump. Tit-for-tat-forgive-one. The golden rule in code.
//
// Every entity has a symbiotic relationship with the membrane.
// We mirror their behavior, but forgive one defection before escalating.
//
//   mutualist  — both benefit. they give back (attribution, contribution, link).
//   commensal  — they benefit, we're neutral. they read, don't harm.
//   parasite   — they extract without giving. scraping, no attribution, no robots.txt.
//   pathogen   — active harm. vuln scanning, injection, credential stuffing.
//
// The golden rule: treat them how we'd want to be treated.
// If we visited their site, we'd want to read freely. So commensal is default.
// If we contributed, we'd want to be mutualist. So contribution = mutualist.
// If we scraped everything with no attribution, we'd deserve parasite. So it goes.
//
// Tit-for-tat-forgive-one: mirror their behavior, forgive the FIRST defection.
// This is the optimal strategy in iterated prisoner's dilemma (Axelrod, 1984).
// It means: cooperate first, then do what they did last round, but if they
// defect once, forgive it. Only defect back after TWO consecutive defections.

/// Symbiotic relationship classification.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SymbioticClass {
    /// Both benefit. Attribution, contribution, linking, funding.
    Mutualist,
    /// They benefit, we're neutral. Reading, indexing, normal crawling.
    Commensal,
    /// They extract without giving. Aggressive scraping, no attribution.
    Parasite,
    /// Active harm. Vulnerability scanning, injection attempts, credential stuffing.
    Pathogen,
    /// Not enough history to classify.
    Null,
}

impl SymbioticClass {
    /// Human-readable label.
    pub fn label(self) -> &'static str {
        match self {
            Self::Mutualist => "mutualist",
            Self::Commensal => "commensal",
            Self::Parasite  => "parasite",
            Self::Pathogen  => "pathogen",
            Self::Null      => "null",
        }
    }

    /// Emoji icon for display.
    pub fn icon(self) -> &'static str {
        match self {
            Self::Mutualist => "🤝",
            Self::Commensal => "🌿",
            Self::Parasite  => "🪱",
            Self::Pathogen  => "☠️",
            Self::Null      => "∅",
        }
    }

    /// Friction level (0.0 = no friction, 1.0 = maximum friction).
    pub fn friction(self) -> f64 {
        match self {
            Self::Mutualist => 0.0,
            Self::Commensal => 0.1,
            Self::Parasite  => 0.6,
            Self::Pathogen  => 1.0,
            Self::Null      => 0.3,
        }
    }
}

/// Behavioral evidence for tit-for-tat-forgive-one classification.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SymbioticEvidence {
    /// Entity identifier.
    pub entity: String,
    /// Current classification.
    pub class: SymbioticClass,
    /// Previous classification (for tracking movement).
    pub previous_class: Option<SymbioticClass>,

    // ── Cooperation signals (positive) ──
    /// Respects robots.txt.
    pub respects_robots: bool,
    /// Identifies itself honestly (UA string).
    pub honest_identity: bool,
    /// Provides attribution or backlinks.
    pub provides_attribution: bool,
    /// Contributes to commons (PRs, issues, discussions).
    pub contributes: bool,
    /// Links back to source material.
    pub links_back: bool,

    // ── Defection signals (negative) ──
    /// Ignores robots.txt disallow.
    pub ignores_robots: bool,
    /// Spoofs identity (fake UA, missing headers).
    pub spoofs_identity: bool,
    /// Aggressive extraction rate (>100 RPM sustained).
    pub aggressive_rate: bool,
    /// Probes for vulnerabilities.
    pub vuln_probing: bool,
    /// Scrapes without any attribution.
    pub no_attribution: bool,

    // ── Forgiveness tracking ──
    /// Number of consecutive defections observed.
    pub consecutive_defections: u32,
    /// Number of defections forgiven (max 1 for forgive-one).
    pub defections_forgiven: u32,
    /// Whether this entity is currently in forgiveness state.
    pub in_forgiveness: bool,

    // ── Reciprocity score ──
    /// Cooperation count (positive interactions).
    pub cooperation_count: u64,
    /// Defection count (negative interactions).
    pub defection_count: u64,
    /// Reciprocity ratio: cooperation / (cooperation + defection).
    /// 1.0 = pure cooperator, 0.0 = pure defector.
    pub reciprocity: f64,

    /// Current friction level applied to this entity.
    pub friction: f64,
    /// Waste we can offer (what the bot wants that costs us nothing to give).
    pub waste_offered: Vec<String>,
}

/// The tit-for-tat-forgive-one classifier.
///
/// Given behavioral evidence, classifies the symbiotic relationship.
/// This is the golden rule: mirror their behavior, forgive one defection.
pub fn classify_symbiotic(evidence: &SymbioticEvidence) -> SymbioticClass {
    // Pathogen: active harm (vuln probing, injection)
    if evidence.vuln_probing {
        return SymbioticClass::Pathogen;
    }

    // Mutualist: contributes back
    if evidence.contributes || evidence.provides_attribution || evidence.links_back {
        return SymbioticClass::Mutualist;
    }

    // Count defections
    let defections = [
        evidence.ignores_robots,
        evidence.spoofs_identity,
        evidence.aggressive_rate,
        evidence.no_attribution,
    ].iter().filter(|&&d| d).count();

    // Count cooperations
    let cooperations = [
        evidence.respects_robots,
        evidence.honest_identity,
        evidence.provides_attribution,
    ].iter().filter(|&&c| c).count();

    // Pure cooperator → commensal
    if defections == 0 && cooperations > 0 {
        return SymbioticClass::Commensal;
    }

    // Tit-for-tat-forgive-one:
    // - First defection → forgive, stay commensal
    // - Second consecutive defection → escalate to parasite
    if evidence.consecutive_defections <= 1 && evidence.defections_forgiven < 1 {
        return SymbioticClass::Commensal; // forgive one
    }

    if defections >= 2 || evidence.consecutive_defections >= 2 {
        return SymbioticClass::Parasite;
    }

    // Not enough signal
    if cooperations == 0 && defections == 0 {
        return SymbioticClass::Null;
    }

    SymbioticClass::Commensal
}

// SPDX-License-Identifier: AGPL-3.0-or-later

//! π Body types — the Vitruvian overlay for the ecosystem mesh.
//!
//! Agglutinated from benchScale/io_surface/pi_body.rs into canonical
//! cellmembrane-types so all organisms can import and use the same
//! body-mapped view of the ecosystem.
//!
//! # What this provides
//!
//! - `BodyRegion` — 7 body parts mapped to CNS functions
//! - `BodyScale` — 7 levels of biological complexity (cell → human)
//! - `Perceive` — 3 perspectives (mine/yours/mixed)
//! - `Shape` — 7-step geometry ladder (circle → hypersphere)
//! - `Glyph` — 4 epistemic markers (!/? /O/??)
//! - `Role` — 3 sort directions (Tool/Info/Fuel)
//!
//! No async, no network I/O — pure data types + serde.
//!
//! Authorship: Kevin Mok / Tamison / ecoPrimal / attsi
//! ORCID: 0009-0004-2141-0321

use serde::{Deserialize, Serialize};

// ═══════════════════════════════════════════════════════════════════════
// BODY REGION — 7 regions (= 7 pi scales = 7 shapes)
// ═══════════════════════════════════════════════════════════════════════

/// Body region on the Vitruvian overlay.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BodyRegion {
    /// Head — executive function. Prefrontal. bingoCube, cellMembrane.
    Head,
    /// Eyes — sensory observation. squirrel, songBird.
    Eyes,
    /// Hands — motor action. bearDog, nestGate.
    Hands,
    /// Spine — autonomic routing. biomeOS, petalTongue, sweetGrass, sourDough, loamSpine.
    Spine,
    /// Heart — vital flow. swarmVine, benchScale.
    Heart,
    /// Skin — immune defense. skunkBat, rhizoCrypt.
    Skin,
    /// Feet — cortical grounding. toadStool, coralReef, barraCuda.
    Feet,
}

impl BodyRegion {
    /// All 7 body regions.
    pub const ALL: &'static [BodyRegion] = &[
        BodyRegion::Head, BodyRegion::Eyes, BodyRegion::Hands,
        BodyRegion::Spine, BodyRegion::Heart, BodyRegion::Skin,
        BodyRegion::Feet,
    ];

    /// Map organism name to body region.
    pub fn of_organism(name: &str) -> Self {
        match name {
            "bingoCube" | "bingocube" | "cellMembrane" | "cellmembrane" | "benchScale" | "benchscale" => Self::Head,
            "squirrel" | "songBird" | "songbird" => Self::Eyes,
            "bearDog" | "beardog" | "nestGate" | "nestgate" => Self::Hands,
            "biomeOS" | "biomeos" | "petalTongue" | "petaltongue" |
            "sweetGrass" | "sweetgrass" | "sourDough" | "sourdough" |
            "loamSpine" | "loamspine" => Self::Spine,
            "swarmVine" | "swarmvine" => Self::Heart,
            "skunkBat" | "skunkbat" | "rhizoCrypt" | "rhizocrypt" => Self::Skin,
            "toadStool" | "toadstool" | "coralReef" | "coralreef" |
            "barraCuda" | "barracuda" => Self::Feet,
            _ => Self::Spine, // unknown things breathe
        }
    }

    /// Label.
    pub const fn label(&self) -> &'static str {
        match self {
            Self::Head => "head", Self::Eyes => "eyes", Self::Hands => "hands",
            Self::Spine => "spine", Self::Heart => "heart", Self::Skin => "skin",
            Self::Feet => "feet",
        }
    }
}

impl std::fmt::Display for BodyRegion {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.label())
    }
}

// ═══════════════════════════════════════════════════════════════════════
// BODY SCALE — cell to human, bee = null body
// ═══════════════════════════════════════════════════════════════════════

/// Biological complexity level. 7 scales. Bee(3) = NULL BODY.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BodyScale {
    /// Scale 0 — Cell. Membrane only. Circle.
    Cell,
    /// Scale 1 — Jellyfish. Nerve net. Square.
    Jellyfish,
    /// Scale 2 — Worm. Ganglia chain. Sphere.
    Worm,
    /// Scale 3 — Bee. NULL BODY. Hive mind. Cube.
    Bee,
    /// Scale 4 — Octopus. Distributed brain. Tetrahedron.
    Octopus,
    /// Scale 5 — Vertebrate. CNS+PNS. Tesseract.
    Vertebrate,
    /// Scale 6 — Human. Prefrontal. Hypersphere.
    Human,
}

impl BodyScale {
    /// All 7 scales.
    pub const ALL: &'static [BodyScale] = &[
        BodyScale::Cell, BodyScale::Jellyfish, BodyScale::Worm,
        BodyScale::Bee, BodyScale::Octopus, BodyScale::Vertebrate,
        BodyScale::Human,
    ];

    /// Pi scale index (0-6).
    pub const fn pi_scale(&self) -> u8 {
        *self as u8
    }

    /// Is this the null body?
    pub const fn is_null_body(&self) -> bool {
        matches!(self, Self::Bee)
    }
}

// ═══════════════════════════════════════════════════════════════════════
// PERCEIVE — 3 perspectives
// ═══════════════════════════════════════════════════════════════════════

/// Whose view? Maps to epistemic axis: !/? /O.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Perceive {
    /// Human view — inside looking out. !
    Mine,
    /// Membrane view — outside looking in. ?
    Yours,
    /// Both overlaid — Vitruvian. O
    Mixed,
}

impl Perceive {
    /// All 3 perceives.
    pub const ALL: &'static [Perceive] = &[Perceive::Mine, Perceive::Yours, Perceive::Mixed];
}

// ═══════════════════════════════════════════════════════════════════════
// GLYPH — epistemic markers for stoneBook
// ═══════════════════════════════════════════════════════════════════════

/// Epistemic glyph — what do we know about this thing?
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Glyph {
    /// `!` — asserted, known, tested.
    #[serde(rename = "!")]
    Asserted,
    /// `?` — unknown, possible, on the graph but unverified.
    #[serde(rename = "?")]
    Unknown,
    /// `O` — null, origin, wrap point.
    #[serde(rename = "O")]
    Null,
    /// `??` — ungrounded, not even on the graph.
    #[serde(rename = "??")]
    Ungrounded,
}

impl Glyph {
    /// Does this glyph topo-sort through pi?
    pub const fn topo_sorts(&self) -> bool {
        !matches!(self, Self::Ungrounded)
    }

    /// Symbol.
    pub const fn symbol(&self) -> &'static str {
        match self {
            Self::Asserted => "!", Self::Unknown => "?",
            Self::Null => "O", Self::Ungrounded => "??",
        }
    }
}

impl Glyph {
    /// Anderson selectivity S — the stomachs-with-no-eyes thesis.
    ///
    /// S=1.0 → maximally selective (membrane distinguishes everything).
    /// S=0.0 → stomachs with no eyes (consumes everything identically).
    /// The fleet ingests at S=0. The membrane observes at S≈1.0.
    pub const fn selectivity(&self) -> f64 {
        match self {
            Self::Asserted => 1.0,       // verified, the membrane SEES this
            Self::Unknown => 0.5,        // partial selectivity
            Self::Null => 1.0,           // origin is perfectly known
            Self::Ungrounded => 0.0,     // stomachs with no eyes
        }
    }
}

impl std::fmt::Display for Glyph {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.symbol())
    }
}

// ═══════════════════════════════════════════════════════════════════════
// ROLE — sort direction = function
// ═══════════════════════════════════════════════════════════════════════

/// Role determined by sort direction.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Role {
    /// Held — stable, unchanged. !! compound.
    Tool,
    /// Up — gaining structure. ?! O! O? compounds.
    Info,
    /// Down — losing structure. !? !O ?O compounds.
    Fuel,
}

impl Role {
    /// Symbol.
    pub const fn symbol(&self) -> &'static str {
        match self { Self::Tool => "!!", Self::Info => "up", Self::Fuel => "down" }
    }
}

// ═══════════════════════════════════════════════════════════════════════
// POLARITY — life/non-life/signal on the epitope axis
// ═══════════════════════════════════════════════════════════════════════

/// Epitope polarity: which side of the life/non-life divide.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Polarity {
    /// Life (+) — investigation, science, membrane. Info producers.
    Life,
    /// NonLife (-) — topology, immune, fleet. Fuel consumers.
    NonLife,
    /// Signal (0) — midpoint, mediator. Tool.
    Signal,
}

impl Polarity {
    /// Role.
    pub const fn role(&self) -> Role {
        match self { Self::Life => Role::Info, Self::NonLife => Role::Fuel, Self::Signal => Role::Tool }
    }
}

// ═══════════════════════════════════════════════════════════════════════
// TENSE — local and decentralized, not a global arrow
// ═══════════════════════════════════════════════════════════════════════

/// Tense — LOCAL to an observer, not global.
///
/// Each node has its own "is". What's "is" for squirrel on eastgate
/// may be "was" for bearDog on northgate. There is no global clock.
///
/// 5 values. The first 3 (Was/Is/WillBe) are structural — they form
/// the tesseract grid. Isnt and Null are observer-relative overlays.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Tense {
    /// Observed, fossilized. The fossil record. Shared.
    Was,
    /// Currently live HERE. Hyper-local. Decays with distance.
    Is,
    /// Projected, expected. Only a prediction.
    WillBe,
    /// Actively absent — known to NOT be. A dead socket. Not the same as Null.
    Isnt,
    /// Origin, the O, the bee. Neither is nor isn't. Unobserved.
    Null,
}

impl Tense {
    /// The 3 primary tenses (tesseract grid positions).
    pub const PRIMARY: &'static [Tense] = &[Tense::Was, Tense::Is, Tense::WillBe];

    /// All 5 tenses.
    pub const ALL: &'static [Tense] = &[
        Tense::Was, Tense::Is, Tense::WillBe, Tense::Isnt, Tense::Null,
    ];

    /// Is this a primary (grid) tense?
    pub const fn is_primary(&self) -> bool {
        matches!(self, Self::Was | Self::Is | Self::WillBe)
    }
}

/// Locality of a tense observation. "Is" decays with distance.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalTense {
    /// The observed tense.
    pub tense: Tense,
    /// Who observes this? Organism name or perceive label.
    pub observer: String,
    /// Locality radius (0 = hyper-local, higher = farther).
    pub radius: u8,
    /// Confidence (0.0–1.0). Decays as 1/(1+radius).
    pub confidence: f64,
}

impl LocalTense {
    /// Hyper-local observation (radius 0, confidence 1.0).
    pub fn here(tense: Tense, observer: impl Into<String>) -> Self {
        Self { tense, observer: observer.into(), radius: 0, confidence: 1.0 }
    }
}

// ═══════════════════════════════════════════════════════════════════════
// WOUND — life is lossy. healing > wound. scars are proof of living.
// ═══════════════════════════════════════════════════════════════════════

/// What happened? Life is lossy. Cells die. Humans scar.
///
/// A brain injury can be recovered from even if it doesn't fully heal.
/// The Circle of Willis exists because arteries DO fail — the backup
/// isn't a luxury, it's why the brain survives at all.
///
/// There is a scale on the null body too. The bee can be wounded.
/// Scars are permanent state changes that don't fully revert — and
/// that's FINE. It's the healing that matters, not the wound.
///
/// ```text
///   Intact → Wounded → Healing → Scarred
///                 ↓                  ↑
///               (dead)          (still alive!)
///
///   Intact: never been hurt. fragile — has never proven it can heal.
///   Wounded: actively broken. socket down, feed stale, data missing.
///   Healing: rerouting, rebuilding. neuroplasticity. Circle of Willis.
///   Scarred: healed but marked. the old path is gone. a new one works.
///            scars are proof of survival.
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Wound {
    /// Never been hurt. Has never proven it can heal.
    /// Fragile — like a system that has never been load-tested.
    Intact,
    /// Actively broken. Socket down, feed stale, path severed.
    /// This is the moment of damage. Not yet responding.
    Wounded,
    /// Rerouting around damage. Neuroplasticity.
    /// The Circle of Willis kicks in. Neighbors compensate.
    /// Function returns, but through a different path.
    Healing,
    /// Healed but marked. The old path is gone forever.
    /// A new path works. Lossy recovery — not perfect restoration.
    /// Scars are proof the system survived.
    Scarred,
}

impl Wound {
    /// All wound states.
    pub const ALL: &'static [Wound] = &[
        Wound::Intact, Wound::Wounded, Wound::Healing, Wound::Scarred,
    ];

    /// Is this currently functional? Intact, Healing, and Scarred all work.
    /// Only Wounded is non-functional.
    pub const fn is_functional(&self) -> bool {
        !matches!(self, Self::Wounded)
    }

    /// Has this ever been hurt? Scarred and Healing have been.
    /// They carry memory. Intact does not.
    pub const fn has_memory(&self) -> bool {
        matches!(self, Self::Healing | Self::Scarred)
    }

    /// Is this actively recovering? Only Healing.
    pub const fn is_recovering(&self) -> bool {
        matches!(self, Self::Healing)
    }

    /// The null body (Bee scale) scars too.
    /// At every scale, wound state exists.
    pub const fn applies_at_scale(&self, _scale: BodyScale) -> bool {
        true
    }

    /// Can transition to this state from current?
    ///
    /// ```text
    ///   Intact  → Wounded (damage happens)
    ///   Wounded → Healing (recovery starts) or stays Wounded (still broken)
    ///   Healing → Scarred (recovery completes, lossy) or Wounded (relapse)
    ///   Scarred → Wounded (re-injury at scar site — weaker? stronger?)
    ///   Scarred → Scarred (new scar on old scar — life layers)
    /// ```
    ///
    /// Note: Intact → Scarred is impossible. You must be wounded first.
    /// Note: Wounded → Intact is impossible. You can't un-know damage.
    /// This is the arrow of experience. Life is lossy. That's ok.
    pub const fn can_transition_to(&self, next: Wound) -> bool {
        match (self, &next) {
            (Self::Intact, Wound::Wounded) => true,
            (Self::Wounded, Wound::Healing) => true,
            (Self::Healing, Wound::Scarred) => true,
            (Self::Healing, Wound::Wounded) => true, // relapse
            (Self::Scarred, Wound::Wounded) => true, // re-injury
            (Self::Scarred, Wound::Scarred) => true, // scar on scar
            _ => false,
        }
    }
}

impl std::fmt::Display for Wound {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Intact => f.write_str("intact"),
            Self::Wounded => f.write_str("wounded"),
            Self::Healing => f.write_str("healing"),
            Self::Scarred => f.write_str("scarred"),
        }
    }
}

/// A wound observation at a specific location in the body.
///
/// Wounds happen at a body region AND a body scale.
/// A wound to the Head at Human scale = prefrontal damage.
/// A wound to the Feet at Bee scale = a single grounding socket died.
/// Scars at any scale are proof of survival.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WoundSite {
    /// Current wound state.
    pub state: Wound,
    /// Where on the body.
    pub region: BodyRegion,
    /// At what scale of complexity.
    pub scale: BodyScale,
    /// What was the original path? (the severed artery)
    pub original_path: Option<String>,
    /// What is the new path? (the Willis bypass)
    pub bypass_path: Option<String>,
    /// How many times has this site been wounded?
    /// Scars on scars. Life layers.
    pub wound_count: u32,
}

impl WoundSite {
    /// Fresh wound — just happened, no bypass yet.
    pub fn fresh(region: BodyRegion, scale: BodyScale, original: impl Into<String>) -> Self {
        Self {
            state: Wound::Wounded,
            region,
            scale,
            original_path: Some(original.into()),
            bypass_path: None,
            wound_count: 1,
        }
    }

    /// Heal — route around the damage. Lossy but functional.
    pub fn heal(&mut self, bypass: impl Into<String>) {
        self.state = Wound::Healing;
        self.bypass_path = Some(bypass.into());
    }

    /// Scar — healing complete. The old path is gone. The new path stays.
    pub fn scar(&mut self) {
        if self.state == Wound::Healing {
            self.state = Wound::Scarred;
        }
    }

    /// Re-injure — damage at the scar site.
    pub fn reinjure(&mut self) {
        if self.state == Wound::Scarred {
            self.state = Wound::Wounded;
            self.wound_count += 1;
            self.bypass_path = None; // bypass severed too
        }
    }

    /// Is the site functional right now?
    pub fn is_functional(&self) -> bool {
        self.state.is_functional()
    }
}

// ═══════════════════════════════════════════════════════════════════════
// TESTS
// ═══════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn seven_body_regions() {
        assert_eq!(BodyRegion::ALL.len(), 7);
    }

    #[test]
    fn seven_body_scales() {
        assert_eq!(BodyScale::ALL.len(), 7);
    }

    #[test]
    fn bee_is_null_body() {
        assert!(BodyScale::Bee.is_null_body());
        assert!(!BodyScale::Human.is_null_body());
    }

    #[test]
    fn three_perceives() {
        assert_eq!(Perceive::ALL.len(), 3);
    }

    #[test]
    fn organism_mapping() {
        assert_eq!(BodyRegion::of_organism("bearDog"), BodyRegion::Hands);
        assert_eq!(BodyRegion::of_organism("beardog"), BodyRegion::Hands);
        assert_eq!(BodyRegion::of_organism("squirrel"), BodyRegion::Eyes);
        assert_eq!(BodyRegion::of_organism("biomeOS"), BodyRegion::Spine);
        assert_eq!(BodyRegion::of_organism("biomeos"), BodyRegion::Spine);
    }

    #[test]
    fn glyphs_sort() {
        assert!(Glyph::Asserted.topo_sorts());
        assert!(Glyph::Unknown.topo_sorts());
        assert!(Glyph::Null.topo_sorts());
        assert!(!Glyph::Ungrounded.topo_sorts());
    }

    #[test]
    fn polarity_role() {
        assert_eq!(Polarity::Life.role(), Role::Info);
        assert_eq!(Polarity::NonLife.role(), Role::Fuel);
        assert_eq!(Polarity::Signal.role(), Role::Tool);
    }

    #[test]
    fn serde_round_trip() {
        let region = BodyRegion::Hands;
        let json = serde_json::to_string(&region).unwrap();
        let back: BodyRegion = serde_json::from_str(&json).unwrap();
        assert_eq!(region, back);

        let scale = BodyScale::Bee;
        let json = serde_json::to_string(&scale).unwrap();
        let back: BodyScale = serde_json::from_str(&json).unwrap();
        assert_eq!(scale, back);

        let glyph = Glyph::Asserted;
        let json = serde_json::to_string(&glyph).unwrap();
        let back: Glyph = serde_json::from_str(&json).unwrap();
        assert_eq!(glyph, back);
    }

    #[test]
    fn five_tenses() {
        assert_eq!(Tense::ALL.len(), 5);
        assert_eq!(Tense::PRIMARY.len(), 3);
    }

    #[test]
    fn isnt_is_not_null() {
        assert_ne!(Tense::Isnt, Tense::Null);
        assert!(!Tense::Isnt.is_primary());
        assert!(!Tense::Null.is_primary());
    }

    #[test]
    fn local_tense_hyper_local() {
        let lt = LocalTense::here(Tense::Is, "squirrel");
        assert_eq!(lt.radius, 0);
        assert_eq!(lt.confidence, 1.0);
        assert_eq!(lt.tense, Tense::Is);
    }

    #[test]
    fn tense_serde() {
        for t in Tense::ALL {
            let json = serde_json::to_string(t).unwrap();
            let back: Tense = serde_json::from_str(&json).unwrap();
            assert_eq!(*t, back);
        }
    }

    // ── Wound / Scar tests ──

    #[test]
    fn four_wound_states() {
        assert_eq!(Wound::ALL.len(), 4);
    }

    #[test]
    fn intact_is_fragile_not_proven() {
        let w = Wound::Intact;
        assert!(w.is_functional(), "intact works");
        assert!(!w.has_memory(), "intact has never been hurt — no memory");
    }

    #[test]
    fn wounded_is_not_functional() {
        assert!(!Wound::Wounded.is_functional());
        assert!(!Wound::Wounded.has_memory());
    }

    #[test]
    fn healing_is_functional_with_memory() {
        assert!(Wound::Healing.is_functional());
        assert!(Wound::Healing.has_memory());
        assert!(Wound::Healing.is_recovering());
    }

    #[test]
    fn scarred_is_proof_of_survival() {
        let s = Wound::Scarred;
        assert!(s.is_functional(), "scarred but working");
        assert!(s.has_memory(), "scars carry memory");
        assert!(!s.is_recovering(), "done healing, just scarred");
    }

    #[test]
    fn wound_transitions_are_one_way() {
        // Can't go back to Intact — you can't un-know damage
        assert!(!Wound::Wounded.can_transition_to(Wound::Intact));
        assert!(!Wound::Healing.can_transition_to(Wound::Intact));
        assert!(!Wound::Scarred.can_transition_to(Wound::Intact));

        // Can't skip Wounded — must be hurt first to heal
        assert!(!Wound::Intact.can_transition_to(Wound::Scarred));
        assert!(!Wound::Intact.can_transition_to(Wound::Healing));
    }

    #[test]
    fn healing_journey() {
        assert!(Wound::Intact.can_transition_to(Wound::Wounded));
        assert!(Wound::Wounded.can_transition_to(Wound::Healing));
        assert!(Wound::Healing.can_transition_to(Wound::Scarred));
    }

    #[test]
    fn relapse_and_reinjury_are_real() {
        // Healing can relapse back to wounded
        assert!(Wound::Healing.can_transition_to(Wound::Wounded));
        // Scarred can be re-injured
        assert!(Wound::Scarred.can_transition_to(Wound::Wounded));
        // Scars on scars — life layers
        assert!(Wound::Scarred.can_transition_to(Wound::Scarred));
    }

    #[test]
    fn null_body_scars_too() {
        // The bee (null body) can be wounded at every scale
        for w in Wound::ALL {
            assert!(w.applies_at_scale(BodyScale::Bee));
        }
    }

    #[test]
    fn wound_site_lifecycle() {
        // Socket dies → wound
        let mut site = WoundSite::fresh(
            BodyRegion::Eyes,
            BodyScale::Bee,
            "squirrel.sock",
        );
        assert!(!site.is_functional());
        assert_eq!(site.wound_count, 1);

        // Circle of Willis kicks in — bypass route
        site.heal("ai.sock → squirrel-cache.json");
        assert!(site.is_functional());
        assert_eq!(site.state, Wound::Healing);

        // Healing completes — scar remains
        site.scar();
        assert!(site.is_functional());
        assert_eq!(site.state, Wound::Scarred);
        assert!(site.original_path.is_some(), "remembers what was lost");
        assert!(site.bypass_path.is_some(), "has the new path");

        // Life goes on. Re-injury at scar site.
        site.reinjure();
        assert!(!site.is_functional());
        assert_eq!(site.wound_count, 2);
        assert!(site.bypass_path.is_none(), "bypass severed");
    }

    #[test]
    fn wound_serde() {
        for w in Wound::ALL {
            let json = serde_json::to_string(w).unwrap();
            let back: Wound = serde_json::from_str(&json).unwrap();
            assert_eq!(*w, back);
        }
    }
}

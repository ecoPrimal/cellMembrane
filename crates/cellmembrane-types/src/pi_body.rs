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
}

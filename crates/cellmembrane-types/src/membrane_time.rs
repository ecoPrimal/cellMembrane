// SPDX-License-Identifier: AGPL-3.0-or-later

//! Membrane-native time — a timekeeper, not a timer.
//!
//! Replaces 4,535 raw `chrono::Utc::now()` calls scattered across 10 organisms
//! with a single shared concept: **when did this happen in membrane time?**
//!
//! ## Design
//!
//! - Unix timestamp (u64 secs + u32 nanos) — no chrono dependency
//! - RFC 3339 formatting built-in (covers 90% of chrono usage)
//! - Staleness-aware: `is_stale(threshold)` uses BusTier-compatible seconds
//! - Gradient-composable: `age_secs()` feeds directly into `gradient_pressure()`
//! - RPM = Rotations Per Membrane — rhythm-relative time, not wall-clock
//!
//! ## The insight
//!
//! chrono is an external dependency that organisms import to ask "what time is it?"
//! But the membrane already has its own time: pulse rhythm, gradient pressure,
//! staleness thresholds. `MembraneTime` internalizes the external — the clock
//! becomes a property of the membrane, not an import from outside it.
//!
//! ## Not a timer
//!
//! Timers (`tokio::time`, `std::time::Instant`) measure duration — "how long
//! until?" That stays in std/tokio. `MembraneTime` is a timekeeper — "when did
//! this happen? how old is it? should it fire based on its tier?"

use serde::{Deserialize, Serialize};
use std::fmt;
use std::time::{SystemTime, UNIX_EPOCH};

/// A point in membrane time.
///
/// Wraps a Unix timestamp. No timezone, no chrono — just when.
/// Composes with `gradient_pressure()` and `BusTier::threshold_secs()`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct MembraneTime {
    /// Seconds since Unix epoch.
    pub secs: u64,
    /// Nanosecond fraction (0–999_999_999).
    pub nanos: u32,
}

impl MembraneTime {
    /// Now.
    #[must_use]
    pub fn now() -> Self {
        let d = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default();
        Self {
            secs: d.as_secs(),
            nanos: d.subsec_nanos(),
        }
    }

    /// From Unix seconds (integer).
    #[must_use]
    pub const fn from_secs(secs: u64) -> Self {
        Self { secs, nanos: 0 }
    }

    /// From Unix seconds (float, like `ts` in pulse feed).
    #[must_use]
    pub fn from_secs_f64(ts: f64) -> Self {
        let secs = ts as u64;
        let nanos = ((ts - secs as f64) * 1_000_000_000.0) as u32;
        Self { secs, nanos }
    }

    /// From a SystemTime.
    #[must_use]
    pub fn from_system_time(t: SystemTime) -> Self {
        let d = t.duration_since(UNIX_EPOCH).unwrap_or_default();
        Self {
            secs: d.as_secs(),
            nanos: d.subsec_nanos(),
        }
    }

    /// Age in seconds since this timestamp. For gradient_pressure().
    #[must_use]
    pub fn age_secs(&self) -> f64 {
        let now = Self::now();
        if now.secs < self.secs {
            return 0.0; // clock skew protection
        }
        (now.secs - self.secs) as f64
            + (now.nanos as f64 - self.nanos as f64) / 1_000_000_000.0
    }

    /// Is this timestamp stale? threshold_secs matches BusTier::threshold_secs().
    ///
    /// ```
    /// # use cellmembrane_types::membrane_time::MembraneTime;
    /// let t = MembraneTime::from_secs(0); // epoch = very old
    /// assert!(t.is_stale(300)); // stale after 5 minutes? yes, epoch is ancient
    /// ```
    #[must_use]
    pub fn is_stale(&self, threshold_secs: u64) -> bool {
        self.age_secs() >= threshold_secs as f64
    }

    /// Never stale — vital tier. Threshold 0 means always fresh.
    #[must_use]
    pub fn is_vital_stale(&self) -> bool {
        false // vital tier never considers things stale
    }

    /// Stale at sensory tier (30s).
    #[must_use]
    pub fn is_sensory_stale(&self) -> bool {
        self.is_stale(30)
    }

    /// Stale at cortical tier (120s).
    #[must_use]
    pub fn is_cortical_stale(&self) -> bool {
        self.is_stale(120)
    }

    /// Stale at motor tier (300s).
    #[must_use]
    pub fn is_motor_stale(&self) -> bool {
        self.is_stale(300)
    }

    /// As f64 Unix timestamp (for compatibility with pulse feed `ts` field).
    #[must_use]
    pub fn as_secs_f64(&self) -> f64 {
        self.secs as f64 + self.nanos as f64 / 1_000_000_000.0
    }

    /// Elapsed seconds between two membrane times (for gradient computation).
    #[must_use]
    pub fn elapsed_since(&self, earlier: &Self) -> f64 {
        self.as_secs_f64() - earlier.as_secs_f64()
    }

    /// Format as RFC 3339 (covers 90% of chrono formatting usage).
    /// e.g. "2026-10-20T16:34:42Z"
    #[must_use]
    pub fn to_rfc3339(&self) -> String {
        // Calculate date/time components from Unix timestamp
        let secs = self.secs as i64;
        let days = secs.div_euclid(86400);
        let day_secs = secs.rem_euclid(86400);
        let hours = day_secs / 3600;
        let minutes = (day_secs % 3600) / 60;
        let seconds = day_secs % 60;

        // Civil date from days since epoch (algorithm from Howard Hinnant)
        let z = days + 719468;
        let era = z.div_euclid(146097);
        let doe = z.rem_euclid(146097);
        let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
        let y = yoe + era * 400;
        let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
        let mp = (5 * doy + 2) / 153;
        let d = doy - (153 * mp + 2) / 5 + 1;
        let m = if mp < 10 { mp + 3 } else { mp - 9 };
        let y = if m <= 2 { y + 1 } else { y };

        format!("{y:04}-{m:02}-{d:02}T{hours:02}:{minutes:02}:{seconds:02}Z")
    }

    /// RPM — Rotations Per Membrane.
    ///
    /// Given a pulse rhythm (from the live `pulse` feed), compute how many
    /// membrane rotations have elapsed since this timestamp.
    ///
    /// `rhythm` is the current pulse_rhythm value (0.0–1.0).
    /// Higher rhythm = more rotations per wall-clock second.
    #[must_use]
    pub fn rpm(&self, rhythm: f64) -> f64 {
        let age = self.age_secs();
        if rhythm <= 0.0 {
            return age; // degenerate: 1 RPM = 1 wall-clock second
        }
        age * rhythm
    }
}

impl Default for MembraneTime {
    fn default() -> Self {
        Self::now()
    }
}

impl fmt::Display for MembraneTime {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.to_rfc3339())
    }
}

impl From<SystemTime> for MembraneTime {
    fn from(t: SystemTime) -> Self {
        Self::from_system_time(t)
    }
}

// ═══════════════════════════════════════════════════════════════════════
// EVOLUTION PRESSURE — sigmoid + gradient applied to live membrane data
//
// The sigmoid aperture, gradient pressure, and BusTier math from cns.rs
// applied to membrane evolution: what should change, and how urgently?
// ═══════════════════════════════════════════════════════════════════════

/// A measurement of evolutionary pressure on a membrane component.
///
/// Combines the sigmoid aperture (load-based flow control) with gradient
/// pressure (staleness difference) and pulse rhythm (membrane tempo).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvolutionPressure {
    /// What's being measured (e.g. "classification", "health", "topology").
    pub component: String,

    /// Gradient pressure: output staleness - input freshness.
    /// Positive = should evolve. Negative = outputs are fresh, hold.
    pub gradient: f64,

    /// Aperture value (0.12–1.0). Sigmoid of current load.
    pub aperture: f64,

    /// Should this component fire (evolve)?
    pub should_fire: bool,

    /// The tier this component operates at.
    pub tier: String,

    /// RPM — membrane-time rotations since last evolution.
    pub rpm: f64,

    /// Rhythm-adjusted urgency: gradient * aperture * rhythm.
    /// This is the actual pressure after all gates are applied.
    pub urgency: f64,
}

/// Compute the sigmoid aperture from a normalized load.
///
/// `aperture(load) = 1 / (1 + e^(2.2 × (load - 1.2)))`, floor 0.12.
/// Non-Newtonian: thick under shear, never a brick wall.
#[must_use]
pub fn aperture(load_normalized: f64) -> f64 {
    (1.0 / (1.0 + (2.2 * (load_normalized - 1.2)).exp()))
        .max(0.12)
        .min(1.0)
}

/// Compute gradient pressure from ages.
#[must_use]
pub fn gradient_pressure(input_ages: &[f64], output_ages: &[f64]) -> f64 {
    if output_ages.is_empty() {
        return 9999.0;
    }
    let freshest_in = input_ages.iter().copied().reduce(f64::min).unwrap_or(0.0);
    let stalest_out = output_ages.iter().copied().reduce(f64::max).unwrap_or(0.0);
    stalest_out - freshest_in
}

/// Tier thresholds (seconds). Mirrors BusTier::threshold_secs().
#[must_use]
pub const fn tier_threshold(tier: &str) -> u64 {
    match tier.as_bytes() {
        b"vital" => 0,
        b"sensory" => 30,
        b"cortical" => 120,
        b"motor" => 300,
        _ => 60, // default: 1 minute
    }
}

/// Should a component fire given its tier, gradient, and aperture?
#[must_use]
pub fn should_fire(tier: &str, gradient: f64, aperture_val: f64) -> bool {
    match tier.as_bytes() {
        b"vital" => true,
        b"motor" => gradient >= tier_threshold(tier) as f64 && aperture_val >= 0.10,
        _ => gradient >= tier_threshold(tier) as f64,
    }
}

/// Compute evolution pressure for a component using live membrane data.
///
/// `input_times`: when inputs were last refreshed.
/// `output_times`: when outputs were last written.
/// `load`: current normalized load (0.0 = idle, 1.0 = saturated, >1.0 = overloaded).
/// `rhythm`: current pulse_rhythm from the membrane (0.0–1.0).
/// `tier`: "vital", "sensory", "cortical", "motor".
#[must_use]
pub fn evolution_pressure(
    component: &str,
    input_times: &[MembraneTime],
    output_times: &[MembraneTime],
    load: f64,
    rhythm: f64,
    tier: &str,
) -> EvolutionPressure {
    let input_ages: Vec<f64> = input_times.iter().map(MembraneTime::age_secs).collect();
    let output_ages: Vec<f64> = output_times.iter().map(MembraneTime::age_secs).collect();
    let gradient = gradient_pressure(&input_ages, &output_ages);
    let aperture_val = aperture(load);
    let fires = should_fire(tier, gradient, aperture_val);

    // RPM: average output age in membrane-time
    let avg_output_age = if output_ages.is_empty() {
        9999.0
    } else {
        output_ages.iter().sum::<f64>() / output_ages.len() as f64
    };
    let rpm = avg_output_age * rhythm.max(0.001);

    // Urgency: the product of all gates
    let urgency = gradient.max(0.0) * aperture_val * rhythm.max(0.001);

    EvolutionPressure {
        component: component.into(),
        gradient,
        aperture: aperture_val,
        should_fire: fires,
        tier: tier.into(),
        rpm,
        urgency,
    }
}

// ═══════════════════════════════════════════════════════════════════════
// TESTS
// ═══════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_now_is_recent() {
        let t = MembraneTime::now();
        assert!(t.secs > 1_700_000_000, "should be after 2023");
        assert!(t.age_secs() < 1.0, "just created, should be <1s old");
    }

    #[test]
    fn test_from_secs() {
        let t = MembraneTime::from_secs(1729000000);
        assert_eq!(t.secs, 1729000000);
        assert_eq!(t.nanos, 0);
    }

    #[test]
    fn test_from_secs_f64() {
        let t = MembraneTime::from_secs_f64(1729000000.5);
        assert_eq!(t.secs, 1729000000);
        assert!(t.nanos > 499_000_000 && t.nanos < 501_000_000);
    }

    #[test]
    fn test_age_secs() {
        let old = MembraneTime::from_secs(0); // epoch
        assert!(old.age_secs() > 1_700_000_000.0);
    }

    #[test]
    fn test_is_stale() {
        let old = MembraneTime::from_secs(0);
        assert!(old.is_stale(300));
        assert!(old.is_sensory_stale());
        assert!(old.is_cortical_stale());
        assert!(old.is_motor_stale());
        assert!(!old.is_vital_stale()); // vital never stale
    }

    #[test]
    fn test_fresh_is_not_stale() {
        let fresh = MembraneTime::now();
        assert!(!fresh.is_sensory_stale());
        assert!(!fresh.is_cortical_stale());
        assert!(!fresh.is_motor_stale());
    }

    #[test]
    fn test_rfc3339() {
        // 2024-01-01T00:00:00Z
        let t = MembraneTime::from_secs(1704067200);
        assert_eq!(t.to_rfc3339(), "2024-01-01T00:00:00Z");
    }

    #[test]
    fn test_rfc3339_epoch() {
        let t = MembraneTime::from_secs(0);
        assert_eq!(t.to_rfc3339(), "1970-01-01T00:00:00Z");
    }

    #[test]
    fn test_display() {
        let t = MembraneTime::from_secs(1704067200);
        assert_eq!(format!("{t}"), "2024-01-01T00:00:00Z");
    }

    #[test]
    fn test_elapsed_since() {
        let a = MembraneTime::from_secs(1000);
        let b = MembraneTime::from_secs(1060);
        assert!((b.elapsed_since(&a) - 60.0).abs() < 0.001);
    }

    #[test]
    fn test_rpm() {
        let t = MembraneTime::from_secs(MembraneTime::now().secs - 100);
        let rhythm = 0.5;
        let rpm = t.rpm(rhythm);
        // ~100 wall-seconds * 0.5 rhythm = ~50 RPM
        assert!(rpm > 45.0 && rpm < 55.0, "rpm={rpm}");
    }

    #[test]
    fn test_ordering() {
        let a = MembraneTime::from_secs(100);
        let b = MembraneTime::from_secs(200);
        assert!(a < b);
    }

    #[test]
    fn test_serde_roundtrip() {
        let t = MembraneTime::from_secs(1729000000);
        let json = serde_json::to_string(&t).unwrap();
        let t2: MembraneTime = serde_json::from_str(&json).unwrap();
        assert_eq!(t, t2);
    }

    // ── Evolution pressure tests ──

    #[test]
    fn test_aperture_idle() {
        let a = aperture(0.0);
        assert!(a > 0.90 && a < 1.0, "idle → mostly open, got {a}");
    }

    #[test]
    fn test_aperture_overloaded() {
        let a = aperture(2.0);
        assert!(a > 0.11 && a < 0.20, "overloaded → floor, got {a}");
    }

    #[test]
    fn test_aperture_normal() {
        let a = aperture(0.5);
        assert!(a > 0.8 && a < 1.0, "half load → mostly open, got {a}");
    }

    #[test]
    fn test_gradient_no_outputs() {
        let g = gradient_pressure(&[10.0], &[]);
        assert_eq!(g, 9999.0, "no outputs → infinite gradient");
    }

    #[test]
    fn test_gradient_fresh_outputs() {
        let g = gradient_pressure(&[100.0], &[10.0]);
        assert!(g < 0.0, "outputs fresher than inputs → negative gradient");
    }

    #[test]
    fn test_gradient_stale_outputs() {
        let g = gradient_pressure(&[10.0], &[500.0]);
        assert!(g > 0.0, "outputs staler than inputs → positive gradient");
    }

    #[test]
    fn test_should_fire_vital() {
        assert!(should_fire("vital", -100.0, 0.01), "vital always fires");
    }

    #[test]
    fn test_should_fire_motor_low_aperture() {
        assert!(!should_fire("motor", 400.0, 0.05), "motor needs aperture >= 0.10");
    }

    #[test]
    fn test_should_fire_motor_high_aperture() {
        assert!(should_fire("motor", 400.0, 0.15), "motor fires with gradient + aperture");
    }

    #[test]
    fn test_evolution_pressure_live() {
        let now = MembraneTime::now();
        let old = MembraneTime::from_secs(now.secs.saturating_sub(200));
        let fresh = MembraneTime::from_secs(now.secs.saturating_sub(5));

        let ep = evolution_pressure(
            "classification",
            &[fresh],       // input is 5s old
            &[old],         // output is 200s old
            0.3,            // light load
            0.774,          // live rhythm from pulse feed
            "cortical",     // 120s threshold
        );

        assert!(ep.gradient > 100.0, "200s output - 5s input = ~195s gradient");
        assert!(ep.aperture > 0.85, "light load → wide aperture, got {}", ep.aperture);
        assert!(ep.should_fire, "cortical threshold 120s, gradient ~195s → fire");
        assert!(ep.urgency > 0.0, "urgency should be positive");
    }

    #[test]
    fn test_evolution_pressure_fresh() {
        let now = MembraneTime::now();
        let recent = MembraneTime::from_secs(now.secs.saturating_sub(10));

        let ep = evolution_pressure(
            "health",
            &[recent],
            &[recent],
            0.5,
            0.5,
            "sensory",
        );

        assert!(!ep.should_fire, "both recent → gradient ~0 < 30s threshold");
    }
}

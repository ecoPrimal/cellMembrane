// SPDX-License-Identifier: AGPL-3.0-or-later

//! Fleet antibody types — adaptive immune pattern memory.
//!
//! An antibody stores the **shape** that recognizes a pathogenic fleet,
//! not the fleet itself. No IPs are stored — IPs are ephemeral routing
//! decisions made by the Caddy layer.

pub mod posture;
pub mod antibody;
pub mod opsonize;

pub use posture::*;
pub use antibody::*;
pub use opsonize::*;

mod tests {
    use super::*;

    fn sample_antibody() -> FleetAntibody {
        FleetAntibody {
            id: "test-antibody-001".to_string(),
            ua_fingerprint: UaFingerprint {
                ua_count: 2,
                top_ua_pct: 0.50,
                platform_split: [0.50, 0.50, 0.0],
            },
            timing: TimingSignature {
                mean_interval_ms: 6000,
                interval_cv: 0.15,
            },
            path_pattern: PathPattern {
                commit_url_pct: 0.92,
                single_page_pct: 0.95,
                has_referrer_pct: 0.0,
            },
            deception: DeceptionSignals {
                hides_identity: true,
                rotates_ips: true,
                ignores_rejection: true,
                encoding_uniform: true,
                ..Default::default()
            },
            confidence: 0.9,
            first_seen_epoch: 1000,
            last_matched_epoch: 2000,
            match_count: 50,
            escalation: DefensePosture::Observe,
            last_defection_epoch: 0,
            defection_count: 0,
            forgive_window_secs: DEFAULT_FORGIVE_WINDOW_SECS,
        }
    }

    fn similar_observation() -> FleetObservation {
        FleetObservation {
            timestamp_epoch: 3000,
            total_requests: 200,
            unique_ips: 180,
            ua_fingerprint: UaFingerprint {
                ua_count: 3,
                top_ua_pct: 0.45,
                platform_split: [0.45, 0.50, 0.05],
            },
            timing: TimingSignature {
                mean_interval_ms: 5500,
                interval_cv: 0.18,
            },
            path_pattern: PathPattern {
                commit_url_pct: 0.88,
                single_page_pct: 0.90,
                has_referrer_pct: 0.01,
            },
            deception: DeceptionSignals {
                hides_identity: true,
                rotates_ips: true,
                ignores_rejection: true,
                encoding_uniform: false,
                ..Default::default()
            },
            depth_distribution: [170, 8, 2, 0],
            rejected_ips: 160,
        }
    }

    #[test]
    fn antibody_matches_similar_fleet() {
        let ab = sample_antibody();
        let obs = similar_observation();
        assert!(ab.matches_observation(&obs));
    }

    #[test]
    fn antibody_rejects_human_traffic() {
        let ab = sample_antibody();
        let human_obs = FleetObservation {
            timestamp_epoch: 3000,
            total_requests: 50,
            unique_ips: 30,
            ua_fingerprint: UaFingerprint {
                ua_count: 25,
                top_ua_pct: 0.08,
                platform_split: [0.30, 0.55, 0.15],
            },
            timing: TimingSignature {
                mean_interval_ms: 45_000,
                interval_cv: 1.8,
            },
            path_pattern: PathPattern {
                commit_url_pct: 0.02,
                single_page_pct: 0.20,
                has_referrer_pct: 0.70,
            },
            deception: DeceptionSignals {
                hides_identity: false,
                rotates_ips: false,
                ignores_rejection: false,
                encoding_uniform: false,
                ..Default::default()
            },
            depth_distribution: [10, 12, 6, 2],
            rejected_ips: 0,
        };
        assert!(!ab.matches_observation(&human_obs));
    }

    #[test]
    fn decayed_antibody_does_not_match() {
        let mut ab = sample_antibody();
        for _ in 0..50 {
            ab.decay(0.9);
        }
        assert!(ab.confidence < 0.1);
        assert!(!ab.matches_observation(&similar_observation()));
    }

    #[test]
    fn serde_roundtrip() {
        let ab = sample_antibody();
        let json = serde_json::to_string(&ab).unwrap();
        let parsed: FleetAntibody = serde_json::from_str(&json).unwrap();
        assert_eq!(ab.id, parsed.id);
        assert_eq!(ab.match_count, parsed.match_count);
        assert_eq!(parsed.escalation, DefensePosture::Observe);
    }

    #[test]
    fn serde_backwards_compat() {
        // Old antibodies without escalation fields should deserialize with defaults
        let json = r#"{"id":"old","ua_fingerprint":{"ua_count":2,"top_ua_pct":0.5,"platform_split":[0.5,0.5,0.0]},"timing":{"mean_interval_ms":6000,"interval_cv":0.15},"path_pattern":{"commit_url_pct":0.9,"single_page_pct":0.9,"has_referrer_pct":0.0},"deception":{"hides_identity":true,"rotates_ips":true,"ignores_rejection":true,"encoding_uniform":true},"confidence":0.8,"first_seen_epoch":1000,"last_matched_epoch":2000,"match_count":10}"#;
        let parsed: FleetAntibody = serde_json::from_str(json).unwrap();
        assert_eq!(parsed.escalation, DefensePosture::Observe);
        assert_eq!(parsed.defection_count, 0);
        assert_eq!(parsed.forgive_window_secs, DEFAULT_FORGIVE_WINDOW_SECS);
        // New deception fields default to false for old data
        assert!(!parsed.deception.chrome_impersonation);
        assert!(!parsed.deception.header_poverty);
    }

    #[test]
    fn posture_escalation_ladder() {
        assert_eq!(DefensePosture::Observe.escalate(), DefensePosture::WarnRoute);
        assert_eq!(DefensePosture::WarnRoute.escalate(), DefensePosture::SlowDegrade);
        assert_eq!(DefensePosture::SlowDegrade.escalate(), DefensePosture::Scatter);
        assert_eq!(DefensePosture::Scatter.escalate(), DefensePosture::Vanish);
        assert_eq!(DefensePosture::Vanish.escalate(), DefensePosture::Disperse);
        assert_eq!(DefensePosture::Disperse.escalate(), DefensePosture::Disperse);
    }

    #[test]
    fn posture_deescalation_ladder() {
        assert_eq!(DefensePosture::Disperse.deescalate(), DefensePosture::Vanish);
        assert_eq!(DefensePosture::Vanish.deescalate(), DefensePosture::Scatter);
        assert_eq!(DefensePosture::Scatter.deescalate(), DefensePosture::SlowDegrade);
        assert_eq!(DefensePosture::SlowDegrade.deescalate(), DefensePosture::WarnRoute);
        assert_eq!(DefensePosture::WarnRoute.deescalate(), DefensePosture::Observe);
        assert_eq!(DefensePosture::Observe.deescalate(), DefensePosture::Observe);
    }

    #[test]
    fn tick_escalation_first_match_goes_to_warn() {
        let mut ab = sample_antibody();
        let prev = ab.tick_escalation(true, 5000);
        assert_eq!(prev, Some(DefensePosture::Observe));
        assert_eq!(ab.escalation, DefensePosture::WarnRoute);
    }

    #[test]
    fn tick_escalation_ignores_rejection_fast_tracks() {
        let mut ab = sample_antibody();
        ab.escalation = DefensePosture::WarnRoute;
        // ignores_rejection is true on sample_antibody
        let prev = ab.tick_escalation(true, 5000);
        assert_eq!(prev, Some(DefensePosture::WarnRoute));
        assert_eq!(ab.escalation, DefensePosture::SlowDegrade);
    }

    #[test]
    fn tick_escalation_full_ladder() {
        let mut ab = sample_antibody();
        let mut t = 1000u64;

        // P0 → P1
        ab.tick_escalation(true, t);
        assert_eq!(ab.escalation, DefensePosture::WarnRoute);

        // P1 → P2 (ignores_rejection = true)
        t += 60;
        ab.tick_escalation(true, t);
        assert_eq!(ab.escalation, DefensePosture::SlowDegrade);

        // P2 → P3 (need ESCALATE_TO_SCATTER consecutive)
        for _ in 0..ESCALATE_TO_SCATTER {
            t += 60;
            ab.tick_escalation(true, t);
        }
        assert_eq!(ab.escalation, DefensePosture::Scatter);

        // P3 → P4 (need ESCALATE_TO_VANISH consecutive)
        for _ in 0..ESCALATE_TO_VANISH {
            t += 60;
            ab.tick_escalation(true, t);
        }
        assert_eq!(ab.escalation, DefensePosture::Vanish);

        // P4 → P5 (need ESCALATE_TO_DISPERSE cumulative defections)
        while ab.escalation != DefensePosture::Disperse {
            t += 60;
            ab.tick_escalation(true, t);
        }
        assert_eq!(ab.escalation, DefensePosture::Disperse);
        assert!(ab.defection_count >= ESCALATE_TO_DISPERSE);
    }

    #[test]
    fn tick_forgive_deescalates() {
        let mut ab = sample_antibody();
        ab.escalation = DefensePosture::SlowDegrade;
        ab.last_defection_epoch = 1000;

        // Not enough silence
        let prev = ab.tick_escalation(false, 1000 + ab.forgive_window_secs - 1);
        assert!(prev.is_none());
        assert_eq!(ab.escalation, DefensePosture::SlowDegrade);

        // Enough silence → forgive one level
        let prev = ab.tick_escalation(false, 1000 + ab.forgive_window_secs);
        assert_eq!(prev, Some(DefensePosture::SlowDegrade));
        assert_eq!(ab.escalation, DefensePosture::WarnRoute);
        assert_eq!(ab.defection_count, 0);
    }

    #[test]
    fn posture_ordering() {
        assert!(DefensePosture::Observe < DefensePosture::WarnRoute);
        assert!(DefensePosture::WarnRoute < DefensePosture::SlowDegrade);
        assert!(DefensePosture::SlowDegrade < DefensePosture::Scatter);
        assert!(DefensePosture::Scatter < DefensePosture::Vanish);
        assert!(DefensePosture::Vanish < DefensePosture::Disperse);
    }

    #[test]
    fn trust_descriptor_monotonically_decreasing() {
        let postures = [
            DefensePosture::Observe,
            DefensePosture::WarnRoute,
            DefensePosture::SlowDegrade,
            DefensePosture::Scatter,
            DefensePosture::Vanish,
            DefensePosture::Disperse,
        ];
        for i in 0..postures.len() - 1 {
            let a = postures[i].trust_descriptor();
            let b = postures[i + 1].trust_descriptor();
            assert!(
                a.trust_level >= b.trust_level,
                "{:?} trust ({}) should be >= {:?} trust ({})",
                postures[i], a.trust_level, postures[i + 1], b.trust_level,
            );
        }
        // First and last should be strictly different
        let first = postures[0].trust_descriptor();
        let last = postures[postures.len() - 1].trust_descriptor();
        assert!(first.trust_level > last.trust_level);
    }

    #[test]
    fn trust_descriptor_beardog_mapping() {
        // Observe → still trusted, active contributor
        let d = DefensePosture::Observe.trust_descriptor();
        assert_eq!(d.membership_hint, "ActiveContributor");
        assert!(d.trust_level >= 0.6);
        assert!(d.restoration_available);

        // WarnRoute → cautious, first signal
        let d = DefensePosture::WarnRoute.trust_descriptor();
        assert_eq!(d.membership_hint, "CautiousInteraction");
        assert!(d.trust_level >= 0.3 && d.trust_level < 0.6);
        assert!(d.restoration_available);

        // Scatter → ecosystem protection
        let d = DefensePosture::Scatter.trust_descriptor();
        assert_eq!(d.membership_hint, "EcosystemProtection");
        assert!(d.trust_level < 0.2);
        assert!(d.restoration_available);

        // Vanish → full protection, no restoration
        let d = DefensePosture::Vanish.trust_descriptor();
        assert_eq!(d.membership_hint, "EcosystemProtection");
        assert_eq!(d.trust_level, 0.0);
        assert!(!d.restoration_available);

        // Disperse → active defense, no restoration
        let d = DefensePosture::Disperse.trust_descriptor();
        assert_eq!(d.membership_hint, "EcosystemProtection");
        assert_eq!(d.symbiosis_hint, "ActiveDefense");
        assert_eq!(d.trust_level, 0.0);
        assert!(!d.restoration_available);
    }

    #[test]
    fn behavioral_hash_stable_across_minor_variation() {
        let obs1 = similar_observation();
        let mut obs2 = obs1.clone();
        // Minor variations that should NOT change the hash
        obs2.total_requests += 50;
        obs2.unique_ips += 20;
        obs2.timing.mean_interval_ms += 500;

        assert_eq!(
            behavioral_hash(&obs1),
            behavioral_hash(&obs2),
            "minor variations should not change behavioral hash"
        );
    }

    #[test]
    fn behavioral_hash_changes_on_major_shift() {
        let obs = similar_observation();
        let mut shifted = obs.clone();
        // Major shift: from commit-heavy to diverse browsing
        shifted.path_pattern.commit_url_pct = 0.05;
        shifted.path_pattern.single_page_pct = 0.20;
        shifted.deception.hides_identity = false;
        shifted.deception.rotates_ips = false;

        assert_ne!(
            behavioral_hash(&obs),
            behavioral_hash(&shifted),
            "major behavioral shift should change hash"
        );
    }

    #[test]
    fn behavioral_hash_ignores_ip_count() {
        let obs1 = similar_observation();
        let mut obs2 = obs1.clone();
        obs2.unique_ips = 5000; // wildly different IP count

        assert_eq!(
            behavioral_hash(&obs1),
            behavioral_hash(&obs2),
            "hash must not depend on IP count"
        );
    }

    #[test]
    fn extract_invariants_fleet_pattern() {
        let obs = similar_observation();
        let inv = extract_invariants(&obs);
        assert!(inv.deep_content_dominant);
        assert!(inv.cookieless);
        assert_eq!(inv.session_depth, "high");
        assert_eq!(inv.ua_diversity, "narrow");
        assert_eq!(inv.ip_pattern, "rotating");
        assert!(inv.deception_flags.contains(&"hides_identity".to_string()));
        assert!(inv.deception_flags.contains(&"rotates_ips".to_string()));
    }

    #[test]
    fn opsonize_tag_serde_roundtrip() {
        let tag = OpsonizeTag {
            behavioral_hash: "a3f71234deadbeef".to_string(),
            detectors: vec!["content_gate".to_string(), "stale_chrome".to_string()],
            confidence: 0.95,
            origin_gate: "golgiBody".to_string(),
            invariants: extract_invariants(&similar_observation()),
            response: OpsonizeResponse::Scatter { ratio: 0.3 },
            created_epoch: 1000,
            last_confirmed_epoch: 2000,
            match_count: 50,
        };
        let json = serde_json::to_string(&tag).unwrap();
        let parsed: OpsonizeTag = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.behavioral_hash, tag.behavioral_hash);
        assert_eq!(parsed.detectors.len(), 2);
        assert_eq!(parsed.match_count, 50);
    }
}

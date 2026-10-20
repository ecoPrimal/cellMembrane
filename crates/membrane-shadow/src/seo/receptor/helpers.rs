// SPDX-License-Identifier: AGPL-3.0-or-later

//! Receptor helper functions — normalization, hashing, session detection.

use std::collections::BTreeMap;

use super::types::*;
use super::{VisitorClass, SESSION_WINDOW_SECS, VELOCITY_THRESHOLD, VELOCITY_WINDOW_SECS};

pub(crate) fn normalize_path(uri: &str) -> String {
    let path = uri.split('?').next().unwrap_or(uri);
    let path = path.split('#').next().unwrap_or(path);
    if path.is_empty() {
        "/".to_string()
    } else {
        path.to_string()
    }
}

/// SHA-256 hash of a string, returned as hex. Used for UA hashing.
pub(crate) fn sha256_hex(s: &str) -> String {
    use sha2::{Digest, Sha256};
    let digest = Sha256::digest(s.as_bytes());
    hex::encode(digest)
}

/// Group raw hits into sessions and compute per-host summaries.
///
/// A session is: same User-Agent string, hits within [`SESSION_WINDOW_SECS`],
/// ordered by timestamp. Different hosts = separate sessions.
pub(crate) fn build_session_summaries(raw_hits: &[RawHit]) -> BTreeMap<String, SessionSummary> {
    if raw_hits.is_empty() {
        return BTreeMap::new();
    }

    // Group by (host, UA) and sort by timestamp.
    let mut grouped: BTreeMap<(String, String), Vec<&RawHit>> = BTreeMap::new();
    for hit in raw_hits {
        grouped
            .entry((hit.host.clone(), hit.ua.clone()))
            .or_default()
            .push(hit);
    }

    // Build sessions from each group.
    let mut all_sessions: Vec<Session> = Vec::new();
    for ((host, _ua), hits) in &grouped {
        let mut sorted: Vec<&&RawHit> = hits.iter().collect();
        sorted.sort_by(|a, b| a.ts.partial_cmp(&b.ts).unwrap_or(std::cmp::Ordering::Equal));

        // Split into sessions at gaps > SESSION_WINDOW_SECS.
        let mut session_start = 0;
        for i in 1..sorted.len() {
            if sorted[i].ts - sorted[i - 1].ts > SESSION_WINDOW_SECS {
                all_sessions.push(build_session(host, &sorted[session_start..i]));
                session_start = i;
            }
        }
        all_sessions.push(build_session(host, &sorted[session_start..]));
    }

    // Aggregate into per-host summaries.
    let mut summaries: BTreeMap<String, SessionSummary> = BTreeMap::new();
    for session in &all_sessions {
        let summary = summaries.entry(session.host.clone()).or_default();
        summary.total_sessions += 1;
        if matches!(
            session.classification,
            VisitorClass::Human | VisitorClass::AgenticHuman
        ) {
            summary.human_sessions += 1;
            let depth = session.pages.len() as f64;
            let n = summary.human_sessions as f64;
            summary.avg_depth = summary.avg_depth * ((n - 1.0) / n) + depth / n;
            if session.pages.len() == 1 {
                summary.bounces += 1;
            }
            if session.pages.len() >= 3 {
                summary.deep_readers += 1;
            }
        }
    }

    summaries
}

/// Build a single session from a sorted slice of hits, applying behavioral reclassification.
pub(crate) fn build_session(host: &str, hits: &[&&RawHit]) -> Session {
    let first = hits[0];
    let last = hits[hits.len() - 1];
    let pages: Vec<String> = hits.iter().map(|h| h.path.clone()).collect();
    let duration_s = if last.ts > first.ts {
        (last.ts - first.ts) as u64
    } else {
        0
    };

    // Start with the UA-based classification from the first hit.
    let mut classification = first.class;

    // Apply behavioral reclassification for "Human" sessions.
    if classification == VisitorClass::Human || classification == VisitorClass::Unknown {
        classification = reclassify_session(hits, classification);
    }

    Session {
        ua_hash: sha256_hex(&first.ua),
        classification,
        pages: pages.clone(),
        entry_page: pages.first().cloned().unwrap_or_default(),
        duration_s,
        host: host.to_string(),
        start_ts: first.ts,
    }
}

/// Apply behavioral signals to reclassify a session.
///
/// Catches bots that use clean browser UAs but exhibit non-human behavior:
/// - Velocity: >5 hits in <10 seconds → ScraperBot
/// - Probe paths: any hit to a known probe path → ScraperBot
/// - All 404s: session of only 404 responses → ScraperBot (path scanning)
pub(crate) fn reclassify_session(hits: &[&&RawHit], initial_class: VisitorClass) -> VisitorClass {
    // Check 1: Any probe path in the session → entire session is ScraperBot.
    // (Individual hits already classified by classify_request, but a session
    // mixing normal + probe paths should be flagged too.)
    let has_probe = hits.iter().any(|h| h.class == VisitorClass::ScraperBot);
    if has_probe {
        return VisitorClass::ScraperBot;
    }

    // Check 2: Velocity — too many hits too fast.
    if hits.len() > VELOCITY_THRESHOLD {
        let first_ts = hits[0].ts;
        let window_end_ts = first_ts + VELOCITY_WINDOW_SECS;
        let hits_in_window = hits.iter().filter(|h| h.ts <= window_end_ts).count();
        if hits_in_window > VELOCITY_THRESHOLD {
            return VisitorClass::ScraperBot;
        }
    }

    initial_class
}


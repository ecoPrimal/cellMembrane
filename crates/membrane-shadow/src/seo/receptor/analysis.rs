// SPDX-License-Identifier: AGPL-3.0-or-later

//! Receptor analysis engine — builds reports from Caddy log entries.

use std::collections::BTreeMap;

use super::types::*;
use super::helpers::*;
use super::{VisitorClass, classify_request};

impl ReceptorReport {
    /// Create an empty report.
    pub(crate) fn empty() -> Self {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        Self {
            hosts: BTreeMap::new(),
            lines_processed: 0,
            parse_errors: 0,
            window_start: f64::MAX,
            window_end: 0.0,
            generated_at: now,
            sessions: BTreeMap::new(),
            raw_hits: Vec::new(),
        }
    }

    /// Test helper — same as `empty()` but publicly named for cross-module tests.
    #[cfg(test)]
    pub(crate) fn empty_for_test() -> Self {
        Self::empty()
    }

    /// Ingest a single parsed log entry into the report.
    pub(crate) fn ingest(&mut self, entry: &CaddyLogEntry) {
        self.lines_processed += 1;

        if entry.ts > 0.0 {
            if entry.ts < self.window_start {
                self.window_start = entry.ts;
            }
            if entry.ts > self.window_end {
                self.window_end = entry.ts;
            }
        }

        let ua = entry
            .request
            .headers
            .user_agent
            .first()
            .map_or("", String::as_str);
        let normalized = normalize_path(&entry.request.uri);
        let class = classify_request(ua, &normalized);

        let host_signal = self
            .hosts
            .entry(entry.request.host.clone())
            .or_insert_with(|| HostSignal {
                host: entry.request.host.clone(),
                ..Default::default()
            });

        host_signal.total_requests += 1;
        match class {
            VisitorClass::Human | VisitorClass::AgenticHuman => host_signal.total_human += 1,
            VisitorClass::SearchBot => host_signal.total_search_bot += 1,
            _ => {}
        }

        let page = host_signal
            .pages
            .entry(normalized.clone())
            .or_insert_with(|| PageSignal {
                path: normalized.clone(),
                ..Default::default()
            });

        page.total_hits += 1;
        match class {
            VisitorClass::Human | VisitorClass::AgenticHuman => page.human_hits += 1,
            VisitorClass::SearchBot => page.search_bot_hits += 1,
            VisitorClass::SocialBot => page.social_bot_hits += 1,
            VisitorClass::AiBot => page.ai_bot_hits += 1,
            VisitorClass::ScraperBot | VisitorClass::StealthFleet => {
                page.scraper_bot_hits += 1;
            }
            VisitorClass::MonitorBot | VisitorClass::GenericBot | VisitorClass::Unknown => {
                page.other_bot_hits += 1;
            }
        }

        match entry.status {
            200..=299 => page.ok_count += 1,
            300..=399 => page.redirect_count += 1,
            404 => page.not_found_count += 1,
            _ => {}
        }

        let duration_ms = entry.duration * 1000.0;
        let n = page.total_hits as f64;
        page.avg_duration_ms = page.avg_duration_ms * ((n - 1.0) / n) + duration_ms / n;

        // Collect raw hit for session grouping.
        self.raw_hits.push(RawHit {
            host: entry.request.host.clone(),
            path: normalized,
            ua: ua.to_string(),
            class,
            ts: entry.ts,
        });
    }

    /// Finalize crawl coverage counts and build session summaries.
    pub(crate) fn finalize(&mut self) {
        for host in self.hosts.values_mut() {
            host.unique_paths = u64::try_from(host.pages.len()).unwrap_or(u64::MAX);
            host.crawl_coverage = u64::try_from(
                host.pages
                    .values()
                    .filter(|p| p.search_bot_hits > 0)
                    .count(),
            )
            .unwrap_or(u64::MAX);
        }

        if self.window_start == f64::MAX {
            self.window_start = 0.0;
        }

        // Build session summaries from raw hits.
        self.sessions = build_session_summaries(&self.raw_hits);
    }

    /// Format the report as a human-readable summary.
    pub fn summary(&self) -> String {
        let mut lines = Vec::new();
        let window_hours = if self.window_end > self.window_start {
            (self.window_end - self.window_start) / 3600.0
        } else {
            0.0
        };

        lines.push(format!(
            "=== Receptor Report ({:.1}h window, {} lines) ===",
            window_hours, self.lines_processed
        ));
        if self.parse_errors > 0 {
            lines.push(format!("  parse errors: {}", self.parse_errors));
        }

        for (host, signal) in &self.hosts {
            lines.push(String::new());
            lines.push(format!("── {host} ──"));
            lines.push(format!(
                "  requests: {}  human: {}  search_bot: {}",
                signal.total_requests, signal.total_human, signal.total_search_bot
            ));
            lines.push(format!(
                "  paths: {}  crawl coverage: {}/{} ({:.0}%)",
                signal.unique_paths,
                signal.crawl_coverage,
                signal.unique_paths,
                if signal.unique_paths > 0 {
                    signal.crawl_coverage as f64 / signal.unique_paths as f64 * 100.0
                } else {
                    0.0
                }
            ));

            let mut pages: Vec<&PageSignal> = signal.pages.values().collect();
            pages.sort_by(|a, b| b.total_hits.cmp(&a.total_hits));

            // Session summary for this host.
            if let Some(sess) = self.sessions.get(host) {
                lines.push(format!(
                    "  sessions: {} total, {} human (avg depth {:.1}, {} bounces, {} deep readers)",
                    sess.total_sessions,
                    sess.human_sessions,
                    sess.avg_depth,
                    sess.bounces,
                    sess.deep_readers,
                ));
            }

            lines.push("  top pages:".into());
            for page in pages.iter().take(15) {
                let bot_indicator = if page.search_bot_hits > 0 {
                    "🔍"
                } else {
                    "  "
                };
                lines.push(format!(
                    "    {bot_indicator} {:<40} hits={:<5} human={:<4} bot={:<4} 404={}",
                    page.path,
                    page.total_hits,
                    page.human_hits,
                    page.search_bot_hits,
                    page.not_found_count,
                ));
            }
        }

        lines.join("\n")
    }

    /// Extract pages that search bots haven't crawled yet ("cold pages").
    ///
    /// These are candidates for higher IndexNow priority — if bots haven't
    /// found them, they need explicit notification.
    #[allow(dead_code)] // public API, wired when IndexNow priority scoring lands
    pub fn cold_pages(&self, host: &str) -> Vec<String> {
        self.hosts.get(host).map_or_else(Vec::new, |signal| {
            signal
                .pages
                .values()
                .filter(|p| p.search_bot_hits == 0 && p.human_hits > 0)
                .map(|p| p.path.clone())
                .collect()
        })
    }

    /// Extract pages with high human traffic but low bot coverage ("hot uncrawled").
    ///
    /// These should be critical priority for IndexNow — humans found them
    /// but search engines haven't indexed them yet.
    pub fn hot_uncrawled(&self, host: &str) -> Vec<String> {
        self.hosts.get(host).map_or_else(Vec::new, |signal| {
            let mut pages: Vec<&PageSignal> = signal
                .pages
                .values()
                .filter(|p| p.search_bot_hits == 0 && p.human_hits >= 3)
                .collect();
            pages.sort_by(|a, b| b.human_hits.cmp(&a.human_hits));
            pages.iter().map(|p| p.path.clone()).collect()
        })
    }
}

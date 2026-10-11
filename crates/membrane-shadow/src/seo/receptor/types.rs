// SPDX-License-Identifier: AGPL-3.0-or-later

//! Receptor data types — log entries, signals, sessions, reports.

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

use super::VisitorClass;

// ── Caddy Log Types ─────────────────────────────────────────────────

/// A single Caddy JSON access log entry.
///
/// Caddy's JSON log format emits one object per request. We only parse
/// the fields needed for SEO signal — no PII fields are retained.
#[derive(Debug, Clone, Deserialize)]
pub struct CaddyLogEntry {
    /// HTTP request details.
    pub request: CaddyRequest,
    /// HTTP response status code.
    pub status: u16,
    /// Response body size in bytes.
    #[allow(dead_code)] // deserialized from Caddy JSON, used for future bandwidth metrics
    #[serde(default)]
    pub size: u64,
    /// Request duration in seconds.
    #[serde(default)]
    pub duration: f64,
    /// Unix timestamp (fractional seconds).
    #[serde(default)]
    pub ts: f64,
}

/// HTTP request details from Caddy log.
#[derive(Debug, Clone, Deserialize)]
pub struct CaddyRequest {
    /// Client IP (will be hashed, never stored raw).
    #[allow(dead_code)] // deserialized from Caddy JSON, hashed elsewhere
    #[serde(default, alias = "remote_ip")]
    pub remote_ip: String,
    /// Requested hostname.
    #[serde(default)]
    pub host: String,
    /// Request URI path.
    #[serde(default)]
    pub uri: String,
    /// HTTP method (GET, POST, etc.).
    #[allow(dead_code)] // deserialized from Caddy JSON, needed for request classification
    #[serde(default)]
    pub method: String,
    /// Request headers (for User-Agent extraction).
    #[serde(default)]
    pub headers: CaddyHeaders,
}

/// Request headers — only User-Agent is extracted.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct CaddyHeaders {
    /// User-Agent header values (Caddy stores as array).
    #[serde(default, rename = "User-Agent")]
    pub user_agent: Vec<String>,
}

// ── Signal Aggregation ──────────────────────────────────────────────

/// Aggregated signal for a single page (URI path) on a single host.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PageSignal {
    /// URI path (e.g. `/evidence/`, `/network/dpsc/`).
    pub path: String,
    /// Total requests.
    pub total_hits: u64,
    /// Human visits.
    pub human_hits: u64,
    /// Search bot crawls.
    pub search_bot_hits: u64,
    /// Social bot previews.
    pub social_bot_hits: u64,
    /// AI bot crawls.
    pub ai_bot_hits: u64,
    /// Scraper/recon bot hits (credential scanners, vuln probes).
    #[serde(default)]
    pub scraper_bot_hits: u64,
    /// Other bot hits (monitor + generic).
    pub other_bot_hits: u64,
    /// HTTP 200 responses.
    pub ok_count: u64,
    /// HTTP 404 responses.
    pub not_found_count: u64,
    /// HTTP 3xx responses (redirects).
    pub redirect_count: u64,
    /// Average response time in milliseconds.
    pub avg_duration_ms: f64,
}

/// Per-host signal summary.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HostSignal {
    /// Hostname (e.g. `sporeprint.primals.eco`).
    pub host: String,
    /// Per-page signal map (path → signal).
    pub pages: BTreeMap<String, PageSignal>,
    /// Total requests across all pages.
    pub total_requests: u64,
    /// Total human visits.
    pub total_human: u64,
    /// Total search bot crawls.
    pub total_search_bot: u64,
    /// Unique paths crawled by search bots (crawl coverage).
    pub crawl_coverage: u64,
    /// Total unique paths seen.
    pub unique_paths: u64,
}

// ── Session Detection ───────────────────────────────────────────────

/// A detected visitor session (same UA within a time window).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Session {
    /// SHA-256 hash of the User-Agent string (never stored raw).
    pub ua_hash: String,
    /// Visitor classification for this session.
    pub classification: VisitorClass,
    /// Ordered navigation path (pages visited in sequence).
    pub pages: Vec<String>,
    /// First page hit (entry page — correlates to which link was clicked).
    pub entry_page: String,
    /// Session duration in seconds (last hit - first hit).
    pub duration_s: u64,
    /// Host this session was on.
    pub host: String,
    /// Session start timestamp (epoch seconds).
    pub start_ts: f64,
}

/// Per-host session summary (aggregated from raw sessions).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SessionSummary {
    /// Total sessions detected.
    pub total_sessions: u64,
    /// Human sessions.
    pub human_sessions: u64,
    /// Average pages per human session (navigation depth).
    pub avg_depth: f64,
    /// Sessions with only 1 page hit (bounces).
    pub bounces: u64,
    /// Sessions with 3+ page hits (deep readers).
    pub deep_readers: u64,
}

/// Raw hit record for session grouping (internal, not serialized in report).
#[derive(Debug, Clone)]
pub(crate) struct RawHit {
    pub(crate) host: String,
    pub(crate) path: String,
    pub(crate) ua: String,
    pub(crate) class: VisitorClass,
    pub(crate) ts: f64,
}

/// Complete receptor report across all hosts.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReceptorReport {
    /// Per-host signal summaries.
    pub hosts: BTreeMap<String, HostSignal>,
    /// Log lines processed.
    pub lines_processed: u64,
    /// Log lines that failed to parse.
    pub parse_errors: u64,
    /// Time window: earliest log timestamp (epoch seconds).
    pub window_start: f64,
    /// Time window: latest log timestamp (epoch seconds).
    pub window_end: f64,
    /// Report generation timestamp (epoch seconds).
    pub generated_at: u64,
    /// Per-host session summaries (populated during finalize).
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub sessions: BTreeMap<String, SessionSummary>,
    /// Raw hits for session grouping (not serialized).
    #[serde(skip)]
    pub(crate) raw_hits: Vec<RawHit>,
}

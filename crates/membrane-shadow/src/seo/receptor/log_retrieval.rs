// SPDX-License-Identifier: AGPL-3.0-or-later

//! Log retrieval and analysis dispatch.

use std::collections::BTreeMap;
use tracing::{debug, info};
use serde_json::Value;

use crate::error::Result;
use super::types::*;
use super::helpers::*;
use super::{VisitorClass, classify_visitor};

// ── Log Retrieval + Parsing ─────────────────────────────────────────

/// Default number of Caddy log lines to analyze.
const DEFAULT_LOG_LINES: u32 = 5000;

/// Caddy access log path on golgiBody.
const CADDY_LOG_PATH: &str = "/var/log/caddy/access.log";

/// Rotated log file (uncompressed, previous rotation).
const CADDY_LOG_ROTATED: &str = "/var/log/caddy/access.log.1";

/// Compressed rotated log file (rotation before previous).
const CADDY_LOG_ROTATED_GZ: &str = "/var/log/caddy/access.log.2.gz";

/// Build an SSH command that reads across log rotation boundaries.
///
/// Combines current + rotated logs (newest last) so `tail -n N` gets
/// the most recent N lines regardless of when rotation happened.
///
/// Without `include_rotated`, reads only the current log file.
pub(crate) fn build_log_command(lines: u32, include_rotated: bool) -> String {
    if include_rotated {
        // Cat rotated files (oldest first) + current, then tail.
        // .2.gz needs zcat; .1 and current are plain text.
        // Use subshell with conditional existence checks.
        format!(
            "{{ [ -f {CADDY_LOG_ROTATED_GZ} ] && zcat {CADDY_LOG_ROTATED_GZ} 2>/dev/null; \
             [ -f {CADDY_LOG_ROTATED} ] && cat {CADDY_LOG_ROTATED} 2>/dev/null; \
             cat {CADDY_LOG_PATH} 2>/dev/null; }} | tail -n {lines}"
        )
    } else {
        format!("tail -n {lines} {CADDY_LOG_PATH} 2>/dev/null")
    }
}

/// Retrieve and analyze Caddy access logs from golgiBody via SSH.
///
/// Fetches the last `lines` entries from the Caddy JSON access log,
/// parses each into a [`CaddyLogEntry`], classifies visitors, and
/// aggregates into a [`ReceptorReport`].
///
/// When `include_rotated` is true, reads across rotation boundaries
/// (`access.log.1` and `access.log.2.gz`) to prevent data loss during
/// Caddy reloads.
pub async fn analyze(config: &crate::ShadowConfig, lines: u32) -> Result<ReceptorReport> {
    analyze_opts(config, lines, false).await
}

/// Analyze with full options including rotated log support.
pub async fn analyze_opts(
    config: &crate::ShadowConfig,
    lines: u32,
    include_rotated: bool,
) -> Result<ReceptorReport> {
    let cmd = build_log_command(lines, include_rotated);
    let raw_output = crate::ssh::exec(config, &cmd).await?;

    let mut report = ReceptorReport::empty();

    for line in raw_output.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        match serde_json::from_str::<CaddyLogEntry>(trimmed) {
            Ok(entry) => {
                if crate::seo::PUBLISH_SITES
                    .iter()
                    .any(|s| s.host == entry.request.host)
                {
                    report.ingest(&entry);
                }
            }
            Err(e) => {
                report.parse_errors += 1;
                debug!(error = %e, "receptor: failed to parse log line");
            }
        }
    }

    report.finalize();

    info!(
        lines_processed = report.lines_processed,
        parse_errors = report.parse_errors,
        hosts = report.hosts.len(),
        "receptor analysis complete"
    );

    Ok(report)
}

/// Analyze logs filtered to a specific host.
pub async fn analyze_host(
    config: &crate::ShadowConfig,
    host: &str,
    lines: u32,
    include_rotated: bool,
) -> Result<ReceptorReport> {
    let source = if include_rotated {
        format!(
            "{{ [ -f {CADDY_LOG_ROTATED_GZ} ] && zcat {CADDY_LOG_ROTATED_GZ} 2>/dev/null; \
             [ -f {CADDY_LOG_ROTATED} ] && cat {CADDY_LOG_ROTATED} 2>/dev/null; \
             cat {CADDY_LOG_PATH} 2>/dev/null; }}"
        )
    } else {
        format!("cat {CADDY_LOG_PATH} 2>/dev/null")
    };
    let cmd = format!("{source} | grep '\"host\":\"{host}\"' | tail -n {lines}");
    let raw_output = crate::ssh::exec(config, &cmd).await?;

    let mut report = ReceptorReport::empty();

    for line in raw_output.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        match serde_json::from_str::<CaddyLogEntry>(trimmed) {
            Ok(entry) => report.ingest(&entry),
            Err(e) => {
                report.parse_errors += 1;
                debug!(error = %e, "receptor: failed to parse log line");
            }
        }
    }

    report.finalize();
    Ok(report)
}

// ── Dispatch Entry Points ───────────────────────────────────────────

/// Dispatch `seo.receptor` commands.
pub async fn dispatch(config: &crate::ShadowConfig, args: &[&str]) -> Result<crate::ShadowOutcome> {
    let lines = args
        .iter()
        .position(|a| *a == "--lines")
        .and_then(|i| args.get(i + 1))
        .and_then(|v| v.parse::<u32>().ok())
        .unwrap_or(DEFAULT_LOG_LINES);

    let host_filter = args
        .iter()
        .position(|a| *a == "--host")
        .and_then(|i| args.get(i + 1).copied());

    let with_feedback = args.contains(&"--feedback");
    let include_rotated = args.contains(&"--include-rotated");

    if with_feedback {
        let report = analyze_opts(config, lines, include_rotated).await?;
        let feedback: Vec<(String, Vec<String>)> = crate::seo::PUBLISH_SITES
            .iter()
            .filter_map(|site| {
                let hot = report.hot_uncrawled(site.host);
                if hot.is_empty() {
                    None
                } else {
                    let urls: Vec<String> = hot
                        .iter()
                        .map(|path| format!("https://{}{path}", site.host))
                        .collect();
                    Some((site.host.to_string(), urls))
                }
            })
            .collect();
        let mut msg = report.summary();

        if !feedback.is_empty() {
            msg.push_str("\n\n=== IndexNow Feedback ===");
            for (host, urls) in &feedback {
                msg.push_str(&format!("\n  {host}: {} hot uncrawled pages", urls.len()));
                for url in urls.iter().take(10) {
                    msg.push_str(&format!("\n    → {url}"));
                }
                if urls.len() > 10 {
                    msg.push_str(&format!("\n    ... and {} more", urls.len() - 10));
                }
            }
        }

        Ok(crate::ShadowOutcome::ok_with(
            msg,
            serde_json::json!({
                "report": report,
                "feedback": feedback,
            }),
        ))
    } else if let Some(host) = host_filter {
        let report = analyze_host(config, host, lines, include_rotated).await?;
        Ok(crate::ShadowOutcome::ok_with(
            report.summary(),
            serde_json::to_value(&report)?,
        ))
    } else {
        let report = analyze_opts(config, lines, include_rotated).await?;
        Ok(crate::ShadowOutcome::ok_with(
            report.summary(),
            serde_json::to_value(&report)?,
        ))
    }
}

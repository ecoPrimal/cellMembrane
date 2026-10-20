// SPDX-License-Identifier: AGPL-3.0-or-later

//! Inbound signal receptor — Caddy log analytics without surveillance.
//!
//! The membrane secretes (IndexNow, GSC, GitHub mirror) but needs to sense
//! what happens after secretion. This module closes the loop:
//!
//! ```text
//! content → zola → Caddy serves → sitemap → IndexNow → GSC
//!    ↑                  ↓                                 ↓
//!    └── seo.adapt ← receptor ← Caddy logs ← crawler visits
//! ```
//!
//! ## Design Principles
//!
//! - **No third-party analytics**. Caddy JSON logs are the only source.
//! - **Self-hosted, log-based**. No cookies, no tracking pixels, no JS.
//! - **Bot/human separation**. Bots = crawl coverage map. Humans = engagement.
//! - **Privacy-preserving**. IPs are hashed, no PII stored, no fingerprinting.
//! - **Feeds back into publish decisions**. Which pages need IndexNow priority?

pub mod types;
pub mod analysis;
pub mod helpers;
pub mod log_retrieval;

pub use types::*;
pub use log_retrieval::*;



#[allow(unused_imports)]
pub use cellmembrane_types::visitor::{
    PROBE_PREFIXES, SESSION_WINDOW_SECS, VELOCITY_THRESHOLD, VELOCITY_WINDOW_SECS, VisitorClass,
    classify_path, classify_request, classify_visitor,
};

#[cfg(test)]
#[path = "tests.rs"]
mod tests;

// SPDX-License-Identifier: AGPL-3.0-or-later

//! Shared ecosystem types — the agglutinated canonical forms.
//!
//! These types existed as 250+ independent copies across 16 organisms.
//! Each organism reinvented `HealthStatus`, `JsonRpcRequest`, `ServiceInfo`,
//! `DiscoveryConfig`, and `SecurityLevel` with slight variations.
//!
//! This module is the canonical source. Import from here; stop copying.
//!
//! # Design choices
//!
//! - `String` (not `Arc<str>`) — most consumers don't need zero-copy;
//!   organisms that do (squirrel, toadStool) can wrap at their boundary.
//! - `serde_json::Value` for JSON-RPC params — maximum compatibility.
//! - No async, no network I/O — pure data types.
//! - `Default` impls where sensible.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt;

// ═══════════════════════════════════════════════════════════════════════
// HEALTH STATUS — was 30+ copies
//
// Agglutinated from:
//   toadStool/integration/protocols (richest: uptime, utilization, workloads)
//   biomeOS/biomeos-atomic-deploy (socket-level: latency, message)
//   bearDog/beardog-types/crypto_service (HSM-aware: hsm_connected)
//
// The unified form keeps: healthy, message, uptime_secs, checks (vec),
// and an extensible `details` map for organism-specific fields.
// ═══════════════════════════════════════════════════════════════════════

/// Health status of a service or component.
///
/// Every organism reports health. This is the shared wire format.
/// Organism-specific metrics go in `details`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    /// Overall health flag — the one bit every consumer needs.
    pub healthy: bool,

    /// Human-readable status or error message.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,

    /// Uptime in seconds (0 if unknown).
    #[serde(default)]
    pub uptime_secs: u64,

    /// Individual health checks (empty = no sub-checks).
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub checks: Vec<HealthCheck>,

    /// Extensible key-value details.
    /// Use for: resource_utilization, active_workloads, hsm_connected,
    /// latency_ms, socket_exists, etc.
    #[serde(default, skip_serializing_if = "HashMap::is_empty")]
    pub details: HashMap<String, serde_json::Value>,
}

/// Individual health check result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthCheck {
    /// Check name (e.g. "database", "rpc", "disk").
    pub name: String,
    /// Whether this check passed.
    pub passed: bool,
    /// Optional detail message.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
    /// Latency of this check in milliseconds.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub latency_ms: Option<u64>,
}

impl Default for HealthStatus {
    fn default() -> Self {
        Self {
            healthy: true,
            message: None,
            uptime_secs: 0,
            checks: Vec::new(),
            details: HashMap::new(),
        }
    }
}

impl HealthStatus {
    /// Healthy with no details.
    #[must_use]
    pub fn ok() -> Self {
        Self::default()
    }

    /// Unhealthy with a message.
    #[must_use]
    pub fn sick(message: impl Into<String>) -> Self {
        Self {
            healthy: false,
            message: Some(message.into()),
            ..Self::default()
        }
    }

    /// Set uptime.
    #[must_use]
    pub fn with_uptime(mut self, secs: u64) -> Self {
        self.uptime_secs = secs;
        self
    }

    /// Add a detail.
    #[must_use]
    pub fn with_detail(mut self, key: impl Into<String>, value: impl Into<serde_json::Value>) -> Self {
        self.details.insert(key.into(), value.into());
        self
    }

    /// Add a health check.
    #[must_use]
    pub fn with_check(mut self, check: HealthCheck) -> Self {
        if !check.passed {
            self.healthy = false;
        }
        self.checks.push(check);
        self
    }

    /// Re-derive `healthy` from checks (all must pass).
    pub fn recompute_healthy(&mut self) {
        if self.checks.is_empty() {
            return;
        }
        self.healthy = self.checks.iter().all(|c| c.passed);
    }
}

impl fmt::Display for HealthStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.healthy {
            write!(f, "healthy")?;
        } else {
            write!(f, "UNHEALTHY")?;
        }
        if let Some(msg) = &self.message {
            write!(f, ": {msg}")?;
        }
        if self.uptime_secs > 0 {
            write!(f, " (up {}s)", self.uptime_secs)?;
        }
        Ok(())
    }
}

// ═══════════════════════════════════════════════════════════════════════
// JSON-RPC 2.0 — was 25+ copies
//
// Agglutinated from:
//   toadStool/runtime/container (clean, standard-compliant)
//   barraCuda/barracuda-core/ipc (domain.operation format)
//   biomeOS/biomeos-types/jsonrpc (straightforward)
//
// Follows the JSON-RPC 2.0 specification exactly.
// ═══════════════════════════════════════════════════════════════════════

/// JSON-RPC 2.0 request.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcRequest {
    /// Protocol version — always "2.0".
    pub jsonrpc: String,

    /// Method name (e.g. `"health.check"`, `"primal.register"`).
    pub method: String,

    /// Parameters (positional array or named object). None for no params.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub params: Option<serde_json::Value>,

    /// Request ID for correlation. None for notifications (no response expected).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub id: Option<serde_json::Value>,
}

/// JSON-RPC 2.0 response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcResponse {
    /// Protocol version — always "2.0".
    pub jsonrpc: String,

    /// Result on success. Mutually exclusive with `error`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,

    /// Error on failure. Mutually exclusive with `result`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub error: Option<JsonRpcError>,

    /// Request ID this response corresponds to.
    pub id: serde_json::Value,
}

/// JSON-RPC 2.0 error object.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct JsonRpcError {
    /// Error code (negative for protocol errors, positive for application).
    /// `i32` matches the overwhelming ecosystem convention and JSON-RPC spec.
    pub code: i32,

    /// Short description.
    pub message: String,

    /// Optional structured data about the error.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub data: Option<serde_json::Value>,
}

impl JsonRpcRequest {
    /// Create a new request.
    #[must_use]
    pub fn new(method: impl Into<String>, params: Option<serde_json::Value>, id: impl Into<serde_json::Value>) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            method: method.into(),
            params,
            id: Some(id.into()),
        }
    }

    /// Create a notification (no ID, no response expected).
    #[must_use]
    pub fn notification(method: impl Into<String>, params: Option<serde_json::Value>) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            method: method.into(),
            params,
            id: None,
        }
    }

    /// Is this a notification? (no id)
    #[must_use]
    pub fn is_notification(&self) -> bool {
        self.id.is_none()
    }
}

impl JsonRpcResponse {
    /// Create a success response.
    #[must_use]
    pub fn success(id: serde_json::Value, result: serde_json::Value) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            result: Some(result),
            error: None,
            id,
        }
    }

    /// Create an error response.
    #[must_use]
    pub fn error(id: serde_json::Value, code: i32, message: impl Into<String>) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            result: None,
            error: Some(JsonRpcError {
                code,
                message: message.into(),
                data: None,
            }),
            id,
        }
    }

    /// Is this a success response?
    #[must_use]
    pub fn is_success(&self) -> bool {
        self.result.is_some()
    }
}

impl JsonRpcError {
    // Standard JSON-RPC 2.0 error codes

    /// Parse error — invalid JSON received.
    pub const PARSE_ERROR: i32 = -32700;
    /// Invalid request — not a valid JSON-RPC request.
    pub const INVALID_REQUEST: i32 = -32600;
    /// Method not found.
    pub const METHOD_NOT_FOUND: i32 = -32601;
    /// Invalid params.
    pub const INVALID_PARAMS: i32 = -32602;
    /// Internal error.
    pub const INTERNAL_ERROR: i32 = -32603;
}

impl fmt::Display for JsonRpcError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "[{}] {}", self.code, self.message)
    }
}

impl std::error::Error for JsonRpcError {}

// ═══════════════════════════════════════════════════════════════════════
// SERVICE INFO — was 30+ copies
//
// Agglutinated from:
//   squirrel/universal_adapters/registry (richest: capabilities, health)
//   toadStool/auto_config/ecosystem_types (endpoint, version, capabilities)
//   toadStool/integration/protocols (endpoints vec, Arc<str>)
//
// Unified: id, name, version, endpoints, capabilities, status, metadata.
// ═══════════════════════════════════════════════════════════════════════

/// Information about a running service in the ecosystem.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceInfo {
    /// Unique service identifier.
    pub id: String,

    /// Human-readable service name.
    pub name: String,

    /// Service version string.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub version: Option<String>,

    /// Endpoint URLs (unix sockets, TCP, etc.).
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub endpoints: Vec<String>,

    /// Capabilities this service provides.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub capabilities: Vec<String>,

    /// Current service status.
    #[serde(default)]
    pub status: ServiceStatus,

    /// Optional key-value metadata.
    #[serde(default, skip_serializing_if = "HashMap::is_empty")]
    pub metadata: HashMap<String, String>,
}

/// Service operational status.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ServiceStatus {
    /// Service is running normally.
    #[default]
    Running,
    /// Service is starting up.
    Starting,
    /// Service is stopped.
    Stopped,
    /// Service is degraded (partially working).
    Degraded,
    /// Service has errored.
    Error,
    /// Status is unknown.
    Unknown,
}

impl fmt::Display for ServiceStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Running => write!(f, "running"),
            Self::Starting => write!(f, "starting"),
            Self::Stopped => write!(f, "stopped"),
            Self::Degraded => write!(f, "degraded"),
            Self::Error => write!(f, "error"),
            Self::Unknown => write!(f, "unknown"),
        }
    }
}

impl ServiceInfo {
    /// Create minimal service info.
    #[must_use]
    pub fn new(id: impl Into<String>, name: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            name: name.into(),
            version: None,
            endpoints: Vec::new(),
            capabilities: Vec::new(),
            status: ServiceStatus::Running,
            metadata: HashMap::new(),
        }
    }

    /// Builder: add an endpoint.
    #[must_use]
    pub fn with_endpoint(mut self, endpoint: impl Into<String>) -> Self {
        self.endpoints.push(endpoint.into());
        self
    }

    /// Builder: add a capability.
    #[must_use]
    pub fn with_capability(mut self, cap: impl Into<String>) -> Self {
        self.capabilities.push(cap.into());
        self
    }

    /// Builder: set version.
    #[must_use]
    pub fn with_version(mut self, version: impl Into<String>) -> Self {
        self.version = Some(version.into());
        self
    }

    /// Is this service operational?
    #[must_use]
    pub fn is_healthy(&self) -> bool {
        matches!(self.status, ServiceStatus::Running | ServiceStatus::Starting)
    }
}

// ═══════════════════════════════════════════════════════════════════════
// DISCOVERY CONFIG — was 30+ copies
//
// Agglutinated from:
//   toadStool/core/toadstool/discovery (interval, timeout, max_services)
//   toadStool/core/common/primal_discovery_complete (cache_ttl, fallbacks)
//   toadStool/core/config/primal_capabilities (methods, cache, retry)
//
// Unified: methods, intervals, timeouts, cache, fallbacks.
// ═══════════════════════════════════════════════════════════════════════

/// Configuration for service discovery.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiscoveryConfig {
    /// Discovery methods in priority order (e.g. `["mdns", "dns_sd", "env"]`).
    #[serde(default = "DiscoveryConfig::default_methods")]
    pub methods: Vec<String>,

    /// How often to refresh discovery (seconds).
    #[serde(default = "DiscoveryConfig::default_interval_secs")]
    pub interval_secs: u64,

    /// Mark a service stale after this many seconds without heartbeat.
    #[serde(default = "DiscoveryConfig::default_timeout_secs")]
    pub timeout_secs: u64,

    /// Maximum services to track.
    #[serde(default = "DiscoveryConfig::default_max_services")]
    pub max_services: usize,

    /// Enable discovery caching.
    #[serde(default = "crate::default_true")]
    pub cache_enabled: bool,

    /// Cache TTL in seconds.
    #[serde(default = "DiscoveryConfig::default_cache_ttl_secs")]
    pub cache_ttl_secs: u64,

    /// Retry attempts on discovery failure.
    #[serde(default = "DiscoveryConfig::default_retries")]
    pub retries: u32,

    /// Enable IPv6 discovery.
    #[serde(default)]
    pub enable_ipv6: bool,

    /// Fallback endpoints by capability name.
    #[serde(default, skip_serializing_if = "HashMap::is_empty")]
    pub fallbacks: HashMap<String, String>,
}

impl Default for DiscoveryConfig {
    fn default() -> Self {
        Self {
            methods: Self::default_methods(),
            interval_secs: Self::default_interval_secs(),
            timeout_secs: Self::default_timeout_secs(),
            max_services: Self::default_max_services(),
            cache_enabled: true,
            cache_ttl_secs: Self::default_cache_ttl_secs(),
            retries: Self::default_retries(),
            enable_ipv6: false,
            fallbacks: HashMap::new(),
        }
    }
}

impl DiscoveryConfig {
    fn default_methods() -> Vec<String> {
        vec!["mdns".into(), "env".into()]
    }
    const fn default_interval_secs() -> u64 { 30 }
    const fn default_timeout_secs() -> u64 { 300 }
    const fn default_max_services() -> usize { 100 }
    const fn default_cache_ttl_secs() -> u64 { 60 }
    const fn default_retries() -> u32 { 3 }
}

// ═══════════════════════════════════════════════════════════════════════
// SECURITY LEVEL — was 32+ copies
//
// Agglutinated from:
//   toadStool/distributed/crypto_integration (Standard→QuantumResistant)
//   toadStool/runtime/wasm (None→Maximum with behavior methods)
//   bearDog/beardog-types (HSM operational levels)
//
// 5-tier scale: None < Standard < High < Maximum < QuantumResistant.
// Maps to all the variants organisms used (Basic=Standard, Enhanced=High,
// HardwareSecured=Maximum, Strict=High, Critical=Maximum, Low=Standard).
// ═══════════════════════════════════════════════════════════════════════

/// Security level for cryptographic operations and access control.
///
/// Ordered from least to most restrictive. Each level implies all
/// protections of the levels below it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SecurityLevel {
    /// No security enforcement (testing only, never in production).
    None,

    /// Software-based cryptography, standard protections.
    /// Aliases: Basic, Low.
    #[default]
    Standard,

    /// Stronger policies, hardware recommended but not required.
    /// Aliases: Enhanced, Strict.
    High,

    /// Hardware-backed security required (HSM, TPM, secure enclave).
    /// Aliases: Critical, `HardwareSecured`.
    Maximum,

    /// Quantum-resistant algorithms required.
    /// Post-quantum key exchange and signatures.
    QuantumResistant,
}

impl SecurityLevel {
    /// Does this level require hardware-backed key storage?
    #[must_use]
    pub const fn requires_hardware(&self) -> bool {
        matches!(self, Self::Maximum | Self::QuantumResistant)
    }

    /// Does this level enforce memory limits on sandboxed code?
    #[must_use]
    pub const fn enforces_memory_limits(&self) -> bool {
        matches!(self, Self::High | Self::Maximum | Self::QuantumResistant)
    }

    /// Is this level safe for production?
    #[must_use]
    pub const fn is_production_safe(&self) -> bool {
        !matches!(self, Self::None)
    }

    /// Minimum TLS version for this security level.
    #[must_use]
    pub const fn min_tls_version(&self) -> &str {
        match self {
            Self::None | Self::Standard => "1.2",
            Self::High | Self::Maximum | Self::QuantumResistant => "1.3",
        }
    }
}

impl fmt::Display for SecurityLevel {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::None => write!(f, "none"),
            Self::Standard => write!(f, "standard"),
            Self::High => write!(f, "high"),
            Self::Maximum => write!(f, "maximum"),
            Self::QuantumResistant => write!(f, "quantum_resistant"),
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════
// TESTS
// ═══════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    // ── HealthStatus ──

    #[test]
    fn test_health_ok() {
        let h = HealthStatus::ok();
        assert!(h.healthy);
        assert!(h.message.is_none());
    }

    #[test]
    fn test_health_sick() {
        let h = HealthStatus::sick("database down");
        assert!(!h.healthy);
        assert_eq!(h.message.as_deref(), Some("database down"));
    }

    #[test]
    fn test_health_with_checks() {
        let h = HealthStatus::ok()
            .with_check(HealthCheck { name: "db".into(), passed: true, message: None, latency_ms: Some(5) })
            .with_check(HealthCheck { name: "rpc".into(), passed: false, message: Some("timeout".into()), latency_ms: Some(5000) });
        assert!(!h.healthy); // rpc failed → unhealthy
        assert_eq!(h.checks.len(), 2);
    }

    #[test]
    fn test_health_recompute() {
        let mut h = HealthStatus::ok()
            .with_check(HealthCheck { name: "a".into(), passed: true, message: None, latency_ms: None })
            .with_check(HealthCheck { name: "b".into(), passed: true, message: None, latency_ms: None });
        h.healthy = false; // manually broken
        h.recompute_healthy();
        assert!(h.healthy); // all checks pass → healthy
    }

    #[test]
    fn test_health_with_details() {
        let h = HealthStatus::ok()
            .with_uptime(3600)
            .with_detail("hsm_connected", true)
            .with_detail("active_workloads", 7);
        assert_eq!(h.uptime_secs, 3600);
        assert_eq!(h.details.get("hsm_connected").and_then(|v| v.as_bool()), Some(true));
        assert_eq!(h.details.get("active_workloads").and_then(|v| v.as_i64()), Some(7));
    }

    #[test]
    fn test_health_display() {
        let h = HealthStatus::sick("oom").with_uptime(42);
        let s = h.to_string();
        assert!(s.contains("UNHEALTHY"));
        assert!(s.contains("oom"));
        assert!(s.contains("42s"));
    }

    #[test]
    fn test_health_serde_roundtrip() {
        let h = HealthStatus::ok()
            .with_uptime(100)
            .with_check(HealthCheck { name: "x".into(), passed: true, message: None, latency_ms: Some(1) });
        let json = serde_json::to_string(&h).unwrap();
        let h2: HealthStatus = serde_json::from_str(&json).unwrap();
        assert_eq!(h2.healthy, h.healthy);
        assert_eq!(h2.uptime_secs, 100);
        assert_eq!(h2.checks.len(), 1);
    }

    // ── JSON-RPC ──

    #[test]
    fn test_jsonrpc_request_new() {
        let req = JsonRpcRequest::new("health.check", None, 1);
        assert_eq!(req.jsonrpc, "2.0");
        assert_eq!(req.method, "health.check");
        assert!(!req.is_notification());
    }

    #[test]
    fn test_jsonrpc_notification() {
        let n = JsonRpcRequest::notification("log.append", Some(serde_json::json!({"level": "info"})));
        assert!(n.is_notification());
        assert!(n.params.is_some());
    }

    #[test]
    fn test_jsonrpc_response_success() {
        let r = JsonRpcResponse::success(serde_json::json!(1), serde_json::json!({"status": "ok"}));
        assert!(r.is_success());
        assert!(r.error.is_none());
    }

    #[test]
    fn test_jsonrpc_response_error() {
        let r = JsonRpcResponse::error(serde_json::json!(1), JsonRpcError::METHOD_NOT_FOUND, "no such method");
        assert!(!r.is_success());
        assert_eq!(r.error.as_ref().unwrap().code, -32601);
    }

    #[test]
    fn test_jsonrpc_error_display() {
        let e = JsonRpcError { code: -32700, message: "parse error".into(), data: None };
        assert_eq!(e.to_string(), "[-32700] parse error");
    }

    #[test]
    fn test_jsonrpc_serde_roundtrip() {
        let req = JsonRpcRequest::new("test", Some(serde_json::json!([1,2,3])), "abc");
        let json = serde_json::to_string(&req).unwrap();
        let req2: JsonRpcRequest = serde_json::from_str(&json).unwrap();
        assert_eq!(req2.method, "test");
        assert_eq!(req2.id, Some(serde_json::json!("abc")));
    }

    // ── ServiceInfo ──

    #[test]
    fn test_service_info_new() {
        let s = ServiceInfo::new("beardog-1", "bearDog")
            .with_version("0.10.0")
            .with_endpoint("unix:///run/membrane/beardog.sock")
            .with_capability("security");
        assert_eq!(s.id, "beardog-1");
        assert!(s.is_healthy());
        assert_eq!(s.endpoints.len(), 1);
        assert_eq!(s.capabilities, vec!["security"]);
    }

    #[test]
    fn test_service_status_display() {
        assert_eq!(ServiceStatus::Running.to_string(), "running");
        assert_eq!(ServiceStatus::Degraded.to_string(), "degraded");
    }

    #[test]
    fn test_service_health_check() {
        let mut s = ServiceInfo::new("x", "X");
        assert!(s.is_healthy());
        s.status = ServiceStatus::Error;
        assert!(!s.is_healthy());
        s.status = ServiceStatus::Degraded;
        assert!(!s.is_healthy());
        s.status = ServiceStatus::Starting;
        assert!(s.is_healthy());
    }

    #[test]
    fn test_service_serde_roundtrip() {
        let s = ServiceInfo::new("s1", "svc")
            .with_endpoint("tcp://127.0.0.1:8080")
            .with_capability("compute");
        let json = serde_json::to_string(&s).unwrap();
        let s2: ServiceInfo = serde_json::from_str(&json).unwrap();
        assert_eq!(s2.id, "s1");
        assert_eq!(s2.endpoints, vec!["tcp://127.0.0.1:8080"]);
    }

    // ── DiscoveryConfig ──

    #[test]
    fn test_discovery_config_defaults() {
        let d = DiscoveryConfig::default();
        assert_eq!(d.methods, vec!["mdns", "env"]);
        assert_eq!(d.interval_secs, 30);
        assert_eq!(d.timeout_secs, 300);
        assert_eq!(d.max_services, 100);
        assert!(d.cache_enabled);
        assert_eq!(d.retries, 3);
    }

    #[test]
    fn test_discovery_config_serde_roundtrip() {
        let d = DiscoveryConfig {
            methods: vec!["dns_sd".into()],
            enable_ipv6: true,
            ..Default::default()
        };
        let json = serde_json::to_string(&d).unwrap();
        let d2: DiscoveryConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(d2.methods, vec!["dns_sd"]);
        assert!(d2.enable_ipv6);
    }

    #[test]
    fn test_discovery_config_deserialize_minimal() {
        // Should work with just `{}` — all fields have defaults
        let d: DiscoveryConfig = serde_json::from_str("{}").unwrap();
        assert_eq!(d.interval_secs, 30);
        assert!(d.cache_enabled);
    }

    // ── SecurityLevel ──

    #[test]
    fn test_security_level_ordering() {
        assert!(SecurityLevel::None < SecurityLevel::Standard);
        assert!(SecurityLevel::Standard < SecurityLevel::High);
        assert!(SecurityLevel::High < SecurityLevel::Maximum);
        assert!(SecurityLevel::Maximum < SecurityLevel::QuantumResistant);
    }

    #[test]
    fn test_security_level_default() {
        assert_eq!(SecurityLevel::default(), SecurityLevel::Standard);
    }

    #[test]
    fn test_security_requires_hardware() {
        assert!(!SecurityLevel::Standard.requires_hardware());
        assert!(!SecurityLevel::High.requires_hardware());
        assert!(SecurityLevel::Maximum.requires_hardware());
        assert!(SecurityLevel::QuantumResistant.requires_hardware());
    }

    #[test]
    fn test_security_production_safe() {
        assert!(!SecurityLevel::None.is_production_safe());
        assert!(SecurityLevel::Standard.is_production_safe());
        assert!(SecurityLevel::QuantumResistant.is_production_safe());
    }

    #[test]
    fn test_security_tls_version() {
        assert_eq!(SecurityLevel::Standard.min_tls_version(), "1.2");
        assert_eq!(SecurityLevel::High.min_tls_version(), "1.3");
        assert_eq!(SecurityLevel::Maximum.min_tls_version(), "1.3");
    }

    #[test]
    fn test_security_display() {
        assert_eq!(SecurityLevel::QuantumResistant.to_string(), "quantum_resistant");
    }

    #[test]
    fn test_security_serde_roundtrip() {
        let l = SecurityLevel::Maximum;
        let json = serde_json::to_string(&l).unwrap();
        assert_eq!(json, "\"maximum\"");
        let l2: SecurityLevel = serde_json::from_str(&json).unwrap();
        assert_eq!(l2, SecurityLevel::Maximum);
    }

    // ── Cross-type integration ──

    #[test]
    fn test_health_in_service() {
        // Show that HealthStatus and ServiceInfo compose naturally
        let health = HealthStatus::ok().with_uptime(600);
        let service = ServiceInfo::new("sg-1", "sweetGrass")
            .with_detail_health(&health);
        assert!(service.metadata.contains_key("healthy"));
        assert_eq!(service.metadata.get("healthy").map(String::as_str), Some("true"));
    }
}

impl ServiceInfo {
    /// Attach health status summary to metadata.
    #[must_use]
    pub fn with_detail_health(mut self, health: &HealthStatus) -> Self {
        self.metadata.insert("healthy".into(), health.healthy.to_string());
        if let Some(msg) = &health.message {
            self.metadata.insert("health_message".into(), msg.clone());
        }
        self.metadata.insert("uptime_secs".into(), health.uptime_secs.to_string());
        self
    }
}

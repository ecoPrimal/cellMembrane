// ── Tests ───────────────────────────────────────────────────────────

use super::*;
use super::helpers::*;

    #[test]
    fn classify_googlebot() {
        assert_eq!(
            classify_visitor(
                "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
            ),
            VisitorClass::SearchBot
        );
    }

    #[test]
    fn classify_bingbot() {
        assert_eq!(
            classify_visitor(
                "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
            ),
            VisitorClass::SearchBot
        );
    }

    #[test]
    fn classify_gptbot() {
        assert_eq!(
            classify_visitor("GPTBot/1.0 (+https://openai.com/gptbot)"),
            VisitorClass::AiBot
        );
    }

    #[test]
    fn classify_claudebot() {
        assert_eq!(classify_visitor("ClaudeBot/1.0"), VisitorClass::AiBot);
    }

    #[test]
    fn classify_twitterbot() {
        assert_eq!(classify_visitor("Twitterbot/1.0"), VisitorClass::SocialBot);
    }

    #[test]
    fn classify_curl() {
        assert_eq!(classify_visitor("curl/7.88.1"), VisitorClass::GenericBot);
    }

    #[test]
    fn classify_chrome() {
        assert_eq!(
            classify_visitor(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            VisitorClass::Human
        );
    }

    #[test]
    fn classify_firefox() {
        assert_eq!(
            classify_visitor(
                "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"
            ),
            VisitorClass::Human
        );
    }

    #[test]
    fn classify_empty() {
        assert_eq!(classify_visitor(""), VisitorClass::Unknown);
    }

    #[test]
    fn classify_uptimerobot() {
        assert_eq!(
            classify_visitor(
                "Mozilla/5.0+(compatible; UptimeRobot/2.0; http://www.uptimerobot.com/)"
            ),
            VisitorClass::MonitorBot
        );
    }

    #[test]
    fn normalize_path_strips_query() {
        assert_eq!(normalize_path("/evidence/?page=2"), "/evidence/");
        assert_eq!(normalize_path("/network/#actors"), "/network/");
        assert_eq!(normalize_path("/"), "/");
        assert_eq!(normalize_path(""), "/");
    }

    #[test]
    fn report_ingest_classifies_correctly() {
        let mut report = ReceptorReport::empty();

        let entry = CaddyLogEntry {
            request: CaddyRequest {
                remote_ip: "1.2.3.4".into(),
                host: "detroit.primals.eco".into(),
                uri: "/evidence/".into(),
                method: "GET".into(),
                headers: CaddyHeaders {
                    user_agent: vec!["Mozilla/5.0 (compatible; Googlebot/2.1)".into()],
                },
            },
            status: 200,
            size: 4096,
            duration: 0.015,
            ts: 1727800000.0,
        };
        report.ingest(&entry);

        let entry2 = CaddyLogEntry {
            request: CaddyRequest {
                remote_ip: "5.6.7.8".into(),
                host: "detroit.primals.eco".into(),
                uri: "/evidence/".into(),
                method: "GET".into(),
                headers: CaddyHeaders {
                    user_agent: vec![
                        "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36".into(),
                    ],
                },
            },
            status: 200,
            size: 4096,
            duration: 0.020,
            ts: 1727800001.0,
        };
        report.ingest(&entry2);

        report.finalize();

        let host = report.hosts.get("detroit.primals.eco").unwrap();
        assert_eq!(host.total_requests, 2);
        assert_eq!(host.total_human, 1);
        assert_eq!(host.total_search_bot, 1);
        assert_eq!(host.crawl_coverage, 1);
        assert_eq!(host.unique_paths, 1);

        let page = host.pages.get("/evidence/").unwrap();
        assert_eq!(page.total_hits, 2);
        assert_eq!(page.human_hits, 1);
        assert_eq!(page.search_bot_hits, 1);
        assert_eq!(page.ok_count, 2);
    }

    #[test]
    fn cold_pages_identifies_uncrawled() {
        let mut report = ReceptorReport::empty();

        let crawled = CaddyLogEntry {
            request: CaddyRequest {
                remote_ip: "1.2.3.4".into(),
                host: "detroit.primals.eco".into(),
                uri: "/".into(),
                method: "GET".into(),
                headers: CaddyHeaders {
                    user_agent: vec!["Googlebot/2.1".into()],
                },
            },
            status: 200,
            size: 1000,
            duration: 0.01,
            ts: 1727800000.0,
        };
        report.ingest(&crawled);

        let uncrawled = CaddyLogEntry {
            request: CaddyRequest {
                remote_ip: "5.6.7.8".into(),
                host: "detroit.primals.eco".into(),
                uri: "/network/dpsc/".into(),
                method: "GET".into(),
                headers: CaddyHeaders {
                    user_agent: vec!["Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36".into()],
                },
            },
            status: 200,
            size: 2000,
            duration: 0.02,
            ts: 1727800001.0,
        };
        report.ingest(&uncrawled);

        report.finalize();

        let cold = report.cold_pages("detroit.primals.eco");
        assert_eq!(cold, vec!["/network/dpsc/"]);
        assert!(report.cold_pages("sporeprint.primals.eco").is_empty());
    }

    #[test]
    fn visitor_class_display() {
        assert_eq!(VisitorClass::SearchBot.to_string(), "search_bot");
        assert_eq!(VisitorClass::Human.to_string(), "human");
        assert_eq!(VisitorClass::AiBot.to_string(), "ai_bot");
        assert_eq!(VisitorClass::ScraperBot.to_string(), "scraper_bot");
        assert_eq!(VisitorClass::AgenticHuman.to_string(), "agentic_human");
    }

    #[test]
    fn classify_path_dotenv() {
        assert_eq!(classify_path("/.env"), Some(VisitorClass::ScraperBot));
        assert_eq!(
            classify_path("/.env.backup"),
            Some(VisitorClass::ScraperBot)
        );
        assert_eq!(classify_path("/.env.prod"), Some(VisitorClass::ScraperBot));
    }

    #[test]
    fn classify_path_aws_credentials() {
        assert_eq!(
            classify_path("/.aws/credentials"),
            Some(VisitorClass::ScraperBot)
        );
    }

    #[test]
    fn classify_path_git() {
        assert_eq!(
            classify_path("/.git/config"),
            Some(VisitorClass::ScraperBot)
        );
    }

    #[test]
    fn classify_path_wordpress() {
        assert_eq!(classify_path("/wp-admin"), Some(VisitorClass::ScraperBot));
        assert_eq!(
            classify_path("/wp-login.php"),
            Some(VisitorClass::ScraperBot)
        );
        assert_eq!(classify_path("/xmlrpc.php"), Some(VisitorClass::ScraperBot));
    }

    #[test]
    fn classify_path_php_on_static_site() {
        assert_eq!(classify_path("/index.php"), Some(VisitorClass::ScraperBot));
        assert_eq!(classify_path("/admin.php"), Some(VisitorClass::ScraperBot));
    }

    #[test]
    fn classify_path_normal_content() {
        assert_eq!(classify_path("/"), None);
        assert_eq!(classify_path("/evidence/"), None);
        assert_eq!(classify_path("/network/dpsc/"), None);
        assert_eq!(classify_path("/analysis/rico-pattern/"), None);
    }

    #[test]
    fn classify_request_probe_overrides_ua() {
        // Clean Chrome UA but requesting /.env → ScraperBot, not Human
        assert_eq!(
            classify_request(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "/.env"
            ),
            VisitorClass::ScraperBot
        );
    }

    #[test]
    fn classify_request_normal_path_uses_ua() {
        assert_eq!(
            classify_request(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "/evidence/"
            ),
            VisitorClass::Human
        );
    }

    #[test]
    fn scraper_session_not_counted_as_human() {
        let mut report = ReceptorReport::empty();

        let ua = "Mozilla/5.0 Chrome/152.0.0.0 Safari/537.36";

        // Scanner hitting 28 dotfiles in 30 seconds
        let probes = [
            "/.env",
            "/.env.backup",
            "/.env.prod",
            "/.env.local",
            "/.aws/credentials",
            "/.git/config",
            "/wp-admin",
            "/xmlrpc.php",
        ];
        for (i, path) in probes.iter().enumerate() {
            report.ingest(&CaddyLogEntry {
                request: CaddyRequest {
                    remote_ip: "5.6.7.8".into(),
                    host: "detroit.primals.eco".into(),
                    uri: path.to_string(),
                    method: "GET".into(),
                    headers: CaddyHeaders {
                        user_agent: vec![ua.into()],
                    },
                },
                status: 404,
                size: 0,
                duration: 0.001,
                ts: 1727800000.0 + (i as f64 * 1.0), // 1 second apart
            });
        }

        report.finalize();

        let host = report.hosts.get("detroit.primals.eco").unwrap();
        // Zero human hits — all probe paths classified as ScraperBot
        assert_eq!(host.total_human, 0, "probe hits should not count as human");
        assert_eq!(host.total_requests, 8);

        // Session should also be ScraperBot, not Human
        let sess = report.sessions.get("detroit.primals.eco").unwrap();
        assert_eq!(
            sess.human_sessions, 0,
            "scraper session should not be counted as human"
        );
    }

    #[test]
    fn velocity_reclassifies_fast_session() {
        let mut report = ReceptorReport::empty();

        let ua = "Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36";

        // 8 legitimate-looking pages in 5 seconds — too fast for a human
        let pages = [
            "/",
            "/evidence/",
            "/network/",
            "/analysis/",
            "/timeline/",
            "/sources/",
            "/about/",
            "/contact/",
        ];
        for (i, path) in pages.iter().enumerate() {
            report.ingest(&CaddyLogEntry {
                request: CaddyRequest {
                    remote_ip: "1.2.3.4".into(),
                    host: "detroit.primals.eco".into(),
                    uri: path.to_string(),
                    method: "GET".into(),
                    headers: CaddyHeaders {
                        user_agent: vec![ua.into()],
                    },
                },
                status: 200,
                size: 1000,
                duration: 0.01,
                ts: 1727800000.0 + (i as f64 * 0.5), // 0.5 seconds apart
            });
        }

        report.finalize();

        let sess = report.sessions.get("detroit.primals.eco").unwrap();
        assert_eq!(
            sess.human_sessions, 0,
            "velocity-flagged session should not be human"
        );
        assert_eq!(sess.total_sessions, 1);
    }

    #[test]
    fn report_summary_format() {
        let mut report = ReceptorReport::empty();

        let entry = CaddyLogEntry {
            request: CaddyRequest {
                remote_ip: "1.2.3.4".into(),
                host: "sporeprint.primals.eco".into(),
                uri: "/".into(),
                method: "GET".into(),
                headers: CaddyHeaders {
                    user_agent: vec!["Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36".into()],
                },
            },
            status: 200,
            size: 1000,
            duration: 0.01,
            ts: 1727800000.0,
        };
        report.ingest(&entry);
        report.finalize();

        let summary = report.summary();
        assert!(summary.contains("Receptor Report"));
        assert!(summary.contains("sporeprint.primals.eco"));
        assert!(summary.contains("human: 1"));
    }

    #[test]
    fn build_log_command_single() {
        let cmd = build_log_command(5000, false);
        assert!(cmd.contains("tail -n 5000"));
        assert!(!cmd.contains("access.log.1"));
    }

    #[test]
    fn build_log_command_rotated() {
        let cmd = build_log_command(50000, true);
        assert!(cmd.contains("access.log.1"));
        assert!(cmd.contains("access.log.2.gz"));
        assert!(cmd.contains("zcat"));
        assert!(cmd.contains("tail -n 50000"));
    }

    #[test]
    fn session_detection_groups_by_ua() {
        let mut report = ReceptorReport::empty();

        let ua = "Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36";

        // Three hits from same UA within 30 minutes = one session
        for (i, path) in ["/", "/evidence/", "/network/"].iter().enumerate() {
            report.ingest(&CaddyLogEntry {
                request: CaddyRequest {
                    remote_ip: "1.2.3.4".into(),
                    host: "detroit.primals.eco".into(),
                    uri: path.to_string(),
                    method: "GET".into(),
                    headers: CaddyHeaders {
                        user_agent: vec![ua.into()],
                    },
                },
                status: 200,
                size: 1000,
                duration: 0.01,
                ts: 1727800000.0 + (i as f64 * 300.0), // 5 min apart
            });
        }

        report.finalize();

        let sess = report.sessions.get("detroit.primals.eco").unwrap();
        assert_eq!(sess.total_sessions, 1);
        assert_eq!(sess.human_sessions, 1);
        assert_eq!(sess.deep_readers, 1); // 3 pages = deep reader
        assert_eq!(sess.bounces, 0);
        assert!((sess.avg_depth - 3.0).abs() < 0.01);
    }

    #[test]
    fn session_detection_splits_at_gap() {
        let mut report = ReceptorReport::empty();

        let ua = "Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36";

        // Hit 1: time T
        report.ingest(&CaddyLogEntry {
            request: CaddyRequest {
                remote_ip: "1.2.3.4".into(),
                host: "detroit.primals.eco".into(),
                uri: "/".into(),
                method: "GET".into(),
                headers: CaddyHeaders {
                    user_agent: vec![ua.into()],
                },
            },
            status: 200,
            size: 1000,
            duration: 0.01,
            ts: 1727800000.0,
        });

        // Hit 2: T + 2 hours (beyond 30min window)
        report.ingest(&CaddyLogEntry {
            request: CaddyRequest {
                remote_ip: "1.2.3.4".into(),
                host: "detroit.primals.eco".into(),
                uri: "/evidence/".into(),
                method: "GET".into(),
                headers: CaddyHeaders {
                    user_agent: vec![ua.into()],
                },
            },
            status: 200,
            size: 1000,
            duration: 0.01,
            ts: 1727800000.0 + 7200.0, // 2 hours later
        });

        report.finalize();

        let sess = report.sessions.get("detroit.primals.eco").unwrap();
        assert_eq!(sess.total_sessions, 2); // Two separate sessions
        assert_eq!(sess.human_sessions, 2);
        assert_eq!(sess.bounces, 2); // Both are single-page
    }

    #[test]
    fn session_summary_in_report_summary() {
        let mut report = ReceptorReport::empty();

        report.ingest(&CaddyLogEntry {
            request: CaddyRequest {
                remote_ip: "1.2.3.4".into(),
                host: "detroit.primals.eco".into(),
                uri: "/".into(),
                method: "GET".into(),
                headers: CaddyHeaders {
                    user_agent: vec!["Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36".into()],
                },
            },
            status: 200,
            size: 1000,
            duration: 0.01,
            ts: 1727800000.0,
        });

        report.finalize();

        let summary = report.summary();
        assert!(summary.contains("sessions:"));
        assert!(summary.contains("1 total"));
        assert!(summary.contains("1 human"));
    }

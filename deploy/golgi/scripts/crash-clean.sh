#!/bin/bash
# crash-clean.sh — ExecStopPost cleanup for Rust services
# Cleans up any leftover pid/lock files after a crash
rm -f /tmp/.${MAINPID:-0}.lock 2>/dev/null

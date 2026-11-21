# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Test Suite - Core Logic, Self-Healing, and Protection Verification
"""
import unittest
from pathlib import Path

from optimusprime.utils.constants import (
    APP_NAME, PROTECTED_PROCESSES, PROTECTED_SERVICE_NAMES,
    DEFAULT_CONFIG, APP_DIR
)
from optimusprime.utils.helpers import norm, name_key, fmt_mb, fmt_gb
from optimusprime.utils.config import load_config, save_config
from optimusprime.utils.self_healing import ensure_directories
from optimusprime.core.tasks import task_category, full_task_name


class TestOptimusPrimeCore(unittest.TestCase):
    def test_protection_rules(self):
        """Verify Windows critical processes and services are strictly protected."""
        critical_processes = ["system", "csrss", "lsass", "smss", "services", "explorer"]
        for p in critical_processes:
            self.assertIn(p, PROTECTED_PROCESSES, f"Critical process '{p}' missing from protection list")

        critical_services = ["WinDefend", "RpcSs", "EventLog", "Schedule"]
        for s in critical_services:
            self.assertIn(s, PROTECTED_SERVICE_NAMES, f"Critical service '{s}' missing from protection list")

    def test_helpers(self):
        """Test formatting and normalization helpers."""
        self.assertEqual(norm("  test  "), "test")
        self.assertEqual(norm(None), "")
        self.assertEqual(name_key("Chrome.EXE"), "chrome")
        self.assertEqual(fmt_mb(1024.56), "1,024.6")
        self.assertEqual(fmt_gb(1024.56), "1,024.56")

    def test_task_categorization(self):
        """Test scheduled task classification logic."""
        self.assertEqual(task_category({"TaskPath": "\\Microsoft\\Windows\\Defrag"}), "Microsoft")
        self.assertEqual(task_category({"TaskName": "OptimusPrime-AutoMaintenance"}), "OPTIMUSPRIME")
        self.assertEqual(task_category({"TaskPath": "\\Google\\ChromeUpdate", "Author": "Google LLC"}), "Third-party / Named")
        self.assertEqual(full_task_name("\\", "TestTask"), "\\TestTask")
        self.assertEqual(full_task_name("\\Folder\\", "TestTask"), "\\Folder\\TestTask")

    def test_self_healing_directories(self):
        """Verify directory hierarchy auto-creation."""
        self.assertTrue(ensure_directories())
        self.assertTrue(APP_DIR.exists())

    def test_config_resilience(self):
        """Verify config store recovers and persists properly."""
        cfg = load_config()
        self.assertIsInstance(cfg, dict)
        self.assertIn("refresh_seconds", cfg)
        self.assertTrue(save_config(cfg))


if __name__ == "__main__":
    unittest.main()

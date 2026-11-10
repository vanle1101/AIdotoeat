from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from scripts import phase10_browser


class Phase10BrowserCliTests(unittest.TestCase):
    def test_camera_rotation_measurement_handles_wraparound(self):
        self.assertAlmostEqual(phase10_browser._angle_delta_degrees(-170, 100), 90)
        self.assertAlmostEqual(phase10_browser._angle_delta_degrees(170, -100), -90)
        state = {"camera": {"x": 1, "z": 0}, "target": {"x": 0, "z": 0}}
        self.assertAlmostEqual(phase10_browser._camera_yaw_degrees(state), 90)

    def test_cli_summary_is_ascii_safe_on_legacy_windows_console(self):
        output = io.StringIO()
        evidence_dir = Path.cwd() / "phase10-evidence-kiếm"
        report = {"views": [{"checks": {"dashboard_loaded": True}}]}
        argv = ["phase10_browser.py", "--url", "http://127.0.0.1:18889/",
                "--output-dir", str(evidence_dir)]
        with patch.object(sys, "argv", argv), \
                patch.object(phase10_browser, "run", new=AsyncMock(return_value=report)), \
                contextlib.redirect_stdout(output):
            self.assertEqual(phase10_browser.main(), 0)
        rendered = output.getvalue()
        rendered.encode("cp1252")
        self.assertIn("\\u1ebf", rendered)


if __name__ == "__main__":
    unittest.main()

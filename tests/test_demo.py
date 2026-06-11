import os
import tempfile
import unittest
from pathlib import Path

from tokensaver.demo import run_demo


class DemoTests(unittest.TestCase):
    def setUp(self):
        self._old_update_env = os.environ.get("TOKENSAVER_CHECK_UPDATE_ON_RUN")
        os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = "0"

    def tearDown(self):
        if self._old_update_env is None:
            os.environ.pop("TOKENSAVER_CHECK_UPDATE_ON_RUN", None)
        else:
            os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = self._old_update_env

    def test_demo_writes_before_after_benchmark(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_demo(tmp)

            comparison = result["comparison"]
            self.assertEqual(comparison["result"], "accepted")
            self.assertLess(comparison["deltas"]["input_tokens"]["delta_pct"], -90)
            self.assertGreater(comparison["roi_score"]["delta"], 0)
            self.assertIn("deep_route_for_short_task", comparison["resolved_findings"])
            self.assertTrue((Path(tmp) / "benchmark.json").exists())
            self.assertIn(
                "TokenSaver Demo Benchmark",
                (Path(tmp) / "benchmark.md").read_text(encoding="utf-8"),
            )
            self.assertTrue((Path(tmp) / "panel" / "index.html").exists())
            self.assertIn(
                "High Cost",
                (Path(tmp) / "panel" / "before.html").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "Healthy",
                (Path(tmp) / "panel" / "after.html").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()

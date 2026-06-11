import os
import tempfile
import unittest
from pathlib import Path

from tokensaver.benchmark import benchmark_runs
from tokensaver.cli import main
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
            self.assertTrue((Path(tmp) / "share-card.svg").exists())
            self.assertIn(
                "High Cost",
                (Path(tmp) / "panel" / "before.html").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "Healthy",
                (Path(tmp) / "panel" / "after.html").read_text(encoding="utf-8"),
            )

    def test_benchmark_and_open_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before_path = root / "before.json"
            after_path = root / "after.json"
            before_path.write_text(
                '{"run_id":"before","input_tokens":1000,"output_tokens":500,"latency_ms":3000}',
                encoding="utf-8",
            )
            after_path.write_text(
                '{"run_id":"after","input_tokens":500,"output_tokens":200,"latency_ms":1000}',
                encoding="utf-8",
            )
            self.assertEqual(
                main(
                    [
                        "benchmark",
                        "--before-file",
                        str(before_path),
                        "--after-file",
                        str(after_path),
                        "--output-dir",
                        str(root / "benchmark"),
                    ]
                ),
                0,
            )
            self.assertTrue((root / "benchmark" / "share-card.svg").exists())
            self.assertEqual(
                main(
                    [
                        "open",
                        "--store-dir",
                        str(root / "missing"),
                        "--demo-store-dir",
                        str(root / "demo"),
                        "--no-browser",
                    ]
                ),
                0,
            )
            self.assertTrue((root / "demo" / "panel" / "index.html").exists())


if __name__ == "__main__":
    unittest.main()

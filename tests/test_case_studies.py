import json
import unittest
from pathlib import Path

from tokensaver.benchmark import benchmark_runs


class CaseStudyTests(unittest.TestCase):
    def test_all_case_studies_are_accepted_and_reduce_input(self):
        root = Path("examples/case-studies")
        cases = [
            "langgraph-repeated-tools",
            "openai-context-waste",
            "rag-oversized-retrieval",
        ]
        for case in cases:
            with self.subTest(case=case):
                before = json.loads((root / case / "before.json").read_text(encoding="utf-8"))
                after = json.loads((root / case / "after.json").read_text(encoding="utf-8"))
                import tempfile

                with tempfile.TemporaryDirectory() as tmp:
                    result = benchmark_runs(before, after, output_dir=tmp, title=case)
                comparison = result["comparison"]
                self.assertEqual(comparison["result"], "accepted")
                self.assertLess(comparison["deltas"]["input_tokens"]["delta"], 0)
                self.assertGreater(comparison["roi_score"]["delta"], 0)
                self.assertEqual(comparison["quality_blockers"], [])


if __name__ == "__main__":
    unittest.main()

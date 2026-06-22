"""Repository development-governance integrity tests."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRINCIPLES = ROOT / "docs" / "governance" / "DEVELOPMENT_PRINCIPLES.md"
EXPECTED_PRINCIPLES_SHA256 = "8f5f4da2ac2539b5f9bbc736571dde5026219a57ef8e71d6cad9126017336e6e"


class DevelopmentGovernanceTests(unittest.TestCase):
    def test_required_governance_files_exist(self) -> None:
        required = [
            ROOT / "AGENTS.md",
            PRINCIPLES,
            ROOT / "docs" / "governance" / "README.md",
            ROOT / "docs" / "governance" / "DEVELOPMENT_LOG.md",
            ROOT / "docs" / "governance" / "TEST_LOG.md",
        ]
        self.assertEqual([], [str(path.relative_to(ROOT)) for path in required if not path.is_file()])

    def test_principles_document_has_not_changed(self) -> None:
        digest = hashlib.sha256(PRINCIPLES.read_bytes()).hexdigest()
        self.assertEqual(
            EXPECTED_PRINCIPLES_SHA256,
            digest,
            "受控开发原则发生变化；只有张涛专项授权并完成原则变更流程后才能更新基线。",
        )

    def test_principles_contain_mandatory_controls(self) -> None:
        text = PRINCIPLES.read_text(encoding="utf-8")
        for required_text in (
            "每次开发结束，都必须总结一份开发记录",
            "每次开发都必须在对应 PRD 中定义配套测试 SOP",
            "每一次迭代、优化、文档变更或缺陷修复，都必须先形成 PRD",
            "只有原则所有者张涛能够授权变更",
        ):
            self.assertIn(required_text, text)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from tokensaver import __version__
from tokensaver.install import (
    build_upgrade_command,
    doctor,
    fix_project_pins,
    scan_project_pins,
    verbose_version_info,
    verify_install,
)


class InstallExperienceTests(unittest.TestCase):
    def test_verbose_version_info_includes_environment_fields(self):
        info = verbose_version_info()

        self.assertEqual(info["version"], __version__)
        self.assertIn("python_executable", info)
        self.assertIn("package_path", info)
        self.assertIn("cli_script_on_path", info)

    def test_scan_and_fix_project_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirements.txt"
            path.write_text(
                "git+https://github.com/zhangtao-jayce/TokenSaver.git@old1234\n",
                encoding="utf-8",
            )

            pins = scan_project_pins(tmp)
            self.assertEqual(pins[0]["commit"], "old1234")

            result = fix_project_pins(commit="new5678", project_dir=tmp)
            self.assertTrue(result["ok"])
            self.assertIn("@new5678", path.read_text(encoding="utf-8"))

    def test_doctor_offline_returns_structured_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = doctor(project_dir=tmp, check_remote=False)

            self.assertIn("version", result)
            self.assertIn("findings", result)
            self.assertIn("upgrade_command", result)

    def test_verify_install_accepts_current_version(self):
        result = verify_install(expected_version=__version__)

        self.assertTrue(result["ok"])
        self.assertEqual(result["version"], __version__)

    def test_upgrade_command_uses_current_python(self):
        command = build_upgrade_command(commit="abc1234")

        self.assertIn("-m pip install", command)
        self.assertIn("@abc1234", command)


if __name__ == "__main__":
    unittest.main()

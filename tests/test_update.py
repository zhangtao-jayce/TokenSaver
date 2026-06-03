import unittest

from tokensaver import __version__
from tokensaver.update import check_for_update, format_update_notice


class UpdateTests(unittest.TestCase):
    def test_check_for_update_reports_available_with_injected_version(self):
        info = check_for_update(latest_version="99.0.0", latest_commit="abcdef1")

        self.assertEqual(info.local_version, __version__)
        self.assertEqual(info.latest_version, "99.0.0")
        self.assertEqual(info.latest_commit, "abcdef1")
        self.assertEqual(info.status, "update_available")
        self.assertIn("@abcdef1", info.upgrade_command)

    def test_check_for_update_reports_up_to_date_with_same_version(self):
        info = check_for_update(latest_version=__version__, latest_commit="abcdef1")

        self.assertEqual(info.status, "up_to_date")

    def test_format_update_notice_is_empty_when_up_to_date(self):
        info = check_for_update(latest_version=__version__, latest_commit="abcdef1")

        self.assertEqual(format_update_notice(info), "")

    def test_format_update_notice_includes_upgrade_command(self):
        info = check_for_update(latest_version="99.0.0", latest_commit="abcdef1")
        notice = format_update_notice(info)

        self.assertIn("TokenSaver Update", notice)
        self.assertIn("latest_version: 99.0.0", notice)
        self.assertIn("pip install --upgrade", notice)


if __name__ == "__main__":
    unittest.main()

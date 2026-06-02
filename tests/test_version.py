import pathlib
import unittest

import tokensaver


class VersionTests(unittest.TestCase):
    def test_package_version_matches_pyproject(self):
        pyproject = pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
        self.assertIn(f'version = "{tokensaver.__version__}"', pyproject)


if __name__ == "__main__":
    unittest.main()

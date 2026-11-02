import os, pathlib, sys, unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import deck  # noqa: E402


class FindChrome(unittest.TestCase):
    def test_none_when_nothing_is_installed(self):
        with mock.patch.dict(os.environ, {"PATH": "", "CHROME": ""}), \
             mock.patch("os.path.exists", return_value=False), \
             mock.patch("shutil.which", return_value=None):
            self.assertIsNone(deck.find_chrome())

    def test_env_wins(self):
        with mock.patch.dict(os.environ, {"CHROME": "/x/chrome"}), \
             mock.patch("os.path.exists", side_effect=lambda p: p == "/x/chrome"):
            self.assertEqual(deck.find_chrome(), "/x/chrome")

    def test_need_chrome_exits_with_one_line(self):
        with mock.patch("deck.find_chrome", return_value=None):
            with self.assertRaises(SystemExit) as cm:
                deck.need_chrome()
            self.assertIn("Chrome not found", str(cm.exception))


if __name__ == "__main__":
    unittest.main()

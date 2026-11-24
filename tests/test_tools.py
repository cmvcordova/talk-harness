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


class LintCommand(unittest.TestCase):
    """The lint must not pass when the browser never finished its measurements."""

    def run_lint(self, stderr, strict=True):
        import contextlib, io, tempfile, types
        root = pathlib.Path(tempfile.mkdtemp())
        (root / "_src").mkdir()
        (root / "deck.toml").write_text('title = "T"\noutput = "t.html"\nfonts = ""\n')
        (root / "t.html").write_text('<main class="deck-stage" id="deckStage"><section class="slide void" data-slide="01"><h1>T</h1></section></main>')
        with mock.patch("deck.build", return_value=root / "t.html"), \
             mock.patch("deck.chrome", return_value=types.SimpleNamespace(returncode=0, stderr=stderr)) as chrome, \
             contextlib.redirect_stdout(io.StringIO()) as out:
            code = deck.cmd_lint(root, types.SimpleNamespace(strict=strict))
        chrome.assert_called_once()
        return code, out.getvalue()

    def test_a_browser_pass_that_did_not_finish_fails_even_without_strict(self):
        code, out = self.run_lint("Chrome failed", strict=False)
        self.assertEqual(code, 1)
        self.assertIn("did not finish", out)

    def test_a_finished_clean_pass_returns_zero(self):
        code, out = self.run_lint('[1:2:INFO:CONSOLE:9] "CHECK done: 1 slides, 0 problems"')
        self.assertEqual(code, 0)
        self.assertIn("0 to look at", out)

    def test_a_browser_finding_fails_under_strict_only(self):
        log = ('[1:2:INFO:CONSOLE:9] "LINT slide 01: small-text: running text at 12px (minimum 24): tiny"\n'
               '[1:2:INFO:CONSOLE:9] "CHECK done: 1 slides, 0 problems"')
        self.assertEqual(self.run_lint(log, strict=True)[0], 1)
        self.assertEqual(self.run_lint(log, strict=False)[0], 0)


if __name__ == "__main__":
    unittest.main()

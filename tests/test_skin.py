import contextlib, io, os, pathlib, shutil, sys, tempfile, unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_src"))
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import deck  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
SKIN = FIX / "skin-a"


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def mini(self):
        root = self.tmp / "mini"
        shutil.copytree(FIX / "mini", root)
        for f in ("deck.css", "viewport-base.css", "controller.js", "viz.js"):
            shutil.copy(ROOT / "_src" / f, root / "_src" / f)
        return root

    def new(self, *extra):
        dest = self.tmp / "talk"
        quiet(deck.main, ["new", str(dest), *extra])
        return dest


class BuildWithSkin(Tmp):
    def test_skin_css_is_pasted_after_the_theme(self):
        root = self.mini()
        shutil.copy(SKIN / "skin.css", root / "_src" / "skin.css")
        r = build.build(root)
        self.assertIn("SKIN-A MARKER", r.html)
        self.assertGreater(r.html.index("SKIN-A MARKER"), r.html.index("DECK CHROME"))
        self.assertTrue(any(l.startswith("skin:") for l in r.lines), r.lines)

    def test_no_skin_file_no_skin_line(self):
        r = build.build(self.mini())
        self.assertFalse(any(l.startswith("skin:") for l in r.lines), r.lines)

    def test_inline_svg_token(self):
        root = self.mini()
        shutil.copy(SKIN / "assets" / "mark.svg", root / "assets" / "mark.svg")
        p = root / "_src" / "slides.html"
        p.write_text(p.read_text().replace("<h1>Mini</h1>", "<h1>Mini</h1><i>__INLINE_mark.svg__</i>"))
        r = build.build(root)
        self.assertIn('<i><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8">', r.html)
        self.assertNotIn("<?xml", r.html)
        self.assertNotIn("__INLINE_", r.html)

    def test_inline_svg_missing_is_a_problem(self):
        root = self.mini()
        p = root / "_src" / "slides.html"
        p.write_text(p.read_text().replace("<h1>Mini</h1>", "<h1>Mini</h1>__INLINE_gone.svg__"))
        before = build.build(self.mini_copy()).problems
        r = build.build(root)
        self.assertEqual(r.problems, before + 1)
        self.assertTrue(any("gone.svg" in l for l in r.lines), r.lines)

    def mini_copy(self):
        root = self.tmp / "mini2"
        if not root.exists():
            shutil.copytree(self.tmp / "mini", root)
            shutil.copy(FIX / "mini" / "_src" / "slides.html", root / "_src" / "slides.html")
        return root

    def test_empty_fonts_means_no_font_link(self):
        root = self.mini()
        p = root / "deck.toml"
        p.write_text(p.read_text().replace(
            'fonts  = "https://fonts.googleapis.com/css2?family=DM+Sans&display=swap"', 'fonts  = ""'))
        r = build.build(root)
        self.assertNotIn('rel="stylesheet"', r.html)
        self.assertNotIn("fonts.googleapis.com", r.html)


class NewWithSkin(Tmp):
    def test_plain_new_has_no_skin(self):
        dest = self.new()
        self.assertFalse((dest / "_src" / "skin.css").exists())
        self.assertNotIn("skin", (dest / "deck.toml").read_text().split("fonts")[0])

    def test_new_with_a_skin_path(self):
        dest = self.new("--skin", str(SKIN))
        self.assertIn("SKIN-A MARKER", (dest / "_src" / "skin.css").read_text())
        self.assertTrue((dest / "assets" / "mark.svg").exists())
        self.assertIn("Skin A cover", (dest / "_src" / "slides.html").read_text())
        self.assertIn("Skin A says hello", (dest / "outline.md").read_text())
        self.assertIn("One mark per slide", (dest / "SKIN.md").read_text())
        cfg = deck.cfg(dest)
        self.assertEqual(cfg["skin"], "skin-a")
        self.assertEqual(cfg["fonts"], "https://fonts.googleapis.com/css2?family=Archivo&display=swap")
        self.assertEqual(cfg["output"], "talk.html")

    def test_a_stamped_skinned_talk_builds(self):
        dest = self.new("--skin", str(SKIN))
        r = build.build(dest)
        self.assertIn("SKIN-A MARKER", r.html)
        self.assertIn("<svg", r.html)
        self.assertEqual(r.problems, 0, r.lines)

    def test_named_starter(self):
        dest = self.new("--skin", str(SKIN), "--starter", "short")
        self.assertIn("Skin A short cover", (dest / "_src" / "slides.html").read_text())
        self.assertTrue((dest / "assets" / "short-only.svg").exists(), "a starter brings its own media")
        self.assertTrue((dest / "assets" / "mark.svg").exists(), "and the skin's assets still come")

    def test_unknown_starter_exits_and_names_the_ones_there(self):
        with self.assertRaises(SystemExit) as cm:
            self.new("--skin", str(SKIN), "--starter", "nope")
        self.assertIn("short", str(cm.exception))

    def test_skin_by_name_through_the_environment(self):
        with mock.patch.dict(os.environ, {"TALK_SKINS": str(FIX)}):
            dest = self.new("--skin", "skin-a")
        self.assertTrue((dest / "_src" / "skin.css").exists())

    def test_unknown_skin_exits_and_says_where_it_looked(self):
        with mock.patch.dict(os.environ, {"TALK_SKINS": str(FIX)}):
            with self.assertRaises(SystemExit) as cm:
                self.new("--skin", "no-such-skin")
        self.assertIn(str(FIX), str(cm.exception))
        self.assertIn("skin-a", str(cm.exception))


class Reskin(Tmp):
    def test_reskin_replaces_css_assets_and_fonts_and_keeps_the_slides(self):
        dest = self.new()
        slides = (dest / "_src" / "slides.html").read_text()
        quiet(deck.main, ["--root", str(dest), "reskin", "--skin", str(SKIN)])
        self.assertIn("SKIN-A MARKER", (dest / "_src" / "skin.css").read_text())
        self.assertTrue((dest / "assets" / "mark.svg").exists())
        self.assertEqual((dest / "_src" / "slides.html").read_text(), slides)
        cfg = deck.cfg(dest)
        self.assertEqual(cfg["skin"], "skin-a")
        self.assertIn("Archivo", cfg["fonts"])


class SetToml(Tmp):
    def test_a_new_key_goes_before_the_first_table(self):
        p = self.tmp / "deck.toml"
        p.write_text('title = "T"\n\n[lint]\nmin_px = 20\n')
        deck.set_toml(p, "skin", "x")
        cfg = deck.tomllib.loads(p.read_text())
        self.assertEqual(cfg["skin"], "x")
        self.assertEqual(cfg["lint"], {"min_px": 20})


if __name__ == "__main__":
    unittest.main()

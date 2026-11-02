import contextlib, io, pathlib, shutil, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_src"))
import build  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "mini"


class Mini(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        shutil.copytree(FIX, self.tmp / "mini")
        self.root = self.tmp / "mini"
        # the fixture holds only what a talk owns; the harness files come from the real _src
        for f in ("deck.css", "viewport-base.css", "controller.js", "viz.js"):
            shutil.copy(ROOT / "_src" / f, self.root / "_src" / f)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, rel, old, new):
        p = self.root / rel
        s = p.read_text()
        assert old in s, old
        p.write_text(s.replace(old, new))

    def test_renumbers_from_document_order_and_backup_unnumbered(self):
        r = build.build(self.root)
        self.assertEqual(r.total, 2)
        self.assertIn('<span class="label">02 / 02</span>', r.html)
        self.assertIn('<span class="label">Backup</span>', r.html)

    def test_lists_placeholders(self):
        r = build.build(self.root)
        self.assertTrue(any("placeholder" in l and "slide 02" in l and "write the lead" in l for l in r.lines), r.lines)

    def test_raw_quote_in_notes_fails(self):
        self.edit("outline.md", 'Say "hello"', 'Say "hello')  # unbalanced, but it is escaped anyway
        build.build(self.root)  # outline notes are always escaped: must pass
        self.edit("_src/slides.html", 'data-notes="old notes"', 'data-notes="a "raw" quote"')
        self.edit("_src/slides.html", ' data-slide="02"', '')  # no outline entry: keeps inline notes
        with self.assertRaises(SystemExit):
            build.build(self.root)

    def test_sums_time_both_languages_and_warns_over_limit(self):
        r = build.build(self.root)
        self.assertTrue(any("timing: 1:25" in l for l in r.lines), r.lines)
        self.assertTrue(any("over the limit" in l for l in r.lines), r.lines)

    def test_injects_notes_by_data_slide_and_outline_wins(self):
        r = build.build(self.root)
        self.assertIn('data-notes="Say &quot;hello&quot; to the room."', r.html)
        self.assertIn('data-notes="The second slide."', r.html)
        self.assertNotIn("old notes", r.html)
        self.assertTrue(any("outline wins" in l and "slide 02" in l for l in r.lines), r.lines)

    def test_media_tokens_link_and_embed(self):
        r = build.build(self.root)
        self.assertIn('src="assets/fig.png"', r.html)
        r2 = build.build(self.root, embed=True)
        self.assertIn("data:image/png;base64,UE5H", r2.html)
        self.edit("_src/slides.html", "__MEDIA_fig.png__", "__MEDIA_missing.png__")
        r3 = build.build(self.root)
        self.assertTrue(any("missing media" in l.lower() and "missing.png" in l for l in r3.lines), r3.lines)

    def test_citations_fill_footband_and_sources(self):
        r = build.build(self.root)
        self.assertIn('<a href="https://example.org/smith" target="_blank" rel="noopener">Smith 2020</a>', r.html)
        self.assertIn("A thing with no URL", r.html)
        self.assertIn('<div class="src"><b>Smith 2020<span class="on">slide 2</span></b>', r.html)
        self.assertNotIn("__SOURCES_LIST__", r.html)

    def test_unknown_viz_fails(self):
        self.edit("_src/slides.html", 'data-viz="drift"', 'data-viz="nope"')
        with self.assertRaises(SystemExit):
            build.build(self.root)

    def test_unknown_data_slide_fails(self):
        self.edit("_src/slides.html", 'data-slide="03"', 'data-slide="09"')
        with self.assertRaises(SystemExit):
            build.build(self.root)

    def test_no_source_is_reported(self):
        r = build.build(self.root)
        self.assertTrue(any("no Source" in l and "03" in l for l in r.lines), r.lines)

    def test_deck_id_and_title_land(self):
        r = build.build(self.root)
        self.assertIn("const DECK_ID = 'mini';", r.html)
        self.assertIn("<title>Mini</title>", r.html)
        self.assertIn('<html lang="en">', r.html)

    def test_main_writes_output(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build.main(["--root", str(self.root)])
        self.assertTrue((self.root / "mini.html").exists())


if __name__ == "__main__":
    unittest.main()

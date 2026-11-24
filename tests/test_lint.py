import pathlib, sys, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import lint  # noqa: E402

CHROME = '<div class="chrome"><span class="label">00 / 00</span></div>'
FOOT = '<div class="footband"><span>results/table3.csv, a long line of provenance that is not counted</span></div>'


def slide(body, attrs='class="slide dark" data-slide="02"'):
    return f"<section {attrs}>{CHROME}{body}{FOOT}</section>"


def rules(html, **cfg):
    return [(p.slide, p.rule) for p in lint.lint_slides(html, cfg)]


class Headline(unittest.TestCase):
    def test_a_sentence_passes(self):
        html = slide('<h2 class="claim">The full matrix beats the ten maxima on two benchmarks.</h2><img src="a.png">')
        self.assertEqual(rules(html), [])

    def test_a_topic_is_named(self):
        html = slide('<h2>Results</h2><img src="a.png">')
        self.assertIn((1, "headline-topic"), rules(html))

    def test_a_question_passes(self):
        html = slide('<h2>Where is it wrong?</h2><img src="a.png">')
        self.assertEqual(rules(html), [])

    def test_a_long_headline_is_named(self):
        html = slide('<h2 class="claim">' + "word " * 19 + 'end.</h2><img src="a.png">')
        self.assertIn((1, "headline-long"), rules(html))
        self.assertNotIn((1, "headline-long"), rules(html, claim_max_words=30))

    def test_a_content_slide_with_no_headline_is_named(self):
        self.assertIn((1, "headline-missing"), rules(slide('<p class="lead">Some text.</p>')))

    def test_a_cover_without_chrome_is_not_a_content_slide(self):
        html = '<section class="slide void" data-slide="01"><h1>Title</h1></section>'
        self.assertEqual(rules(html), [])


class Body(unittest.TestCase):
    def test_words_outside_headline_chrome_footer_and_labels_are_counted(self):
        body = '<h2 class="claim">A claim that is a sentence.</h2><p class="lead">' + "w " * 50 + '</p><div class="label">not counted</div>'
        got = lint.lint_slides(slide(body), {})
        hit = [p for p in got if p.rule == "words"]
        self.assertEqual(len(hit), 1)
        self.assertIn("50 words", hit[0].message)

    def test_words_in_a_table_or_a_figure_are_evidence_and_not_counted(self):
        body = ('<h2 class="claim">A claim that is a sentence.</h2><table><tr><td>' + "w " * 80 + '</td></tr></table>'
                '<figure><figcaption>' + "w " * 30 + '</figcaption></figure>')
        self.assertEqual(rules(slide(body)), [])

    def test_a_one_number_slide_needs_no_headline(self):
        self.assertEqual(rules(slide('<div class="stat">1920</div><p class="lead">The stage is fixed.</p>')), [])

    def test_few_words_pass(self):
        body = '<h2 class="claim">A claim that is a sentence.</h2><p class="lead">' + "w " * 30 + "</p><img src='a.png'>"
        self.assertEqual(rules(slide(body)), [])

    def test_a_bare_list_with_no_evidence_is_named(self):
        body = '<h2 class="claim">A claim that is a sentence.</h2><ul class="ticks"><li>one</li><li>two</li></ul>'
        self.assertIn((1, "list-no-evidence"), rules(slide(body)))

    def test_a_list_beside_a_figure_passes(self):
        body = '<h2 class="claim">A claim that is a sentence.</h2><ul class="ticks"><li>one</li></ul><img src="a.png">'
        self.assertEqual(rules(slide(body)), [])

    def test_structured_lists_are_evidence(self):
        for wrap in ('<ol class="asks"><li>Why?</li></ol>', '<ol class="findings"><li>It holds.</li></ol>',
                     '<div class="ledger"><div><ul class="ticks"><li>built</li></ul></div></div>'):
            body = '<h2 class="claim">A claim that is a sentence.</h2>' + wrap
            self.assertEqual(rules(slide(body)), [], wrap)

    def test_too_many_figures(self):
        body = '<h2 class="claim">A claim that is a sentence.</h2>' + '<img src="a.png">' * 3
        self.assertIn((1, "figures"), rules(slide(body)))
        self.assertEqual(rules(slide(body), max_figures=3), [])

    def test_logos_in_the_chrome_and_partner_row_are_not_figures(self):
        body = ('<h2 class="claim">A claim that is a sentence.</h2><img src="a.png">'
                '<div class="partners"><img src="logo.svg"><img src="logo2.svg"></div>')
        html = slide(body).replace(CHROME, '<div class="chrome"><span class="who"><img src="mark.png"></span><span class="label">00 / 00</span></div>')
        self.assertEqual(rules(html), [])


class Svg(unittest.TestCase):
    CLAIM = '<h2 class="claim">A claim that is a sentence.</h2>'

    def test_an_inline_svg_is_a_figure(self):
        body = self.CLAIM + '<ul class="ticks"><li>Read this curve</li></ul><svg viewBox="0 0 1 1"><g><circle/></g></svg>'
        self.assertEqual(rules(slide(body)), [])

    def test_three_inline_svgs_are_too_many(self):
        body = self.CLAIM + '<svg viewBox="0 0 1 1"></svg>' * 3
        self.assertIn((1, "figures"), rules(slide(body)))

    def test_a_nested_svg_counts_once(self):
        body = self.CLAIM + '<svg viewBox="0 0 2 2"><svg viewBox="0 0 1 1"></svg><svg viewBox="0 0 1 1"></svg></svg>'
        self.assertEqual(rules(slide(body)), [])

    def test_a_mark_is_not_a_figure(self):
        body = self.CLAIM + '<ul class="ticks"><li>one</li></ul><span class="mark"><svg viewBox="0 0 1 1"></svg></span>'
        self.assertIn((1, "list-no-evidence"), rules(slide(body)))

    def test_only_the_stage_of_a_built_deck_is_read(self):
        built = ('<html><body><main class="deck-stage" id="deckStage">' + slide(self.CLAIM + '<img src="a.png">')
                 + "</main><script>/* one <section class='slide'><h2>Results</h2></section> per slide */</script></body></html>")
        self.assertEqual(rules(lint.stage(built)), [])
        self.assertEqual(lint.numbered(lint.stage(built)), 1)


class Scope(unittest.TestCase):
    def test_backup_slides_are_skipped(self):
        html = slide("<h2>Keys</h2>", 'class="slide dark" data-slide="09" data-backup')
        self.assertEqual(rules(html), [])

    def test_lint_off_skips_a_slide_and_a_named_rule_skips_one_rule(self):
        self.assertEqual(rules(slide("<h2>Results</h2>", 'class="slide dark" data-slide="02" data-lint="off"')), [])
        got = rules(slide("<h2>Results</h2>", 'class="slide dark" data-slide="02" data-lint="headline-topic"'))
        self.assertNotIn((1, "headline-topic"), got)

    def test_slide_numbers_follow_the_file(self):
        html = slide('<h2 class="claim">A claim that is a sentence.</h2><img src="a.png">') + slide("<h2>Results</h2><img src='a.png'>")
        self.assertEqual(rules(html), [(2, "headline-topic")])

    def test_comments_are_ignored(self):
        html = "<!-- <section class='slide'><h2>Results</h2></section> -->" + slide('<h2 class="claim">A claim that is a sentence.</h2><img src="a.png">')
        self.assertEqual(rules(html), [])


class Count(unittest.TestCase):
    def test_numbered_leaves_out_backup_slides_and_comments(self):
        html = ("<!-- <section class='slide'></section> -->" + slide("<h2>A.</h2>")
                + slide("<h2>B.</h2>", 'class="slide dark" data-slide="09" data-backup'))
        self.assertEqual(lint.numbered(html), 1)

    def test_words_in_a_structured_list_are_not_counted(self):
        body = '<h2 class="claim">A claim that is a sentence.</h2><ol class="asks"><li>' + "w " * 80 + "</li></ol>"
        self.assertEqual(rules(slide(body)), [])


class Pace(unittest.TestCase):
    def test_more_than_the_rate_is_a_note(self):
        self.assertTrue(lint.pace(slides=12, seconds=300, rate=1.5))
        self.assertIsNone(lint.pace(slides=6, seconds=300, rate=1.5))
        self.assertIsNone(lint.pace(slides=6, seconds=0, rate=1.5))


if __name__ == "__main__":
    unittest.main()

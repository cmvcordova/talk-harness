#!/usr/bin/env python3
"""Lint a deck against the rules for slides that have evidence behind them.

    python3 tools/deck.py lint            # warnings; exit 0
    python3 tools/deck.py lint --strict   # exit 1 if anything is named

The rules, and where each comes from:

  headline-missing   a content slide has no headline
  headline-topic     the headline is a topic ("Results"), not a sentence.
                     Assertion-evidence slides (a sentence headline, visual
                     evidence under it) gave better comprehension and recall
                     than topic headlines with bullets: Garner & Alley, Int.
                     J. Engineering Education 29(6), 2013, n = 110.
  headline-long      the headline has more words than `claim_max_words` (18).
                     The tested decks kept headlines to two lines.
  words              more than `body_max_words` (45) words outside the
                     headline, labels, footer, tables, figures and
                     structured lists. The assertion-evidence deck in that
                     study averaged 21 words a slide; the deck it beat
                     averaged 41.
  list-no-evidence   the body is a bullet list with no figure, table or
                     number. A numbered list of questions (ol.asks), of
                     findings (ol.findings) or a ledger is evidence in itself.
  figures            more than `max_figures` (2) figures or tables. One
                     message per slide: Doumont; Naegle, PLoS Comput Biol 2021.
  pace               more than `slides_per_minute` (1.5) numbered slides for
                     each minute the outline sums to. A note, not a warning.

Two more are measured in the browser by the deck's own check mode, since
they depend on how the text wraps: `headline-lines` (more than two lines)
and `small-text` (running text under `min_px`, 24).

A slide opts out with data-lint="off", or out of single rules with
data-lint="words figures". Backup slides are never linted. Thresholds are
set in deck.toml under [lint].
"""
import re
from dataclasses import dataclass
from html.parser import HTMLParser

DEFAULTS = {"claim_max_words": 18, "body_max_words": 45, "max_figures": 2,
            "slides_per_minute": 1.5, "min_px": 24}
SECTION = re.compile(r"<section\b.*?</section>", re.S)
HEADLINE_TAGS = {"h1", "h2"}
HEADLINE_CLASSES = {"claim", "pull"}
# text inside these is not the body: the band at the top, the footer, labels, credits
QUIET = {"chrome", "footband", "label", "kicker", "status", "credit", "wordmark", "lockup", "cite", "caption", "src"}
# an image inside these is a logo or a mark, not evidence
NOT_A_FIGURE = {"chrome", "partners", "who", "lockup", "mark", "credit"}
# a list inside these is structured: it is the evidence
STRUCTURED = {"asks", "findings", "ledger"}
VOID = {"img", "br", "hr", "input", "meta", "link", "source", "wbr"}


@dataclass
class Problem:
    slide: int
    rule: str
    message: str

    def __str__(self):
        return f"LINT slide {self.slide:02d}: {self.rule}: {self.message}"


class _Slide(HTMLParser):
    """Walk one <section> and collect its headline, body words, lists and figures."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []            # (tag, classes) of open elements
        self.headline = None       # text of the first headline
        self._in_headline = 0
        self.body_words = 0
        self.figures = 0
        self.bare_list = False
        self.has_number = False
        self.has_chrome = False

    def _inside(self, names):
        return any(c in names for _, cls in self.stack for c in cls)

    def handle_starttag(self, tag, attrs):
        cls = set((dict(attrs).get("class") or "").split())
        if "chrome" in cls:
            self.has_chrome = True
        if "stat" in cls:
            self.has_number = True
        figure = tag in ("img", "table") or (tag == "canvas" and "fig-full" not in cls)
        if figure and not self._inside(NOT_A_FIGURE) and not cls & NOT_A_FIGURE:
            self.figures += 1
        if tag in ("ul", "ol") and not cls & STRUCTURED and not self._inside(STRUCTURED):
            self.bare_list = True
        if tag in VOID:
            return
        self.stack.append((tag, cls))
        if self.headline is None and not self._in_headline and (tag in HEADLINE_TAGS or cls & HEADLINE_CLASSES) \
                and not self._inside(QUIET):
            self._in_headline = len(self.stack)
            self.headline = ""

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                if self._in_headline and i < self._in_headline:
                    self._in_headline = 0
                del self.stack[i:]
                break
        if self._in_headline and len(self.stack) < self._in_headline:
            self._in_headline = 0

    def handle_data(self, data):
        if not data.strip():
            return
        if self._in_headline:
            self.headline += data
        elif not self._inside(QUIET | STRUCTURED) and not any(t in ("script", "style", "table", "figure") for t, _ in self.stack):
            self.body_words += len(data.split())      # a table, a figure and a structured list are evidence: not counted


def _attr(tag, name):
    m = re.search(rf'{name}="([^"]*)"', tag)
    return m.group(1) if m else None


def lint_slides(html, cfg=None):
    """Problems for every numbered slide in `html` (the slides file or the built deck)."""
    cfg = {**DEFAULTS, **(cfg or {})}
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    out = []
    for n, m in enumerate(SECTION.finditer(html), 1):
        block = m.group(0)
        tag = block[: block.index(">") + 1]
        if "data-backup" in tag:
            continue
        skip = set((_attr(tag, "data-lint") or "").split())
        if "off" in skip:
            continue
        s = _Slide()
        s.feed(block)
        found = []
        head = " ".join((s.headline or "").split())
        if s.has_chrome and not head and not s.has_number:   # on a one-number slide the number is the headline
            found.append(("headline-missing", "a content slide with no headline"))
        if head and s.has_chrome:      # a cover or a lone sentence has a title, not a claim
            words = head.split()
            if len(words) < 4 and head[-1] not in ".?!":
                found.append(("headline-topic", f'"{head}" names a topic; write the sentence the slide proves'))
            if len(words) > cfg["claim_max_words"]:
                found.append(("headline-long", f'{len(words)} words in the headline (limit {cfg["claim_max_words"]})'))
        if s.body_words > cfg["body_max_words"]:
            found.append(("words", f'{s.body_words} words under the headline (limit {cfg["body_max_words"]}); say them, and show the evidence'))
        if s.bare_list and not s.figures and not s.has_number:
            found.append(("list-no-evidence", "a bullet list with no figure, table or number beside it"))
        if s.figures > cfg["max_figures"]:
            found.append(("figures", f'{s.figures} figures or tables (limit {cfg["max_figures"]}); one message per slide'))
        out += [Problem(n, rule, msg) for rule, msg in found if rule not in skip]
    return out


def numbered(html):
    """How many slides of the talk `html` holds, backup slides left out."""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return sum("data-backup" not in m.group(0)[: m.group(0).index(">") + 1] for m in SECTION.finditer(html))


def pace(slides, seconds, rate):
    """A note when the deck has more slides for its minutes than `rate` allows, else None."""
    if not seconds or slides / (seconds / 60) <= rate:
        return None
    return (f"LINT pace: {slides} slides in {seconds // 60}:{seconds % 60:02d} is "
            f"{slides / (seconds / 60):.1f} a minute (note above {rate})")

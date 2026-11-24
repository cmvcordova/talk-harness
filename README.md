# talk-harness

A small system for building talks as one HTML file, with the rules that keep
them honest built into the build. Claude Code drives it: you answer a brief,
it writes the outline, the slides and the figures, checks every slide, and
hands you a deck and a PDF.

Decks from this system have a fixed 1920×1080 stage that scales to any
screen, live figures drawn on canvas, speaker notes, a numbering that
follows the file, a build that lists every placeholder and sums the talk
time, and a check that reports anything that overflows a slide.

## You need

- Python 3.11 or newer
- Google Chrome or Chromium (for the check, the screenshots and the PDF)
- [Claude Code](https://claude.com/claude-code)

Nothing is installed. There are no packages.

## Start a talk

By hand, copy the harness into a folder for the talk (or install the skill
below and let Claude do this):

```
git clone https://github.com/cmvcordova/talk-harness.git
python3 talk-harness/tools/deck.py new my-talk
cd my-talk
```

Answer the questions in `brief.md`. Then open Claude Code in the folder and
say:

```
build my talk from brief.md
```

Claude reads `CLAUDE.md`, which tells it what to do and what it may not do.
It will ask about any answer you left blank, show you the outline, then
build the deck, screenshot every slide, run the overflow check and export
the PDF. From there you talk to it: "slide 4 is too dense", "the kicker on 7
is wrong", "we lost two minutes, cut one slide".

## Make it a skill

So that "let's make a presentation" always lands here, link the skill into
Claude Code's personal skills folder once:

```
ln -s ~/code/talk-harness/skill ~/.claude/skills/new-talk
```

From then on, in any folder, say "new talk for the lab meeting on the 20th"
or type `/new-talk`. Claude clones or updates the harness, stamps the folder
next to your other talks, fills the brief from what you said, asks only for
what is still blank, and hands over to the folder's `CLAUDE.md`.

## What you get

```
my-talk/
  talk.html        the deck, one file; open it in a browser
  talk.pdf         the backup, one slide per page
  outline.md       order, timings, what is said, where every fact came from
  brief.md         your answers
  _src/            the slides, the figures and the theme
  assets/          media the deck links
  sources/         citations and other evidence the build reads
  shots/           a screenshot of every slide
```

## Presenting

Open `talk.html` in a browser. Keys:

| key | does |
|---|---|
| ← → space | previous, next |
| `#12` in the URL | open on slide 12 |
| N | speaker notes. Turn it off before sharing a screen. |
| E, then Ctrl+S | edit text in place, download the edited file |
| F | fullscreen |

Media is linked from `assets/`, so share the folder or build one portable
file with `python3 _src/build.py --embed-media`.

## What the build enforces

Every `python3 _src/build.py` prints a report like this:

```
  media: linked from assets/
  citations: 2 sources linked across 8 slides
  numbering: 7 slides in the talk, 1 backup
  placeholder on slide 05: TODO the AUROC from table 3
  no Source line in outline.md for slide 06 · The cohort
  timing: 18:30 summed from outline.md (limit 20:00)
built talk.html — 47,684 bytes, 7 slides, 1 things to fix
```

Slide numbers come from document order. Speaker notes come from the outline.
Placeholders are listed. Timing is summed, never estimated. A slide whose
outline entry has no `Source` line is named. The build fails on a raw double
quote inside a note, a figure name that `viz.js` does not define, or a slide
with no outline entry.

`python3 tools/deck.py check` loads the deck headless and reports every
element that leaves the 1920×1080 stage, every text box that clips its own
content, and every image that did not load. Exit code 1 means something to
fix.

`python3 tools/deck.py lint` names the slides that break the rules for
slides with evidence behind them: a headline that is a topic and not a
sentence, a headline over two lines, more than 45 words under it, a bullet
list with no figure beside it, more than two figures, running text under
24 px. Each rule and the study it comes from is in `tools/lint.py`. A slide
opts out with `data-lint="off"`; the thresholds are set under `[lint]` in
`deck.toml`.

## Skins

A skin puts a house style on a deck without touching the engine. It is a
folder:

```
my-skin/
  skin.toml     name, fonts (a Google Fonts URL, or "" for system fonts),
                about (one line), home (the folder this house's talks live in)
  skin.css      token overrides and brand rules; pasted after deck.css
  assets/       marks and logos; copied into the talk's assets/
  starter/      optional: slides.html, outline.md a new talk starts from
  starters/x/   optional: named starters, chosen with --starter x
  SKIN.md       optional: the house rules; copied into the talk
```

Stamp a talk with it, by path or by name:

```
python3 talk-harness/tools/deck.py new my-talk --skin path/to/my-skin --starter x
```

A name is looked up in `$TALK_SKINS`, then `~/.config/talk-harness/skins/`,
then `talk-harness/skins/`. `deck.py skins` lists what it finds. After a
skin changes, `deck.py reskin --skin NAME` in a talk folder copies the new
stylesheet and assets in and leaves the slides alone.

Every ground in the theme sets five local properties: `--ground`, `--ink`,
`--ink-2`, `--ink-3`, `--bd`. Components read only those. So a skin adds a
ground in one rule:

```css
.slide.sand{--ground:#d8c9a8;--ink:#1f1b16;--ink-2:#4a443b;--ink-3:rgba(31,27,22,.62);--bd:#b9a57e}
```

`__INLINE_name.svg__` in a slide pastes an SVG from `assets/` into the
page, so a mark drawn with `currentColor` takes the colour of its place.

## The example deck

The repo root is itself a working talk: eight slides that use every layout
in the theme and explain the rules. Build it and look:

```
python3 tools/deck.py serve
```

## Editing by hand

Everything Claude does, you can do: edit `outline.md` and `_src/slides.html`,
run the build, open the file. `CLAUDE.md` is also the human manual; the
"Layouts in the theme" section lists every class.

## Re-skinning

The theme is the "Mat" palette: deep forest, warm cream, one burnt-orange
accent. The tokens at the top of `_src/deck.css` are the whole re-skin.
Fonts are set in `deck.toml`.

## Credits

`_src/viewport-base.css` is from
[zarazhangrui/frontend-slides](https://github.com/zarazhangrui/frontend-slides)
(MIT). Everything else is MIT, see `LICENSE`.

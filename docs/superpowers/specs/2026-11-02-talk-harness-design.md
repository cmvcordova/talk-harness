# talk-harness — design

Date: 2026-11-02. Author: César Valdez Córdova with Claude.

## Intent

Five decks (co-science pitch, PUCP, Wolf lab, Kindler, and the first geomancer
pitch) were built with the same system: one outline as the source of truth,
a `_src/` folder of four files that build into one HTML file, and a build
script that lists every placeholder, sums the timings and refuses to lie.
Labmates asked for it. This repo is that system, stripped of every talk, with
two front doors: a README for a person and a `brief.md` + `CLAUDE.md` so
Claude Code builds a deck from whatever context the labmate hands it.

The deck is driven by Claude end to end. Editing by hand is possible and is a
footnote, not the path.

## Goals

- A labmate clones, answers `brief.md`, opens Claude Code, says "build my
  talk from brief.md", and ends with a built deck, screenshots of every slide,
  an overflow report and a PDF.
- Every rule that made the previous decks honest is enforced by the build or
  written in `CLAUDE.md`: numbers trace to files or read `TODO[value]`,
  placeholders are listed on every build, timing is summed, limits are stated
  where they occur.
- Zero dependencies beyond Python 3.11+, Chrome, and Claude Code.

## Non-goals

- A theme picker. One theme ships (the "Mat" palette). Tokens are at the top
  of `deck.css`; changing them is the whole job of re-skinning.
- Markdown-to-slides. Slides are HTML, authored by Claude.
- Any content from the previous talks.

## Anti-goals

- A deck that builds with a silent placeholder, an unsourced number, or a
  slide that overflows the stage.
- Anything that reads as a product (manifoldwerks tokens, lockups, URLs).

## Layout of the repo

```
talk-harness/
  README.md            the labmate's page
  brief.md             questions answered before any slide exists
  CLAUDE.md            how Claude turns the brief into a deck; the rules
  outline.md           template: order, timings, notes, source per slide
  deck.toml            title, output file, language, media folder, time limit, fonts
  _src/
    build.py           outline + slides + css + js -> one HTML file
    slides.html        the example deck (eight slides that show every layout)
    deck.css           theme tokens + the shared system
    viewport-base.css  vendored from zarazhangrui/frontend-slides (MIT)
    controller.js      stage, navigation, notes, edit mode, figure lifecycle, check mode
    viz.js             the visual contract + two example visuals
  tools/
    deck.py            serve | shots | check | pdf | new
  tests/
    test_build.py      unittest, no pytest needed
  LICENSE              MIT
```

The repo root is itself a working talk. `tools/deck.py new ../my-talk` copies
the skeleton (everything but `tests/`, `docs/`, `.git`) into a new folder.

## deck.toml

```toml
title  = "A talk"            # <title> and the cover
output = "talk.html"         # built file, next to deck.toml
lang   = "en"
media  = "assets"            # folder the build links media from
limit  = "20:00"             # the build warns when the outline sum passes it
fonts  = "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700;12..96,800&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700&family=DM+Mono:wght@400;500&display=swap"
```

The localStorage key and the download name of the edit mode derive from
`output`'s stem.

## outline.md

One `## NN · Title` heading per slide. Under it, a list with these fields,
each optional: `Time:`, `Notes:`, `Source:`, `Visual:`, `Beat:`. The Spanish
names `Tiempo`, `Notas`, `Fuente` are accepted too, so the author's own decks
still build. `Time` is `m:ss`. Slides in `_src/slides.html` carry
`data-slide="NN"`; the build copies that slide's `Notes` into `data-notes`,
escaped. If the slide already has `data-notes`, the outline wins and the build
says so.

## build.py

Reads `deck.toml`, `outline.md`, `_src/*`. Writes `output`. Prints a report.
Exits non-zero on: unbalanced quote in `data-notes`, a missing `data-viz`
name, a slide number in `data-slide` with no outline entry. Prints but does
not fail on: placeholders (`<span class="ph">`), missing media, timing over
the limit, slides with no `Source` line.

Rules it applies, in order:

1. `__VIEWPORT_BASE__` in deck.css is replaced with the vendored file.
2. `__MEDIA_name.ext__` becomes `media/name.ext`, or a data URI with
   `--embed-media`. Missing files are listed.
3. `data-cite="key other"` on a `<section>` fills that slide's
   `<span class="cites"></span>` with links from `sources/citations.json`
   (`{key: {label, url}}`), and `__SOURCES_LIST__` anywhere becomes the list
   of every cited source with the slides it appears on. Both are no-ops when
   the file does not exist.
4. Notes are injected from the outline by `data-slide`.
5. Slide numbers: any text matching `NN / NN` inside a section is rewritten
   from document order. Sections with `data-backup` are labelled `Backup`
   and do not count toward the total.
6. Placeholders are listed per slide.
7. Timing is summed from the outline and compared with `limit`.

## controller.js

As in the previous decks: fixed 1920×1080 stage scaled as a unit; arrows,
space, PageUp/Down, Home/End, wheel, touch; `#n` deep link; `N` notes panel;
`E` edit mode and Ctrl+S download; one animation loop, only the visible
slide's canvases run; `?t=<s>` freezes every visual and marks the body
`settled`; `beforeprint` renders every figure at its `printAt`.

New: `?check=1`. The stage is scaled to 1, every slide is shown in turn, and
for each slide the controller logs to the console one line per problem:

```
CHECK slide 03: overflow <h2.reveal> right=1931 bottom=640
CHECK slide 05: broken image assets/fig.png
CHECK slide 07: clipped text <p.lead> scrollHeight=420 clientHeight=300
CHECK done: 8 slides, 3 problems
```

An element with `data-offstage` is skipped (for things that animate in from
outside). Elements with zero size are skipped.

## viz.js

```js
VIZ['name'] = function(canvas){ ...; return {printAt: 4, reset(){}, frame(t){}} }
```

`frame(t)` is called with seconds since the slide became visible, plus `?t=`.
`reset()` is called each time the slide is entered. `PRINTING` is true during
print; a visual that leaves pixels transparent must paint its own ground then.
Helpers shipped: `mkRnd(seed)`, `gauss(rnd)`, `smoothstep`, `rgba`, `ground`,
`arrowHead`, `FONT`. Two visuals ship: `drift` (ambient points on a slow
field, for covers) and `scatter-labels` (points settle into groups, labels
arrive in order; a schematic).

## tools/deck.py

Subcommands, all zero-dependency:

- `serve [port]`: builds, serves the deck folder on 127.0.0.1, opens the
  browser at the deck.
- `shots [out_dir]`: builds, screenshots every slide at `?t=1#n` with headless
  Chrome at 1920×1080, writes `shots/NN.png`. Prints the paths.
- `check`: builds, loads `?check=1&t=1` headless with console logging, prints
  every `CHECK` line, exits 1 if problems > 0.
- `pdf`: builds, exports `<output stem>.pdf` with headless Chrome, prints page
  count.
- `new <dir>`: copies the skeleton into `<dir>`.

Chrome is found at the macOS path, then `google-chrome`, `chromium`,
`chromium-browser` on PATH, then `$CHROME`. A clear error otherwise.

## brief.md

Headings with a blank answer line under each. The questions are the ones
asked at the start of every previous deck: who is in the room and what they
already know; the one thing they leave with; length and question time;
language; date and venue; what results exist and where they live on disk
(paths); what must not be said or shown; what the speaker was complimented
on last time; existing material to reuse.

## CLAUDE.md

Tells Claude: read `brief.md` first, ask for any blank answer that changes
the deck, then write `outline.md` before any slide, then slides, then build,
`tools/deck.py check`, `tools/deck.py shots`, look at every screenshot, fix,
`tools/deck.py pdf`, and only then say done. The rules: every number traces
to a file named in the slide's Source line or reads `TODO[value]`; a figure
that is an illustration says so on its own face; limits are stated where they
occur; speaker notes live in the outline; words on slides live in
`slides.html`; no "not X, but Y"; no intensifiers; a style pass removes
words; the audience has met every term before it appears on a slide; timing
is summed, never estimated; the notes panel is off when sharing a screen.

## README.md

For the labmate. Three steps: clone, fill `brief.md`, open Claude Code and
type the one-line prompt. Then the keys, what the build prints, and a
footnote on editing by hand. Requirements: Python 3.11+, Chrome, Claude Code.

## Left to the builder

- Exact copy of the example deck's eight slides, as long as they show: cover
  with a live field, a dark slide with chrome and a two-column body, a cream
  slide with a table, a stat slide, a slide with a media placeholder, a
  canvas schematic with its footer disclaimer, a Sources slide, a backup slide.
- The ambient field's maths.
- Test fixtures.

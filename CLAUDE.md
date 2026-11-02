# CLAUDE.md — a talk built with talk-harness

This folder is one talk. You build it, end to end, from `brief.md`. The
person presenting answers the brief, opens Claude Code here, and says
"build my talk from brief.md". From then on the work is yours. They look at
screenshots and tell you what to change.

## The job, in order

1. Read `brief.md`. If an answer that changes the deck is blank (the room,
   the one thing, the length, what exists on disk), ask for it before
   anything else. Ask all the questions in one message.
2. Read every path the brief names. Note what is on disk and what is not.
   Nothing that is not on disk or at a URL the brief gave becomes a number
   on a slide.
3. Write `outline.md` before any slide: one `## NN · Title` per slide with
   `Time`, `Notes`, `Source`, `Visual`, `Beat`. Sum the times; fit the
   length in the brief with the question time left over. Show the outline
   to the person and wait for them before building slides, unless they
   told you to go straight through.
4. Write `_src/slides.html`, one `<section>` per outline entry, with
   `data-slide="NN"`. Words on slides live here; words that are spoken live
   in the outline.
5. Draw figures. A figure of data is made by a script in `figures/` that
   reads a committed file and writes to `assets/`. A figure that explains an
   idea is a `<canvas data-viz>` in `_src/viz.js` or an SVG, and the slide
   says on its face that it is an illustration.
6. Build, check, look, fix, export. The commands are below. Do not say the
   deck is done until the check reports zero problems, you have opened every
   screenshot and looked at it, and the PDF has one page per slide.

## Rules

Honesty:

- Every number on a slide traces to a file named in that slide's `Source`
  line in the outline, or the slide reads `TODO[value]`. Never type a number
  from memory.
- A figure that is an illustration says so where the figure is, not at the
  end of the talk.
- A limit is stated where it occurs, on the slide the claim is on.
- A `<span class="ph">...</span>` marks anything still to write or draw. The
  build lists every one. Never present a deck with one in it.
- Timing is summed from the outline by the build. Never estimate it.

Audience:

- Every term the room has not met is introduced out loud before it appears
  on a slide. If a word is on a slide before it was explained, that is a bug.
- One idea per slide. If a slide needs a paragraph, it is two slides.

Prose, in any language:

- No "not X, but Y" as a rhetorical move.
- No intensifiers: really, truly, very, extremely.
- No throat-clearing: "it is important to note", "note that".
- Plain verbs: use, make, show. Not utilize, implement, demonstrate.
- A style pass removes words. If an edit makes a line longer without making
  it clearer, revert it.
- A slide never reads like a paragraph from a paper.

Presenting:

- The notes panel (N) is off before sharing a screen.
- Backup slides go after the last numbered slide with `data-backup`. They
  are not numbered and not timed.

## Files

| Path | Owns |
|---|---|
| `brief.md` | the answers everything follows from |
| `outline.md` | order, timings, speaker notes, source per slide |
| `deck.toml` | title, output file, language, media folder, time limit, fonts |
| `_src/slides.html` | the words and layout on screen |
| `_src/viz.js` | live figures: `VIZ['name'] = canvas => ({printAt, reset, frame(t)})` |
| `_src/deck.css` | the theme; tokens at the top are the whole re-skin |
| `_src/build.py` | assembles the deck and enforces the rules above |
| `_src/controller.js`, `_src/viewport-base.css` | the runtime; do not edit for a talk |
| `sources/citations.json` | `{key: {label, url}}`; `data-cite="key"` on a section becomes footer links |
| `assets/` | media, referenced as `__MEDIA_name.ext__` in slides |
| `figures/` | scripts that draw data figures into `assets/` (create when needed) |
| `tools/deck.py` | serve, screenshots, check, PDF |

## Commands

All on the laptop, from this folder.

Build:

```
python3 _src/build.py
```

Report overflow, clipped text and broken images on every slide. Exit code 1
means problems:

```
python3 tools/deck.py check
```

Screenshot every slide to `shots/NN.png`, then open each one and look:

```
python3 tools/deck.py shots
```

One slide, frozen at second 6 of its figures:

```
python3 tools/deck.py shots --slide 3 --t 6
```

Export the PDF backup, one slide per page:

```
python3 tools/deck.py pdf
```

Serve and open in the browser for the person:

```
python3 tools/deck.py serve
```

## Layouts in the theme

Grounds: `dark` (default, wood glow), `cream` (tonal break), `void` (thesis
and close; nothing but the sentence). Chrome: `<div class="chrome"><span
class="label">00 / 00</span></div>` on numbered slides; the build rewrites
the number. Footer: `<div class="footband">`, with `<span class="cites">
</span>` where citations should land. Type: `h1`, `h2`, `.lead`, `.body`,
`.kicker`, `.label`, `.pull`, `.stat`, `em` for the accent colour. Blocks:
`.row` + `.col`, `.cell`, `.info`, `ul.ticks`, `table`, `.plates`,
`.fillbody`. Motion: `.reveal` on the children of a slide, `.r-late` and
`.r-late2` to hold one back.

The example deck in `_src/slides.html` uses every one of these. Replace it;
do not append to it.

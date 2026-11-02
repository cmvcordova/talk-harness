# Outline · A talk built with talk-harness

This file is the source of truth for the talk: slide order, how long each slide
takes, what is said over it, and where every fact on it comes from. Words that
appear on screen live in `_src/slides.html`; words that are spoken live here.

One `## NN · Title` heading per slide. Under it, any of these lines:

- `Time: m:ss`   how long the slide takes. The build sums these and compares
  the total with `limit` in `deck.toml`. Never estimate the total by hand.
- `Notes: ...`   what is said. The build copies it into the slide's notes
  panel (press N). One paragraph; use &quot; for a double quote.
- `Source: ...`  where every number and claim on the slide comes from: a
  file in this folder, a key in `sources/citations.json`, or `TODO[value]`.
  The build names every slide that lacks this line.
- `Visual: ...`  what is on screen, in one line.
- `Beat: ...`    the one thing the room should take from this slide.

Spanish field names (`Tiempo`, `Notas`, `Fuente`) are accepted too.

---

## 01 · Cover
- Time: 0:30
- Visual: the title over a slow drifting field
- Beat: this is what a deck from this harness looks like
- Notes: Say the title. Say who you are and who you work with. Say what the room will leave with, in one sentence.
- Source: none; no facts on this slide

## 02 · What the build enforces
- Time: 1:30
- Visual: two columns of short lines
- Beat: the build refuses to lie for you
- Notes: Every deck from this harness is built by one script. It numbers the slides from their order in the file. It lists every placeholder. It sums the timings from the outline. It fails if a speaker note would break the page. If a number is on a slide, the slide says where it came from.
- Source: _src/build.py; the stage size is from _src/viewport-base.css (citation key frontend-slides)

## 03 · A schematic, and it says so
- Time: 1:30
- Visual: points fly in and settle into groups; four labels arrive with leader lines
- Beat: a drawing that explains an idea must say on its face that it is not data
- Notes: This figure is drawn live by viz.js. The points are made up, and the footer says so. When a figure is an illustration, the slide says it where the figure is, not at the end of the talk.
- Source: schematic; no data. Drawn by VIZ['scatter-labels'] in _src/viz.js

## 04 · The outline fields
- Time: 1:00
- Visual: a cream slide with a table
- Beat: five fields, one file, and the build reads it
- Notes: The outline carries five fields per slide. Time is summed. Notes land in the notes panel. Source is where every fact on the slide came from. Visual and Beat are for the author.
- Source: outline.md, this file

## 05 · One number, and where it came from
- Time: 0:45
- Visual: one large number with its source under it
- Beat: a number alone is a claim; a number with a file is a fact
- Notes: The stage is nineteen-twenty by ten-eighty. The whole stage scales to the screen as one unit, so nothing reflows. That number is in viewport-base.css, and the slide says so.
- Source: _src/viewport-base.css, section 3 (citation key frontend-slides)

## 06 · A figure from a file
- Time: 1:00
- Visual: an SVG figure linked from assets/, with a caption
- Beat: media is linked by default and embedded on request
- Notes: Figures come from the assets folder through a media token. The build links them by default, so the folder ships. Pass embed-media for one portable file. This one is an illustration; the figure says so on its own face.
- Source: assets/example-figure.svg, an illustration drawn for this deck; PDF export per citation key chrome-headless

## 07 · Sources
- Time: 0:30
- Visual: every source the deck cited, with the slides it appears on
- Beat: the list writes itself from sources/citations.json
- Notes: Everything cited in the deck is listed here, with the slide it was used on. The build writes this list, so it cannot drift from the slides.
- Source: sources/citations.json

## 08 · Keys
- Time: 0:00
- Visual: a backup slide; not counted in the talk
- Beat: what to press
- Notes: A backup slide. It is not numbered and does not count toward the time.
- Source: _src/controller.js

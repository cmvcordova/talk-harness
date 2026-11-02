# talk-harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A public, zero-dependency repo that Claude Code drives from a brief to a built, checked HTML deck plus PDF.

**Architecture:** Static files only. `_src/build.py` assembles `deck.css` + `controller.js` + `viz.js` + `slides.html` into one HTML, enforcing the honesty rules. `tools/deck.py` wraps headless Chrome for serve, screenshots, overflow check and PDF. `CLAUDE.md` is the driver; `brief.md` is the input.

**Tech Stack:** Python 3.11+ stdlib (tomllib, unittest, http.server), vanilla JS, CSS, headless Chrome.

**Spec:** `docs/superpowers/specs/2026-11-02-talk-harness-design.md`

## Global Constraints

- Python 3.11+ only; no third-party packages anywhere.
- No talk content, no manifoldwerks tokens or lockups, no personal URLs.
- `viewport-base.css` keeps its MIT notice (Zara Zhang, 2025).
- Field names in `outline.md`: `Time|Tiempo`, `Notes|Notas`, `Source|Fuente`, `Visual`, `Beat`.
- The stage is 1920×1080 and never reflows.

## Review Focus

- A `data-notes` value containing `&quot;` must pass; a raw `"` must fail (Task 5 test).
- An outline with `Tiempo: 1:05` and `Time: 0:30` sums to 1:35 (Task 5 test).
- A section marked `data-backup` keeps "Backup" and is excluded from the total (Task 5 test).
- `?check=1` on the example deck reports 0 problems; a deliberately widened element reports 1 (Task 7 verification).
- `deck.py` on a machine without Chrome prints one clear line and exits 2 (Task 7 test).

---

### Task 1: Skeleton, license, config

**Files:** Create `LICENSE`, `.gitignore`, `deck.toml`, `_src/viewport-base.css`, `_src/deck.css`.

- [ ] Write `LICENSE` (MIT, César Miguel Valdez Córdova, 2026) with a second section reproducing the MIT notice for `viewport-base.css`.
- [ ] Write `.gitignore`: `*.pdf`, `shots/`, `__pycache__/`, `.DS_Store`.
- [ ] Write `deck.toml` exactly as in the spec.
- [ ] Copy `viewport-base.css` from the frontend-slides skill, header credit added.
- [ ] Write `deck.css`: tokens, grounds, type, chrome, layout helpers (`row`, `col`, `stack`, `info`, `cell`, `ticks`, `table`, `credit`, `plates`, `ph`), live figures (`fig`, `fig-full`, `fig-cap`, `scrim`, `scrim-soft`), motion (`reveal`, `r-late`, `settled`), deck chrome, print, notes panel, edit affordance. Nothing talk-specific.
- [ ] Commit: `chore: skeleton, license, theme`.

### Task 2: controller.js with check mode

**Files:** Create `_src/controller.js`.

**Produces:** globals `VIZ`, `TOFF`, `PRINTING` are consumed from viz.js; `Deck` and `Editor` classes; `?check=1` logs `CHECK ...` lines.

- [ ] Port the Deck and Editor classes; storage key and download name come from `const DECK_ID = '__DECK_ID__'` which build.py fills from `output`'s stem.
- [ ] Add `Deck.check()`: set scale 1, for each slide show it, measure every descendant with `getBoundingClientRect` relative to the stage, log overflow when right > 1921 or bottom > 1081 or left < -1 or top < -1; log clipped text when `scrollHeight > clientHeight + 2` on elements with `overflow` not visible; log broken images when `img.complete && naturalWidth === 0`; skip `[data-offstage]` and zero-size elements; finish with `CHECK done: N slides, K problems`.
- [ ] Run check mode when `new URLSearchParams(location.search).has('check')`.
- [ ] Commit: `feat: controller with check mode`.

### Task 3: viz.js

**Files:** Create `_src/viz.js`.

- [ ] Helpers: `mkRnd`, `gauss`, `clamp01`, `smoothstep`, `rgba`, `ground`, `arrowHead`, `FONT`; `TOFF`, `PRINTING`, `REDUCE`.
- [ ] `VIZ['drift']`: 600 points advected by a sum of three sine fields; paper-coloured; `printAt: 6`.
- [ ] `VIZ['scatter-labels']`: three groups settle from random positions, four labels with leader lines arrive at 2.2, 3.8, 5.4, 7.0 s; `printAt: 9`.
- [ ] Commit: `feat: viz contract and two example visuals`.

### Task 4: build.py, test-first

**Files:** Create `_src/build.py`, `tests/test_build.py`, `tests/fixtures/` (a mini deck).

**Produces:** `build(root: Path, embed: bool=False) -> Report` where `Report` has `html: str`, `lines: list[str]`, `problems: int`, `total: int`; `main()` prints lines and writes the file.

- [ ] Write tests: `test_renumbers_from_document_order`, `test_backup_unnumbered`, `test_lists_placeholders`, `test_raw_quote_in_notes_fails`, `test_sums_time_both_languages`, `test_injects_notes_by_data_slide`, `test_media_tokens_link_and_embed`, `test_citations_fill_footband_and_sources`, `test_unknown_viz_fails`, `test_limit_warning`.
- [ ] Run `python3 -m unittest -v`; expect ImportError.
- [ ] Implement `build.py` per spec section "build.py".
- [ ] Run tests; expect all pass.
- [ ] Commit: `feat: build with the honesty checks`.

### Task 5: outline and the example deck

**Files:** Create `outline.md`, `_src/slides.html`.

- [ ] Write `outline.md` with eight entries, `Time` on each, `Notes` on each, `Source` on every slide that states a fact.
- [ ] Write the eight slides listed in the spec, each `<section class="slide ..." data-slide="NN">`, chrome label `00 / 00` where numbered.
- [ ] `python3 _src/build.py`; expect "built talk.html", 0 placeholders unless intended, timing line.
- [ ] Commit: `feat: example deck`.

### Task 6: tools/deck.py

**Files:** Create `tools/deck.py`, `tests/test_tools.py`.

- [ ] Test `find_chrome` returns `None` when `PATH` is empty and `CHROME` unset and the macOS path is absent (monkeypatch `os.path.exists`).
- [ ] Implement `find_chrome()`, `serve(port)`, `shots(out)`, `check()`, `pdf()`, `new(dest)` with `argparse`.
- [ ] Run `python3 tools/deck.py check` on the example; expect `CHECK done: 8 slides, 0 problems`.
- [ ] Run `python3 tools/deck.py shots`; open the PNGs and look.
- [ ] Run `python3 tools/deck.py pdf`; expect 8 pages.
- [ ] Commit: `feat: deck tools`.

### Task 7: brief, CLAUDE.md, README

**Files:** Create `brief.md`, `CLAUDE.md`, `README.md`.

- [ ] Write each per the spec sections of the same name.
- [ ] `python3 tools/deck.py new /tmp/x` and build there; expect success.
- [ ] Commit: `docs: brief, driver, readme`.

---
name: new-talk
description: Use when the user wants a new presentation, talk, deck, slides, pitch, lightning talk or show-and-tell, or types /new-talk. Load before writing any slide, before copying files from an older deck, and before reaching for the frontend-slides skill.
---

# New talk

Every talk is built with talk-harness. The harness lives at
`~/code/talk-harness`; the talk folder's own `CLAUDE.md` drives the build.
This skill only gets you to that folder with the brief filled in. It does
not replace the folder's `CLAUDE.md`: read that next and follow it.

## Steps

1. **Find the harness.** If `~/code/talk-harness/tools/deck.py` is missing:

   ```
   git clone https://github.com/cmvcordova/talk-harness.git ~/code/talk-harness
   ```

   If it exists, `git -C ~/code/talk-harness pull --ff-only` once per session.

2. **Stamp the folder.** Next to the user's other talks, named
   `YYYY-MM-DD-venue-slug` with the date of the talk:

   ```
   python3 ~/code/talk-harness/tools/deck.py new <parent>/YYYY-MM-DD-venue-slug
   ```

   If the talk belongs to a house (a company, a lab, a project with its own
   look), stamp it with that house's skin. List the skins on this machine;
   each one names its starters and the folder its talks live in:

   ```
   python3 ~/code/talk-harness/tools/deck.py skins
   ```

   Then stamp inside that folder, with the starter that fits the room:

   ```
   python3 ~/code/talk-harness/tools/deck.py new <skin's home>/YYYY-MM-DD-venue-slug --skin <name> --starter <starter>
   ```

   A talk with no house goes next to the user's other talks, with no skin.

   Never copy `_src/` from an older deck. The stamped folder has the whole
   system and no content: a one-slide `outline.md` and `slides.html` to
   replace, an empty `sources/citations.json`, an empty `assets/`. The
   per-talk constants live in `deck.toml`. The harness root itself is the
   example deck; look at its `_src/slides.html` for every layout.

3. **Fill `brief.md`** with what the user already said. Then ask, in one
   message, only the brief's questions that are still blank and change the
   deck: the room, the one thing they leave with, length and question time,
   language, what exists on disk and where, what must not be said.

4. **Set `deck.toml`**: title, output file name, language, time limit.

5. **Hand over.** `cd` into the folder, read its `CLAUDE.md`, and follow it:
   outline first and shown to the user, then slides, build, check, shots,
   PDF. The folder's `CLAUDE.md` wins over any parent `CLAUDE.md` for how
   the deck is built. Audience and language rules written for a different
   talk in a parent `CLAUDE.md` do not apply.

6. **Register it.** If the parent folder is a git repo with a README table
   of talks, add a row. Commit on a branch named after the folder.

## Material from older talks

Reuse data and sources by copying the file into the new `sources/` and
naming it in the outline's `Source` line. Reuse a figure script by copying it
into `figures/`. Do not reuse `_src/` files, and do not symlink.

## Improving the system

A fix to `build.py`, `controller.js`, `deck.css` or `tools/deck.py` goes into
`~/code/talk-harness`, committed and pushed, then copied into the talk. A
fix made only inside a talk folder is lost for the next one.

## Common mistakes

| Mistake | Instead |
|---|---|
| Paste brand colours into `_src/deck.css` of one talk | a skin folder, `--skin`, and `reskin` when it changes |
| Skip `deck.py lint` because the check passed | the check finds overflow; the lint finds slides with no claim or no evidence |
| Copy `build.py`, `deck.css`, `controller.js` from the last deck and patch `OUT` by hand | `deck.py new`, then edit `deck.toml` |
| Build slides from the frontend-slides skill's template | the stamped `_src/slides.html`; the theme and runtime are already there |
| Ask a dozen questions in your own words | the brief's blank questions, in one message |
| Write `slides.html` before `outline.md` | outline first, shown to the user |
| Apply a parent `CLAUDE.md` written for another room | the talk's own `brief.md` and `CLAUDE.md` |

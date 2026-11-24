#!/usr/bin/env python3
"""Assemble the deck into one HTML file.

    python3 _src/build.py                 # linked media (ship the folder)
    python3 _src/build.py --embed-media   # one portable file, media inline

Reads deck.toml, outline.md and _src/{deck.css,viewport-base.css,
controller.js,viz.js,slides.html}; writes the file deck.toml names.
If _src/skin.css exists it is pasted after deck.css: a skin overrides the
theme's tokens and adds its own rules (tools/deck.py new --skin).

What it enforces, every build:
  - slide numbers come from document order; data-backup slides are "Backup"
  - speaker notes come from outline.md, matched by data-slide="NN"
  - every <span class="ph"> placeholder is listed
  - media tokens __MEDIA_name.ext__ are resolved, and missing files listed
  - __INLINE_name.svg__ pastes an SVG from the media folder into the slide,
    so a mark can take its colour from the text around it (currentColor)
  - data-cite keys become footer links from sources/citations.json, and
    __SOURCES_LIST__ becomes the list of every source used
  - the talk time is summed from the outline's Time lines, never estimated
  - a slide whose outline entry has no Source line is named
It fails (exit 1) on a raw double quote inside data-notes, a data-viz name
viz.js does not define, and a data-slide with no outline entry.
"""
import argparse, base64, html as _html, json, pathlib, re, sys
from dataclasses import dataclass, field

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    sys.exit("build.py needs Python 3.11 or newer (for tomllib).")

MIME = {".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".gif": "image/gif",
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml",
        ".webp": "image/webp"}
FIELDS = {"time": "time", "tiempo": "time", "notes": "notes", "notas": "notes",
          "source": "source", "fuente": "source", "visual": "visual", "beat": "beat"}
SECTION = re.compile(r"<section\b.*?</section>", re.S)


@dataclass
class Report:
    html: str = ""
    lines: list = field(default_factory=list)
    problems: int = 0
    total: int = 0


def parse_outline(text):
    """{'01': {'title': ..., 'time': '0:30', 'notes': ..., 'source': ...}, ...}"""
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+(\d{1,2})\s*[·.:-]\s*(.*)$", line)
        if m:
            cur = m.group(1).zfill(2)
            out[cur] = {"title": m.group(2).strip()}
            continue
        if line.startswith("#"):
            cur = None
            continue
        if cur is None:
            continue
        f = re.match(r"^-\s+\*{0,2}([A-Za-z]+)\*{0,2}:\s*(.*)$", line)
        if f and f.group(1).lower() in FIELDS:
            key = FIELDS[f.group(1).lower()]
            out[cur][key] = f.group(2).strip()
    return out


def mmss(secs):
    return f"{secs // 60}:{secs % 60:02d}"


def parse_mmss(s):
    m = re.match(r"^\s*(\d+):(\d{2})\s*$", s or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def opening_tag(block):
    return block[: block.index(">") + 1]


def build(root, embed=False):
    root = pathlib.Path(root)
    src = root / "_src"
    cfg = tomllib.loads((root / "deck.toml").read_text())
    rep = Report()
    say = rep.lines.append

    viewport = (src / "viewport-base.css").read_text()
    css = (src / "deck.css").read_text().replace("__VIEWPORT_BASE__", viewport.strip())
    if (src / "skin.css").exists():
        css += "\n/* --- skin: _src/skin.css --- */\n" + (src / "skin.css").read_text()
        say(f"skin: {cfg.get('skin', 'unnamed')} (_src/skin.css)")
    slides = (src / "slides.html").read_text()
    viz = (src / "viz.js").read_text()
    ctl = (src / "controller.js").read_text()
    outline = parse_outline((root / "outline.md").read_text()) if (root / "outline.md").exists() else {}

    # --- media: linked by default, embedded on request --------------------
    media_dir = root / cfg.get("media", "assets")
    missing = []

    def media(fname):
        p = media_dir / fname
        if not p.exists():
            missing.append(fname)
        elif embed:
            return f"data:{MIME.get(p.suffix.lower(), 'application/octet-stream')};base64," + base64.b64encode(p.read_bytes()).decode()
        return f"{media_dir.name}/{fname}"

    for tok, fname in set(re.findall(r"(__MEDIA_([A-Za-z0-9_.-]+)__)", slides)):
        slides = slides.replace(tok, media(fname))
    if missing:
        rep.problems += len(missing)
        say("MISSING MEDIA (the slide will show a broken asset): " + ", ".join(f"{media_dir.name}/{m}" for m in missing))
    say("media: " + ("embedded" if embed else f"linked from {media_dir.name}/"))

    # --- inline SVG: the file's markup goes into the slide ------------------
    gone = []

    def inline(m):
        p = media_dir / m.group(1)
        if not p.exists():
            gone.append(m.group(1))
            return ""
        svg = p.read_text()
        svg = re.sub(r"<\?xml.*?\?>|<!DOCTYPE.*?>|<!--.*?-->", "", svg, flags=re.S)
        return svg.strip()

    slides = re.sub(r"__INLINE_([A-Za-z0-9_.-]+\.svg)__", inline, slides)
    if gone:
        rep.problems += len(gone)
        say("MISSING INLINE SVG (nothing is drawn): " + ", ".join(f"{media_dir.name}/{g}" for g in sorted(set(gone))))

    # --- citations: data-cite keys -> footer links; __SOURCES_LIST__ -------
    cpath = root / "sources" / "citations.json"
    if cpath.exists():
        cites = json.loads(cpath.read_text())
        used, n = {}, 0

        def fill(m):
            nonlocal n
            blk = m.group(0); n += 1
            km = re.search(r'data-cite="([^"]+)"', opening_tag(blk))
            if not km:
                return blk
            links = []
            for k in km.group(1).split():
                if k not in cites:
                    sys.exit(f"build failed: data-cite key '{k}' is not in sources/citations.json")
                c = cites[k]; used.setdefault(k, []).append(n)
                lab = _html.escape(c["label"])
                links.append(f'<a href="{c["url"]}" target="_blank" rel="noopener">{lab}</a>' if c.get("url") else lab)
            return blk.replace('<span class="cites"></span>', '<span class="cites">' + " &middot; ".join(links) + "</span>")

        slides = SECTION.sub(fill, slides)
        rows = []
        for k, on in used.items():
            c = cites[k]
            where = ", ".join(str(i) for i in sorted(set(on)))
            link = (f'<a href="{c["url"]}" target="_blank" rel="noopener">{_html.escape(c["url"])}</a>'
                    if c.get("url") else '<span class="on">no public URL</span>')
            rows.append(f'<div class="src"><b>{_html.escape(c["label"])}<span class="on">slide {where}</span></b>{link}</div>')
        slides = slides.replace("__SOURCES_LIST__", "\n".join(rows))
        say(f"citations: {len(used)} sources linked across {n} slides")
    elif "__SOURCES_LIST__" in slides or "data-cite=" in slides:
        say("citations: sources/citations.json not found; data-cite and __SOURCES_LIST__ left as is")

    # --- speaker notes come from the outline, matched by data-slide --------
    def notes(m):
        blk = m.group(0); tag = opening_tag(blk)
        sm = re.search(r'data-slide="(\d{1,2})"', tag)
        if not sm:
            return blk
        nn = sm.group(1).zfill(2)
        if nn not in outline:
            sys.exit(f"build failed: data-slide=\"{nn}\" has no '## {nn} ·' entry in outline.md")
        text = outline[nn].get("notes", "")
        if 'data-notes="' in tag:
            say(f"notes: slide {nn} had data-notes in slides.html; the outline wins")
            tag2 = re.sub(r'\s*data-notes="[^"]*"', "", tag)
        else:
            tag2 = tag
        tag2 = tag2[:-1] + f' data-notes="{_html.escape(text, quote=True)}">'
        return tag2 + blk[len(tag):]

    slides = SECTION.sub(notes, slides)

    # --- a raw double quote inside data-notes corrupts the <section> tag ---
    for m in re.finditer(r'data-notes="', slides):
        end = slides.index('"', m.end())
        if slides[end + 1] not in " \t\r\n>/":
            where = slides.count("<section", 0, m.start()) + 1
            sys.exit(f"build failed: unescaped double quote in data-notes on slide {where}.\n"
                     f"  ...{slides[end-60:end+40]}...\n  Use &quot; inside speaker notes.")

    # --- every data-viz must exist ----------------------------------------
    defined = set(re.findall(r"""VIZ\[\s*['"]([^'"]+)['"]\s*\]\s*=""", viz))
    for name in set(re.findall(r'data-viz="([^"]+)"', slides)):
        if name not in defined:
            sys.exit(f"build failed: data-viz=\"{name}\" is not defined in viz.js (have: {', '.join(sorted(defined)) or 'none'})")

    # --- slide numbers from document order; backup slides unnumbered ------
    blocks = [(m.start(), m.end()) for m in SECTION.finditer(slides)]
    numbered = [i for i, (a, b) in enumerate(blocks) if "data-backup" not in opening_tag(slides[a:b])]
    total = len(numbered)
    out, last, k = [], 0, 0
    for i, (a, b) in enumerate(blocks):
        out.append(slides[last:a])
        blk = slides[a:b]
        if i in numbered:
            k += 1; label = f"{k:02d} / {total:02d}"
        else:
            label = "Backup"
        out.append(re.sub(r"(?<=>)\s*\d{1,2}\s*/\s*\d{1,2}\s*(?=<)", label, blk))
        last = b
    out.append(slides[last:])
    slides = "".join(out)
    rep.total = total
    say(f"numbering: {total} slides in the talk, {len(blocks) - total} backup")

    # --- placeholders: listed on every build, never silently presented ----
    for i, m in enumerate(SECTION.finditer(slides), 1):
        found = re.findall(r'<span class="ph">(.*?)</span>', m.group(0), re.S)
        if found:
            rep.problems += len(found)
            say(f"placeholder on slide {i:02d}: " + " | ".join(" ".join(f.split()) for f in found))

    # --- sources: every outline entry should say where its facts come from -
    for nn, e in outline.items():
        if not e.get("source"):
            say(f"no Source line in outline.md for slide {nn} · {e['title']}")

    # --- timing: summed from the outline, never estimated ------------------
    secs = sum(parse_mmss(e.get("time")) or 0 for e in outline.values())
    limit = parse_mmss(cfg.get("limit", ""))
    if limit is not None:
        say(f"timing: {mmss(secs)} summed from outline.md (limit {mmss(limit)})")
        if secs > limit:
            rep.problems += 1
            say(f"timing: over the limit by {mmss(secs - limit)}")
    else:
        say(f"timing: {mmss(secs)} summed from outline.md")

    # --- assemble ------------------------------------------------------------
    deck_id = pathlib.Path(cfg["output"]).stem
    # an empty `fonts` in deck.toml means system fonts and no network
    fonts = (f'<link rel="preconnect" href="https://fonts.googleapis.com">\n'
             f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
             f'<link rel="stylesheet" href="{cfg["fonts"]}">\n') if cfg.get("fonts") else ""
    ctl = ctl.replace("__DECK_ID__", deck_id)
    rep.html = f"""<!DOCTYPE html>
<html lang="{cfg.get('lang', 'en')}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_html.escape(cfg['title'])}</title>
{fonts}<style>
{css}
</style>
</head>
<body>
<div class="deck-viewport">
<main class="deck-stage" id="deckStage">
{slides}
</main>
</div>
<script>
{viz}
{ctl}
</script>
</body>
</html>
"""
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parent.parent),
                    help="the talk folder (holds deck.toml); default: the parent of _src/")
    ap.add_argument("--embed-media", action="store_true", help="inline media as data URIs")
    a = ap.parse_args(argv)
    root = pathlib.Path(a.root)
    rep = build(root, embed=a.embed_media)
    cfg = tomllib.loads((root / "deck.toml").read_text())
    out = root / cfg["output"]
    out.write_text(rep.html, encoding="utf-8")
    for l in rep.lines:
        print("  " + l)
    print(f"built {out.name} — {len(rep.html):,} bytes, {rep.total} slides" + (f", {rep.problems} things to fix" if rep.problems else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

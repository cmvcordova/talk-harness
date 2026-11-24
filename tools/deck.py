#!/usr/bin/env python3
"""Drive a talk folder with headless Chrome. No dependencies.

    python3 tools/deck.py serve [--port 8731]   build, serve, open in the browser
    python3 tools/deck.py shots [--out shots]   build, screenshot every slide at ?t=1
    python3 tools/deck.py check                 build, report overflow, clipped text, broken images
    python3 tools/deck.py pdf                   build, export <output>.pdf, one slide per page
    python3 tools/deck.py lint [--strict]       build, name slides that break the evidence rules (tools/lint.py)
    python3 tools/deck.py new <dir> [--skin S] [--starter N]
                                                copy the skeleton into a new talk folder
    python3 tools/deck.py reskin --skin S       put a skin (again) on an existing talk
    python3 tools/deck.py skins                 list the skins this machine can find

Every command takes --root <talk folder> (default: the parent of tools/).

A skin is a folder with skin.toml (name, fonts, about, home), skin.css (token overrides
and brand rules, pasted after deck.css), and optionally assets/ (copied into
the talk's assets/), starter/ or starters/<name>/ (slides.html, outline.md,
brief.md, citations.json and assets/ that a new talk starts from) and
SKIN.md (house rules, copied to the talk).
--skin takes a path, or a name looked up in $TALK_SKINS, then
~/.config/talk-harness/skins/, then the harness's own skins/.
Chrome is found at the macOS path, then google-chrome / chromium on PATH,
then $CHROME.
"""
import argparse, os, pathlib, re, shutil, subprocess, sys, time, webbrowser

try:
    import tomllib
except ModuleNotFoundError:
    sys.exit("deck.py needs Python 3.11 or newer (for tomllib).")

HERE = pathlib.Path(__file__).resolve().parent
CHROME_CANDIDATES = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                     "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]
SKELETON = ["README.md", "CLAUDE.md", "brief.md", "outline.md", "deck.toml", ".gitignore",
            "_src", "tools", "assets", "sources"]


def find_chrome():
    env = os.environ.get("CHROME")
    if env and os.path.exists(env):
        return env
    for c in CHROME_CANDIDATES:
        if os.path.isabs(c):
            if os.path.exists(c):
                return c
        elif shutil.which(c):
            return shutil.which(c)
    return None


def need_chrome():
    c = find_chrome()
    if not c:
        sys.exit("Chrome not found. Install Google Chrome or Chromium, or set CHROME=/path/to/chrome.")
    return c


def cfg(root):
    return tomllib.loads((root / "deck.toml").read_text())


def build(root):
    r = subprocess.run([sys.executable, str(root / "_src" / "build.py"), "--root", str(root)])
    if r.returncode != 0:
        sys.exit(r.returncode)
    return root / cfg(root)["output"]


def chrome(args, timeout=120):
    return subprocess.run([need_chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                           "--window-size=1920,1080", *args],
                          capture_output=True, text=True, timeout=timeout)


def count_slides(out):
    body = re.sub(r"<!--.*?-->", "", out.read_text(), flags=re.S)
    return len(re.findall(r"<section\s+[^>]*class=", body))


# ----------------------------------------------------------------- commands
def cmd_serve(root, a):
    out = build(root)
    url = f"http://127.0.0.1:{a.port}/{out.name}"
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(a.port), "--bind", "127.0.0.1",
                            "--directory", str(root)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.6)
    print(f"serving {root} at {url}  (Ctrl+C stops)")
    webbrowser.open(url)
    try:
        srv.wait()
    except KeyboardInterrupt:
        srv.terminate()


def cmd_shots(root, a):
    out = build(root)
    dest = root / a.out
    dest.mkdir(exist_ok=True)
    n = count_slides(out)
    which = [a.slide] if a.slide else range(1, n + 1)
    for i in which:
        png = dest / f"{i:02d}.png"
        chrome([f"--virtual-time-budget={a.budget}", f"--screenshot={png}", f"file://{out}?t={a.t}#{i}"])
        print(png)
    print(f"{len(list(which))} screenshots in {dest}/ — open them and look at every one.")


def cmd_check(root, a):
    out = build(root)
    r = chrome(["--virtual-time-budget=10000", "--enable-logging=stderr", "--v=0", "--dump-dom",
                f"file://{out}?check=1&t=1"])
    # Chrome logs console lines as ...INFO:CONSOLE:925] "text" or ...CONSOLE(925)] "text"
    console = re.compile(r'CONSOLE[:(]\d+\)?\]\s+"([^"]*)"')
    found = [m.group(1) for m in console.finditer(r.stderr)]
    lines = [l for l in found if l.startswith("CHECK ")]
    errors = [l for l in found if "Uncaught" in l or "no visual named" in l]
    for l in errors + lines:
        print("  " + l)
    done = next((l for l in lines if l.startswith("CHECK done")), None)
    if not done:
        print("  check did not finish: the page threw before measuring, or Chrome printed nothing. Run `shots` and look.")
        return 1
    problems = int(re.search(r"(\d+) problems", done).group(1)) + len(errors)
    return 1 if problems else 0


def cmd_lint(root, a):
    import lint
    out = build(root)
    c = {**lint.DEFAULTS, **cfg(root).get("lint", {})}
    found = [str(p) for p in lint.lint_slides((root / "_src" / "slides.html").read_text(), c)]
    # the two rules that depend on how the text wraps are measured in the browser
    r = chrome(["--virtual-time-budget=10000", "--enable-logging=stderr", "--v=0", "--dump-dom",
                f"file://{out}?check=1&t=1&lint={c['min_px']}"])
    found += [m.group(1) for m in re.finditer(r'CONSOLE[:(]\d+\)?\]\s+"(LINT [^"]*)"', r.stderr)]
    text = (root / "outline.md").read_text() if (root / "outline.md").exists() else ""
    secs = sum(int(m.group(1)) * 60 + int(m.group(2)) for m in re.finditer(r"^-\s+\*{0,2}(?:Time|Tiempo)\*{0,2}:\s*(\d+):(\d{2})", text, flags=re.M))
    numbered = lint.numbered((root / "_src" / "slides.html").read_text())
    note = lint.pace(numbered, secs, c["slides_per_minute"])
    for line in sorted(found):
        print("  " + line)
    if note:
        print("  " + note)
    print(f"  lint: {len(found)} to look at" + (", 1 note" if note else "") + f" across {numbered} slides. Rules and sources: tools/lint.py")
    return 1 if (a.strict and found) else 0


def cmd_pdf(root, a):
    out = build(root)
    pdf = root / (out.stem + ".pdf")
    chrome(["--no-pdf-header-footer", "--virtual-time-budget=20000", f"--print-to-pdf={pdf}", f"file://{out}"], timeout=300)
    if not pdf.exists():
        sys.exit("no PDF was written")
    pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))
    print(f"{pdf}  {pdf.stat().st_size:,} bytes, {pages} pages (expected {count_slides(out)})")


# ------------------------------------------------------------------- skins
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def skin_dirs():
    dirs = [pathlib.Path(p).expanduser() for p in os.environ.get("TALK_SKINS", "").split(os.pathsep) if p]
    dirs.append(pathlib.Path.home() / ".config" / "talk-harness" / "skins")
    dirs.append(HERE.parent / "skins")
    return dirs


def known_skins():
    """{name: folder} for every skin on the search path; the first one found wins."""
    out = {}
    for d in skin_dirs():
        if d.is_dir():
            for c in sorted(d.iterdir()):
                if (c / "skin.toml").exists():
                    out.setdefault(c.name, c.resolve())
    return out


def find_skin(name):
    p = pathlib.Path(name).expanduser()
    if (p / "skin.toml").exists():
        return p.resolve()
    known = known_skins()
    if name in known:
        return known[name]
    sys.exit(f"no skin named '{name}'. Looked for a folder with skin.toml at {p} and in: "
             + ", ".join(str(d) for d in skin_dirs())
             + ". Skins found: " + (", ".join(sorted(known)) or "none") + ".")


def set_toml(path, key, value):
    """Set `key = "value"` in a flat TOML file, keeping every other line and comment."""
    line = f'{key} = "{value}"'
    text = path.read_text()
    new, n = re.subn(rf'^{re.escape(key)}\s*=\s*"[^"]*"', lambda m: line, text, count=1, flags=re.M)
    if not n:   # a new key goes before the first [table], or it would land inside it
        m = re.search(r"^\[", text, flags=re.M)
        new = (text[:m.start()] + line + "\n" + text[m.start():]) if m else text.rstrip("\n") + "\n" + line + "\n"
    path.write_text(new)


def starter_of(skin, name):
    """The folder a new talk's slides and outline come from, or None for the harness default."""
    if name:
        d = skin / "starters" / name
        if not d.is_dir():
            have = sorted(c.name for c in (skin / "starters").iterdir() if c.is_dir()) if (skin / "starters").is_dir() else []
            sys.exit(f"skin '{skin.name}' has no starter named '{name}'. It has: " + (", ".join(have) or "only the default") + ".")
        return d
    return skin / "starter" if (skin / "starter").is_dir() else None


def apply_skin(skin, dest, starter=None, fresh=False):
    """Copy a skin's stylesheet, assets and house rules into a talk. With
    fresh=True (a new talk) the skin's starter replaces the default one."""
    meta = tomllib.loads((skin / "skin.toml").read_text())
    shutil.copy(skin / "skin.css", dest / "_src" / "skin.css")
    if (skin / "assets").is_dir():
        shutil.copytree(skin / "assets", dest / "assets", dirs_exist_ok=True, ignore=IGNORE)
    if (skin / "SKIN.md").exists():
        shutil.copy(skin / "SKIN.md", dest / "SKIN.md")
    if fresh:
        src = starter_of(skin, starter)
        if src:
            for name, to in (("slides.html", dest / "_src" / "slides.html"), ("outline.md", dest / "outline.md"),
                             ("brief.md", dest / "brief.md"), ("citations.json", dest / "sources" / "citations.json")):
                if (src / name).exists():
                    shutil.copy(src / name, to)
            if (src / "assets").is_dir():   # media the starter's own slides use
                shutil.copytree(src / "assets", dest / "assets", dirs_exist_ok=True, ignore=IGNORE)
    set_toml(dest / "deck.toml", "skin", meta.get("name", skin.name))
    if "fonts" in meta:
        set_toml(dest / "deck.toml", "fonts", meta["fonts"])
    return meta


def cmd_skins(root, a):
    known = known_skins()
    for name, path in sorted(known.items()):
        meta = tomllib.loads((path / "skin.toml").read_text())
        starters = sorted(c.name for c in (path / "starters").iterdir() if c.is_dir()) if (path / "starters").is_dir() else []
        print(f"{name:16} {path}" + (f"   starters: {', '.join(starters)}" if starters else "")
              + (f"\n{'':16} {meta['about']}" if meta.get("about") else "")
              + (f"\n{'':16} talks live in: {meta['home']}" if meta.get("home") else ""))
    if not known:
        print("no skins found in: " + ", ".join(str(d) for d in skin_dirs()))


def cmd_reskin(root, a):
    skin = find_skin(a.skin)
    meta = apply_skin(skin, root)
    print(f"skin '{meta.get('name', skin.name)}' applied to {root}: _src/skin.css, assets/, deck.toml fonts. "
          f"Slides and outline untouched. Build, then look at every screenshot.")


def cmd_new(root, a):
    dest = pathlib.Path(a.dest).resolve()
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f"{dest} exists and is not empty")
    skin_path = find_skin(a.skin) if a.skin else None   # fail before anything is copied
    if skin_path:
        starter_of(skin_path, a.starter)
    dest.mkdir(parents=True, exist_ok=True)
    for name in SKELETON:
        src = root / name
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dest / name, ignore=IGNORE)
        else:
            shutil.copy(src, dest / name)
    # the harness root is the example deck; a new talk starts with none of its content
    starter = HERE / "starter"
    shutil.copy(starter / "outline.md", dest / "outline.md")
    shutil.copy(starter / "slides.html", dest / "_src" / "slides.html")
    shutil.copy(starter / "deck.toml", dest / "deck.toml")
    shutil.rmtree(dest / "sources", ignore_errors=True); (dest / "sources").mkdir()
    shutil.copy(starter / "citations.json", dest / "sources" / "citations.json")
    shutil.rmtree(dest / "assets", ignore_errors=True); (dest / "assets").mkdir()
    (dest / "assets" / ".gitkeep").write_text("")
    shutil.rmtree(dest / "tools" / "starter", ignore_errors=True)
    skin = ""
    if a.skin:
        meta = apply_skin(find_skin(a.skin), dest, starter=a.starter, fresh=True)
        skin = f" (skin: {meta.get('name', a.skin)})"
    elif a.starter:
        sys.exit("--starter names a starter inside a skin; give --skin too")
    print(f"new talk folder: {dest}{skin}\n  1. answer brief.md\n  2. open Claude Code there and say: build my talk from brief.md")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(HERE.parent), help="the talk folder (holds deck.toml)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8731)
    s = sub.add_parser("shots"); s.add_argument("--out", default="shots"); s.add_argument("--slide", type=int)
    s.add_argument("--t", default="10", help="seconds to freeze the figures at (10: every figure has settled)"); s.add_argument("--budget", type=int, default=5000)
    sub.add_parser("check")
    s = sub.add_parser("lint"); s.add_argument("--strict", action="store_true", help="exit 1 if any slide is named")
    sub.add_parser("pdf")
    s = sub.add_parser("new"); s.add_argument("dest")
    s.add_argument("--skin", help="a skin folder, or the name of one on the search path")
    s.add_argument("--starter", help="a named starter inside the skin (starters/<name>/)")
    s = sub.add_parser("reskin"); s.add_argument("--skin", required=True)
    sub.add_parser("skins")
    a = ap.parse_args(argv)
    root = pathlib.Path(a.root).resolve()
    if not (root / "deck.toml").exists():
        sys.exit(f"no deck.toml in {root}")
    return {"serve": cmd_serve, "shots": cmd_shots, "check": cmd_check, "pdf": cmd_pdf, "new": cmd_new,
            "reskin": cmd_reskin, "skins": cmd_skins, "lint": cmd_lint}[a.cmd](root, a) or 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Drive a talk folder with headless Chrome. No dependencies.

    python3 tools/deck.py serve [--port 8731]   build, serve, open in the browser
    python3 tools/deck.py shots [--out shots]   build, screenshot every slide at ?t=1
    python3 tools/deck.py check                 build, report overflow, clipped text, broken images
    python3 tools/deck.py pdf                   build, export <output>.pdf, one slide per page
    python3 tools/deck.py new <dir>             copy the skeleton into a new talk folder

Every command takes --root <talk folder> (default: the parent of tools/).
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


def cmd_pdf(root, a):
    out = build(root)
    pdf = root / (out.stem + ".pdf")
    chrome(["--no-pdf-header-footer", "--virtual-time-budget=20000", f"--print-to-pdf={pdf}", f"file://{out}"], timeout=300)
    if not pdf.exists():
        sys.exit("no PDF was written")
    pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))
    print(f"{pdf}  {pdf.stat().st_size:,} bytes, {pages} pages (expected {count_slides(out)})")


def cmd_new(root, a):
    dest = pathlib.Path(a.dest).resolve()
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f"{dest} exists and is not empty")
    dest.mkdir(parents=True, exist_ok=True)
    for name in SKELETON:
        src = root / name
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dest / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
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
    print(f"new talk folder: {dest}\n  1. answer brief.md\n  2. open Claude Code there and say: build my talk from brief.md")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(HERE.parent), help="the talk folder (holds deck.toml)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8731)
    s = sub.add_parser("shots"); s.add_argument("--out", default="shots"); s.add_argument("--slide", type=int)
    s.add_argument("--t", default="10", help="seconds to freeze the figures at (10: every figure has settled)"); s.add_argument("--budget", type=int, default=5000)
    sub.add_parser("check")
    sub.add_parser("pdf")
    s = sub.add_parser("new"); s.add_argument("dest")
    a = ap.parse_args(argv)
    root = pathlib.Path(a.root).resolve()
    if not (root / "deck.toml").exists():
        sys.exit(f"no deck.toml in {root}")
    return {"serve": cmd_serve, "shots": cmd_shots, "check": cmd_check, "pdf": cmd_pdf, "new": cmd_new}[a.cmd](root, a) or 0


if __name__ == "__main__":
    sys.exit(main())

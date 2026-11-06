"""Link-preview image: social/repo-preview.png, for the repo's Settings, Social preview.

GitHub takes it through its web UI only. Run build_hero.py first.
"""
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE.parent / "social"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BG = "#0b0c10"

svg = (HERE.parent / "profile" / "assets" / "hero-dark.svg").read_text(encoding="utf-8")
# a thumbnail cannot carry the small print: keep the headline and the surface
svg = re.sub(r'<g class="cp mono".*?</g>', "", svg)
svg = re.sub(r'<text class="co mono".*?</text>', "", svg)
svg = re.sub(r'<rect x="\.5" y="\.5"[^>]*/>', "", svg, count=1)
svg = svg.replace('width="800" height="360"', 'width="1280" height="576"', 1)

OUT.mkdir(exist_ok=True)
page = OUT / "_preview.html"
page.write_text(f'<!doctype html><meta charset="utf-8"><body style="margin:0;background:{BG};padding-top:32px">{svg}',
                encoding="utf-8")
subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-prefers-reduced-motion",
                "--window-size=1280,640", f"--screenshot={OUT / 'repo-preview.png'}", page.as_uri()],
               capture_output=True, timeout=60)
page.unlink()

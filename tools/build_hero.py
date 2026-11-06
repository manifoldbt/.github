"""Draws profile/assets/hero-{dark,light}.svg from surface.json. Every vertex is a backtest.

    pip install fonttools brotli pillow
    python hero_surface.py surface.json   # the data, needs manifoldbt
    python build_hero.py                  # the picture

fonts/ holds the latin Inter and JetBrains Mono woff2 from Google Fonts (not committed).
"""
import base64
import io
import json
import math
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image

HERE = Path(__file__).parent
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE.parent / "profile" / "assets"
DATA = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "surface.json").read_text())
FAST, SLOW, SHARPE = DATA["fast"], DATA["slow"], DATA["sharpe"]
N, M = len(FAST), len(SLOW)

THEMES = {
    "dark": dict(card="#0b0c10", line="#1e2030", text="#e8e9ed", muted="#8b8fa3", dim="#7d819e",
                 floor="#262a3d", pill="#12131a", mark="#ffffff",
                 ramp=["#1b2240", "#34488f", "#5b7ff5", "#a9bdfb"],
                 zone=["#166534", "#22c55e", "#4ade80", "#bbf7d0"], mesh="#0b0c10", skirt="#141725"),
    "light": dict(card="#ffffff", line="#e2e4ec", text="#12131a", muted="#565b70", dim="#5f6478",
                  floor="#d5d8e4", pill="#f5f6fa", mark="#12131a",
                  ramp=["#dce3fa", "#a3b6f8", "#5b7ff5", "#2238a0"],
                  zone=["#bbf7d0", "#4ade80", "#16a34a", "#14532d"], mesh="#ffffff", skirt="#eceef6"),
}

LOOP = 10.0
START, SPAN = 0.3, 2.0       # the surface rises
ZONE_ON, MARK_ON = 3.0, 3.4  # then the plateau lights up, then its label
HOLD = 9.4
PLATEAU_FLOOR = 1.1          # smoothed Sharpe that bounds the plateau
CX, CY, DX, DY, ZS = 600.0, 132.0, 12.3, 6.3, 68.0


def project(i, j, z=0.0):
    # the footprint on screen stays the same whatever the size of the grid
    u, v = i * 14 / (M - 1), j * 14 / (N - 1)
    return CX + (u - v) * DX, CY + (u + v) * DY - z * ZS


def ramp(colors, t):
    t = max(0.0, min(1.0, t)) * (len(colors) - 1)
    k = min(int(t), len(colors) - 2)
    a, b = colors[k], colors[k + 1]
    f = t - k
    return "#" + "".join(
        f"{round(int(a[p:p + 2], 16) * (1 - f) + int(b[p:p + 2], 16) * f):02x}" for p in (1, 3, 5))


def font(path, family, chars):
    opts = subset.Options(flavor="woff2", layout_features=["kern"], notdef_outline=True)
    f = TTFont(path)
    s = subset.Subsetter(opts)
    s.populate(text=chars)
    s.subset(f)
    f.flavor = "woff2"
    buf = io.BytesIO()
    f.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return (f'@font-face{{font-family:"{family}";src:url(data:font/woff2;base64,{b64}) '
            f'format("woff2");font-weight:100 900}}')


def logo(color):
    im = Image.open(HERE / "logo.png").convert("RGBA")
    h = 60
    im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
    r, g, b = (int(color[p:p + 2], 16) for p in (1, 3, 5))
    im.putdata([(r, g, b, round(a * max(cr, cg, cb) / 255)) for cr, cg, cb, a in im.get_flattened_data()])
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return im.size, base64.b64encode(buf.getvalue()).decode()


def pct(t):
    return f"{100 * t / LOOP:.2f}".rstrip("0").rstrip(".")


def fade(name, start, dur=0.3):
    return (f"@keyframes {name}{{0%,{pct(start)}%{{opacity:0}}{pct(start + dur)}%,{pct(HOLD)}%{{opacity:1}}"
            f"100%{{opacity:0}}}}.{name}{{animation:{name} {LOOP:g}s linear infinite}}")


def poly(pts):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def plateau():
    """The connected vertices around the best smoothed cell that stay above PLATEAU_FLOOR."""
    smooth = [[0.0] * M for _ in range(N)]
    for j in range(N):
        for i in range(M):
            around = [SHARPE[v][u] for v in range(max(j - 1, 0), min(j + 2, N)) for u in range(max(i - 1, 0), min(i + 2, M))]
            smooth[j][i] = sum(around) / len(around)
    seed = max(((j, i) for j in range(N) for i in range(M)), key=lambda p: smooth[p[0]][p[1]])
    zone, todo = {seed}, [seed]
    while todo:
        j, i = todo.pop()
        for v, u in ((j + 1, i), (j - 1, i), (j, i + 1), (j, i - 1)):
            if 0 <= v < N and 0 <= u < M and (v, u) not in zone and smooth[v][u] >= PLATEAU_FLOOR:
                zone.add((v, u))
                todo.append((v, u))
    return zone


def plateau_label(zone):
    mean = sum(SHARPE[j][i] for j, i in zone) / len(zone)
    return f"plateau: Sharpe {mean:.1f}", f"{len(zone)} neighbours, not one lucky cell"


def surface(c, css):
    body = []
    hi, lo = max(max(r) for r in SHARPE), min(min(r) for r in SHARPE)

    # floor: Sharpe = 0, so the height of the surface above it is the real number
    floor = []
    for t in range(15):
        a, b = project(0, t * (N - 1) / 14), project(M - 1, t * (N - 1) / 14)
        floor.append(f'<path d="M{a[0]:.1f} {a[1]:.1f}L{b[0]:.1f} {b[1]:.1f}"/>')
        a, b = project(t * (M - 1) / 14, 0), project(t * (M - 1) / 14, N - 1)
        floor.append(f'<path d="M{a[0]:.1f} {a[1]:.1f}L{b[0]:.1f} {b[1]:.1f}"/>')
    css.append(fade("fl", 0.1))
    body.append(f'<g class="fl" stroke="{c["floor"]}" stroke-width=".6" fill="none">{"".join(floor)}</g>')

    # the cells rise in the engine's enumeration order, and those of the plateau change color in place,
    # so that a ridge in front of them still hides them
    zone = plateau()
    cells = []
    for j in range(N - 1):
        for i in range(M - 1):
            z = [SHARPE[j][i], SHARPE[j][i + 1], SHARPE[j + 1][i + 1], SHARPE[j + 1][i]]
            mean = sum(z) / 4
            t = (mean - lo) / (hi - lo)
            pts = [project(i, j, z[0]), project(i + 1, j, z[1]), project(i + 1, j + 1, z[2]), project(i, j + 1, z[3])]
            corners = sum((v, u) in zone for v, u in ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)))
            base = ramp(c["ramp"], t)
            fill = ramp(c["zone"], t) if corners >= 2 else base
            n = j * (M - 1) + i
            t0 = START + SPAN * n / ((N - 1) * (M - 1))
            name = f"q{n}"
            lit = fill != base
            before = f";fill:{base}" if lit else ""
            after = f";fill:{fill}" if lit else ""
            frames = (f"0%,{pct(t0)}%{{opacity:0;transform:translateY({mean * ZS:.0f}px){before}}}"
                      f"{pct(t0 + .3)}%{{opacity:1;transform:none{before}}}")
            if lit:
                frames += (f"{pct(ZONE_ON)}%{{opacity:1;transform:none{before}}}"
                           f"{pct(ZONE_ON + .3)}%{{opacity:1;transform:none{after}}}")
            frames += f"{pct(HOLD)}%{{opacity:1;transform:none{after}}}100%{{opacity:0;transform:none{after}}}"
            css.append(f"@keyframes {name}{{{frames}}}.{name}{{animation:{name} {LOOP:g}s cubic-bezier(.2,.7,.2,1) infinite}}")
            cells.append((i + j, f'<polygon class="{name}" fill="{fill}" points="{poly(pts)}"/>'))
    cells.sort(key=lambda x: x[0])
    body.append(f'<g stroke="{c["mesh"]}" stroke-width=".5" stroke-opacity=".7">{"".join(x[1] for x in cells)}</g>')

    # skirt under the two front edges, so the surface reads as a solid
    edge_l = [project(i, N - 1, SHARPE[N - 1][i]) for i in range(M)]
    edge_r = [project(M - 1, j, SHARPE[j][M - 1]) for j in range(N)]
    skirt_l = poly(edge_l + [project(M - 1, N - 1), project(0, N - 1)])
    skirt_r = poly(edge_r + [project(M - 1, N - 1), project(M - 1, 0)])
    css.append(fade("sk", 2.5))
    body.append(f'<g class="sk" fill="{c["skirt"]}" stroke="{c["floor"]}" stroke-width=".6">'
                f'<polygon points="{skirt_l}"/><polygon points="{skirt_r}"/></g>')

    # axes, along the floor's two front edges
    ang = math.degrees(math.atan2(DY, DX))
    lx, ly = project((M - 1) / 2, N - 1)
    rx, ry = project(M - 1, (N - 1) / 2)
    css.append(fade("ax", 2.6))
    body.append(
        f'<g class="ax mono" font-size="9.5" fill="{c["dim"]}" text-anchor="middle">'
        f'<text transform="translate({lx - 5:.1f} {ly + 14:.1f}) rotate({ang:.1f})">slow EMA {SLOW[0]} to {SLOW[-1]}</text>'
        f'<text transform="translate({rx + 5:.1f} {ry + 14:.1f}) rotate({-ang:.1f})">fast EMA {FAST[0]} to {FAST[-1]}</text></g>')

    # the plateau: a line from its middle, and what it is
    label, detail = plateau_label(zone)
    mj = sum(p[0] for p in zone) / len(zone)
    mi = sum(p[1] for p in zone) / len(zone)
    j, i = min(zone, key=lambda p: (p[0] - mj) ** 2 + (p[1] - mi) ** 2)
    px, py = project(i, j, SHARPE[j][i])
    top = 92
    css.append(fade("pk", MARK_ON))
    body.append(
        f'<g class="pk"><path d="M{px:.1f} {py - 4:.1f}V{top}" stroke="{c["mark"]}" stroke-width=".8"/>'
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.6" fill="{c["mark"]}"/>'
        f'<text class="mono" x="{px:.1f}" y="{top - 16}" font-size="10.5" fill="{c["text"]}">{label}</text>'
        f'<text class="mono" x="{px:.1f}" y="{top - 3}" font-size="10.5" fill="{c["muted"]}">{detail}</text></g>')

    # the call that made it, then what it is
    css.append(fade("co", .2))
    body.append(f'<text class="co mono" x="775" y="44" font-size="10.5" fill="{c["muted"]}" text-anchor="end">'
                f'mbt.run_sweep(strategy, {{"fast": ..., "slow": ...}}, config, store)</text>')
    css.append(fade("cp", 2.7))
    body.append(
        f'<g class="cp mono" font-size="9.5" fill="{c["dim"]}" text-anchor="end">'
        f'<text x="775" y="331">{N * M:,} real backtests, not a drawing. EMA crossover, BTCUSDT 1h,</text>'
        f'<text x="775" y="344">2023 to 2024, fees and slippage on. Height = in-sample Sharpe.</text></g>')
    return "".join(body)


def build(theme):
    c = THEMES[theme]
    css = []
    scene = surface(c, css)

    (lw, lh), lg = logo(c["text"])
    left = [
        f'<image x="40" y="30" width="{lw * 26 / lh:.1f}" height="26" href="data:image/png;base64,{lg}"/>',
        f'<text x="{40 + lw * 26 / lh + 10:.1f}" y="49" font-size="16.5" font-weight="500" fill="{c["text"]}">Manifold-BT</text>',
    ]
    for y, t, col in ((112, "Sweep the grid.", c["text"]), (151, "Read the surface.", c["text"]),
                      (190, "Check every fill.", c["muted"])):
        left.append(f'<text x="40" y="{y}" font-size="35" font-weight="600" letter-spacing="-.7" fill="{col}">{t}</text>')
    for y, t in ((224, "Python backtesting with a Rust engine. Signals, fills,"),
                 (245, "fees, funding and equity all run in Rust, from bars"),
                 (266, "down to the order queue.")):
        left.append(f'<text x="40" y="{y}" font-size="14.5" fill="{c["muted"]}">{t}</text>')
    x = 40.0
    for t, w in (("Bars", 46), ("Trades", 60), ("L2 book", 66), ("MBO", 50), ("Options", 66)):
        left.append(f'<rect x="{x}" y="296" width="{w}" height="26" rx="13" fill="{c["pill"]}" stroke="{c["line"]}"/>'
                    f'<text x="{x + w / 2}" y="313" font-size="12" fill="{c["muted"]}" text-anchor="middle">{t}</text>')
        x += w + 7

    label, detail = plateau_label(plateau())
    text_chars = "".join(sorted(set(
        "Manifold-BT Sweep the grid. Read the surface. Check every fill. Python backtesting with a Rust engine. "
        "Signals, fills, fees, funding and equity all run in Rust, from bars down to the order queue. "
        "Bars Trades L2 book MBO Options")))
    mono_chars = "".join(sorted(set(
        'mbt.run_sweep(strategy, {"fast": ..., "slow": ...}, config, store) '
        f"{N * M:,} real backtests, not a drawing. EMA crossover, BTCUSDT 1h, 2023 to 2024, fees and slippage on. "
        f"Height = in-sample Sharpe. slow EMA fast 0123456789 {label} {detail}")))
    fonts = font(HERE / "fonts" / "inter.woff2", "Inter", text_chars) + font(
        HERE / "fonts" / "jbmono.woff2", "JetBrains Mono", mono_chars)

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="360" viewBox="0 0 800 360">'
        f'<style>{fonts}text{{font-family:Inter,system-ui,sans-serif}}'
        '.mono,.mono text{font-family:"JetBrains Mono",ui-monospace,monospace}'
        f'@media (prefers-reduced-motion:no-preference){{{"".join(css)}}}</style>'
        f'<rect x=".5" y=".5" width="799" height="359" rx="14" fill="{c["card"]}" stroke="{c["line"]}"/>'
        + "".join(left) + scene + "</svg>")


OUT.mkdir(parents=True, exist_ok=True)
for theme in THEMES:
    svg = build(theme)
    (OUT / f"hero-{theme}.svg").write_text(svg, encoding="utf-8", newline="")
    print(theme, len(svg.encode()) // 1024, "KB")

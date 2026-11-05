"""Render the paperops README images (hero, conversation) in light and dark.

Text is drawn with IBM Plex fonts (SIL OFL, fetched from google/fonts on first
use) and saved as SVG paths, so the images do not depend on the viewer's fonts.

    python .github/assets/make_readme_art.py                 # writes the SVGs here
    python .github/assets/make_readme_art.py --preview DIR   # also writes PNG previews to DIR

Requires matplotlib.
"""

from __future__ import annotations

import sys
import tempfile
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, FancyBboxPatch

OUT = Path(__file__).parent
PREVIEW = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
FONTS = Path(tempfile.gettempdir()) / "paperops-readme-fonts"
FONT_FILES = {
    "IBMPlexMono-Regular.ttf": "ibmplexmono",
    "IBMPlexMono-Medium.ttf": "ibmplexmono",
    "IBMPlexMono-SemiBold.ttf": "ibmplexmono",
    "IBMPlexSansJP-Regular.ttf": "ibmplexsansjp",
    "IBMPlexSansJP-Medium.ttf": "ibmplexsansjp",
}
FONTS.mkdir(exist_ok=True)
for name, family in FONT_FILES.items():
    if not (FONTS / name).is_file():
        url = f"https://github.com/google/fonts/raw/main/ofl/{family}/{name}"
        urllib.request.urlretrieve(url, FONTS / name)

FP = {
    "mono": FontProperties(fname=FONTS / "IBMPlexMono-Regular.ttf"),
    "mono-md": FontProperties(fname=FONTS / "IBMPlexMono-Medium.ttf"),
    "mono-sb": FontProperties(fname=FONTS / "IBMPlexMono-SemiBold.ttf"),
    "jp": FontProperties(fname=FONTS / "IBMPlexSansJP-Regular.ttf"),
    "jp-md": FontProperties(fname=FONTS / "IBMPlexSansJP-Medium.ttf"),
}

PALETTES = {
    "light": dict(paper="#fcfcfb", ink="#17191f", ink2="#535a66", rule="#e1e4ea", brand="#3f51b5",
                  brand_s="#e9ecf9", add="#2f7d3a", add_s="#e7f3e8", cut="#b23b30", cut_s="#fbeceb",
                  mark="#a0620c", mark_s="#fbf0dc", note="#eceef2"),
    "dark": dict(paper="#13161c", ink="#e9ecf2", ink2="#9ca4b3", rule="#272c38", brand="#93a1f5",
                 brand_s="#1d2444", add="#6cc77a", add_s="#15301b", cut="#f0897e", cut_s="#3a1c19",
                 mark="#e3a548", mark_s="#33260f", note="#1c212b"),
}  # fmt: skip

matplotlib.rcParams["svg.fonttype"] = "path"
matplotlib.rcParams["svg.hashsalt"] = "paperops"


class Canvas:
    def __init__(self, w: int, h: int, pal: dict[str, str]) -> None:
        self.pal = pal
        self.fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
        self.fig.patch.set_alpha(0)
        self.ax = self.fig.add_axes((0, 0, 1, 1))
        self.ax.set_xlim(0, w)
        self.ax.set_ylim(h, 0)
        self.ax.axis("off")
        self.ax.patch.set_alpha(0)

    def rect(self, x, y, w, h, r, fill, edge=None, lw=0.0):
        self.ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle=f"round,pad=0,rounding_size={r}",
                facecolor=self.pal.get(fill, fill),
                edgecolor=self.pal.get(edge, edge) if edge else "none",
                linewidth=lw,
            )
        )

    def line(self, x1, y1, x2, y2, color, lw=1.0):
        self.ax.plot([x1, x2], [y1, y2], color=self.pal[color], linewidth=lw, solid_capstyle="butt")

    def dot(self, x, y, r, color):
        self.ax.add_patch(Circle((x, y), r, facecolor=self.pal[color], edgecolor="none"))

    def text(self, x, y, s, font, size_px, color, ha="left"):
        self.ax.text(
            x,
            y,
            s,
            fontproperties=FP[font],
            fontsize=size_px * 0.72,
            color=self.pal[color],
            va="baseline",
            ha=ha,
        )

    def save(self, stem: str) -> None:
        self.fig.savefig(OUT / f"{stem}.svg", transparent=True, metadata={"Date": None})
        if PREVIEW:
            bg = "#ffffff" if "light" in stem else "#0d1117"
            self.fig.savefig(PREVIEW / f"{stem}.png", facecolor=bg, dpi=150)
        plt.close(self.fig)


def hero(theme: str) -> None:
    c = Canvas(880, 300, PALETTES[theme])
    c.rect(0, 0, 880, 300, 12, "paper")
    c.text(44, 110, "paperops", "mono-sb", 58, "ink")
    c.rect(46, 130, 40, 5, 2.5, "brand")
    c.text(44, 174, "論文を、エージェントと書く。", "jp-md", 21, "ink")
    c.text(44, 204, "数個の添削で、好みの文章へ。", "jp-md", 21, "ink")
    c.text(44, 254, "$ pops init", "mono", 14, "ink2")
    c.text(150, 254, "あとは会話で", "jp", 14, "ink2")

    ox, oy = 372, 36
    c.rect(ox, oy, 472, 228, 9, "paper", edge="rule", lw=1.0)
    c.text(ox + 18, oy + 28, "sections/results.tex", "mono", 12, "ink2")
    c.text(ox + 454, oy + 28, "paper-revise", "mono", 12, "ink2", ha="right")
    c.line(ox, oy + 42, ox + 472, oy + 42, "rule")

    c.rect(ox + 12, oy + 54, 448, 26, 5, "mark_s")
    c.text(ox + 20, oy + 72, "%>", "mono-md", 12.5, "mark")
    c.text(ox + 44, oy + 72, "結論を先に。条件は Methods へ", "jp-md", 12.5, "mark")

    c.rect(ox + 12, oy + 88, 448, 48, 5, "cut_s")
    c.text(ox + 20, oy + 107, "-", "mono-md", 12.5, "cut")
    c.text(ox + 44, oy + 107, "本研究で用いた条件の範囲において、空洞底部の", "jp", 12.5, "ink2")
    c.text(ox + 44, oy + 127, "電位は低下する傾向が見られた（図 2）。", "jp", 12.5, "ink2")

    c.rect(ox + 12, oy + 144, 448, 26, 5, "add_s")
    c.text(ox + 20, oy + 162, "+", "mono-md", 12.5, "add")
    c.text(
        ox + 44,
        oy + 162,
        "深い空洞の底は、平坦面より 12 V 低く帯電する（図 2）。",
        "jp",
        12.5,
        "ink",
    )

    c.rect(ox + 12, oy + 184, 448, 28, 5, "note")
    c.text(ox + 20, oy + 203, "STYLE.md", "mono-md", 12, "brand")
    c.text(ox + 88, oy + 203, "規則を追加: 段落は結論の文で始める", "jp", 12, "ink2")
    c.save(f"hero-{theme}")


def conversation(theme: str) -> None:
    c = Canvas(880, 346, PALETTES[theme])
    c.rect(0, 0, 880, 346, 12, "paper")
    c.text(32, 40, "YOU", "mono-md", 12, "ink2")
    c.rect(32, 52, 476, 66, 10, "brand_s")
    c.text(50, 80, "案 A で進めて。", "jp", 15, "ink")
    c.text(50, 104, "図と本文を最後まで作って、PDF を見せて。", "jp", 15, "ink")

    c.text(32, 152, "AGENT", "mono-md", 12, "ink2")
    c.rect(32, 164, 476, 150, 10, "note")
    c.text(50, 192, "草稿ができました（12 ページ）。", "jp", 15, "ink")
    c.text(50, 216, "図 3 枚は、描画結果を見て 3 round 直しています。", "jp", 13.5, "ink2")
    c.text(50, 246, "初見の読者が受け取った主張は BRIEF と一致:", "jp", 15, "ink")
    c.text(50, 272, "「深い空洞の底は、壁が電子を遮るため低く帯電する」", "jp", 15, "ink")
    c.text(50, 296, "添削は TeX に %> で書いてください。", "jp", 13.5, "ink2")

    c.line(540, 32, 540, 314, "rule")
    c.text(564, 40, "WHAT HAPPENS", "mono-md", 12, "ink2")
    steps = [
        ("BRIEF.md", "主張 1 文、発見、載せないもの"),
        ("figures/", "描く → 見る → 直す、を記録"),
        ("numbers.tex", "本文の数値と出典"),
        ("sections/", "段落は主張の文から書く"),
        ("pops build", "PDF、未定義の参照と引用"),
        ("paper-check", "初見の読者に PDF だけ読ませる"),
    ]
    for i, (name, what) in enumerate(steps):
        y = 76 + 41 * i
        c.dot(568, y - 4, 3.5, "brand")
        if i < len(steps) - 1:
            c.line(568, y + 4, 568, y + 29, "rule", lw=1.2)
        c.text(584, y, name, "mono-md", 12.5, "ink")
        c.text(584, y + 19, what, "jp", 12, "ink2")
    c.save(f"conversation-{theme}")


for theme in PALETTES:
    hero(theme)
    conversation(theme)
print("ok")

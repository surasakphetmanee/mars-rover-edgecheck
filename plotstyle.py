"""One figure style for every Professor OS paper.

    import plotstyle as ps
    ps.use("lncs")                                  # fonts, sizes, Okabe–Ito colour cycle
    fig, ax = ps.figure("lncs")                     # sized to the real \\textwidth
    ax.plot(x, y, color=ps.ROLE["ours"], label="ours")
    ax.plot(x, b, color=ps.ROLE["baseline"], label="baseline")
    ax.imshow(M, cmap=ps.SEQ)                       # Crameri batlow; ps.DIV = vik centred on 0
    ps.save(fig, HERE / "fig_pmax")                 # fig_pmax.pdf (vector) + fig_pmax.png

Why each choice:
- Categorical colours are Okabe–Ito. All 8 stay distinct under every common
  colour-vision deficiency, which a Crameri map cut into lines does not do.
  ROLE fixes the meaning of a colour across papers: "ours" is always blue and
  "baseline" is always vermillion.
- Continuous data uses Crameri's Scientific colour maps. They are perceptually
  uniform and grayscale-safe (Crameri et al., Nat. Commun. 11, 5444, 2020).
  Never use jet, rainbow or turbo.
- Widths are the class's own \\textwidth / \\columnwidth. They were measured
  with pdflatex on 2026-09-26, except acm-col (acmart's documented value).
  The figure is drawn at print size and included at width=\\textwidth or
  \\columnwidth, so 8 pt text in the plot is 8 pt on the page and stays
  readable.
- The type is serif Computer Modern (mathtext "cm"), so labels match the
  LNCS/IEEE body text. No LaTeX install is needed, so nightly runs on any
  machine work. use(..., usetex=True) typesets through real LaTeX when you
  want exact kerning.
- ps.save writes a PDF next to the PNG. Include the .pdf in the paper (vector);
  the PNG is only for quick looks and Markdown.
- No titles inside figures: the caption is the title in every venue we target.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

try:  # Crameri maps; fall back to viridis-family so a missing package never breaks a run
    from cmcrameri import cm as _cmc
    SEQ, DIV, CYC = _cmc.batlow, _cmc.vik, _cmc.romaO
except ImportError:  # pragma: no cover
    SEQ, DIV, CYC = mpl.colormaps["viridis"], mpl.colormaps["RdBu_r"], mpl.colormaps["twilight"]

# Okabe & Ito (2008), in cycle order: most distinct pairs first.
OKABE_ITO = {
    "blue": "#0072B2", "vermillion": "#D55E00", "green": "#009E73", "orange": "#E69F00",
    "purple": "#CC79A7", "sky": "#56B4E9", "yellow": "#F0E442", "black": "#000000",
}
CYCLE = list(OKABE_ITO.values())
ROLE = {
    "ours": OKABE_ITO["blue"],
    "baseline": OKABE_ITO["vermillion"],
    "alt": OKABE_ITO["green"],        # a second competitor / variant
    "alt2": OKABE_ITO["orange"],
    "oracle": OKABE_ITO["black"],     # exact value from PRISM/Storm/MATLAB
    "bound": "#7F7F7F",               # thresholds, closed-form bounds, guides
    "band": "#BFBFBF",                # uncertainty fill behind a line
}

PT = 1 / 72.27  # TeX points per inch
# venue -> (text width in, column width in, base font pt for figure text)
VENUES = {
    "lncs":       (347.12 * PT, 347.12 * PT, 8),
    "ieee":       (516.0 * PT, 252.0 * PT, 8),
    "acm":        (506.30 * PT, 241.15 * PT, 7),
    "springer":   (338.0 * PT, 338.0 * PT, 8),    # svjour3 smallextended (EMSE etc.)
    "springer2c": (495.0 * PT, 238.96 * PT, 8),   # svjour3 twocolumn
}


def use(venue: str = "lncs", usetex: bool = False) -> None:
    """Set rcParams for `venue`. Call once at the top of a figure script."""
    if venue not in VENUES:
        raise ValueError(f"venue must be one of {sorted(VENUES)}")
    base = VENUES[venue][2]
    usetex = usetex and shutil.which("latex") is not None
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["CMU Serif", "Computer Modern Roman", "cmr10", "DejaVu Serif"],
        "mathtext.fontset": "cm",
        "axes.formatter.use_mathtext": True,
        "axes.unicode_minus": False,    # cmr10 has no U+2212 glyph
        "text.usetex": usetex,
        "font.size": base,
        "axes.labelsize": base,
        "axes.titlesize": base,
        "legend.fontsize": base - 1,
        "xtick.labelsize": base - 1,
        "ytick.labelsize": base - 1,
        "axes.prop_cycle": mpl.cycler(color=CYCLE),
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "lines.linewidth": 1.2,
        "lines.markersize": 3.5,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "legend.frameon": False,
        "legend.handlelength": 1.6,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,   # embed TrueType: editable in Inkscape, accepted by IEEE PDF eXpress
        "ps.fonttype": 42,
        "image.cmap": SEQ.name if hasattr(SEQ, "name") else "viridis",
    })
    try:
        mpl.colormaps.register(SEQ, name=SEQ.name, force=True)
    except (ValueError, AttributeError, TypeError):
        pass


def figure(venue: str = "lncs", width: str | float = "text", aspect: float = 0.62,
           nrows: int = 1, ncols: int = 1, **kw):
    """plt.subplots sized for print. width: "text", "col", or a fraction of \\textwidth.
    aspect = height / width (0.62 ≈ golden ratio)."""
    tw, cw, _ = VENUES[venue]
    w = tw if width == "text" else cw if width == "col" else tw * float(width)
    return plt.subplots(nrows, ncols, figsize=(w, w * aspect), **kw)


def save(fig, stem: str | Path, png: bool = True) -> Path:
    """Write <stem>.pdf (vector, for the paper) and, by default, <stem>.png."""
    stem = Path(stem).with_suffix("")
    fig.savefig(stem.with_suffix(".pdf"))
    if png:
        fig.savefig(stem.with_suffix(".png"))
    plt.close(fig)
    return stem.with_suffix(".pdf")

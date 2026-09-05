"""The pixel-art deity artwork shown beside the dashboard.

Preferred source is a real pixel-art image dropped into ``assets/`` (see
``ASSET_NAMES``). It is inlined as a base64 data URI so it renders without
Streamlit's static-file serving needing to be configured, and is scaled with
``image-rendering: pixelated`` so the pixel grid stays crisp instead of being
smoothed into mush by the browser's default interpolation.

If no such file is present, a hand-authored SVG silhouette is drawn instead so
the layout never has a hole in it. That fallback is stored as run-length spans
(one ``(start_col, end_col)`` pair per filled run) rather than a character
bitmap, which keeps it readable and lets the renderer emit one ``<rect>`` per
run instead of one per pixel.

This is decorative artwork — the only fixed content in the dashboard. Every
numeric value on the page is computed from the datasets at runtime.
"""
from __future__ import annotations

import base64
import functools
from pathlib import Path

# Logical grid size of the artwork.
GRID_WIDTH = 30

# Standing Sri Venkateswara silhouette, following the reference motif: a tall
# tiered kireetam (crown) narrowing to a small head, modest arms at mid height,
# then a robe that flares steadily to a stepped lotus pedestal — the widest
# point of the figure is the base, not the shoulders.
#
# Each row is a tuple of filled column runs, so a row can contain gaps. The
# renderer emits one <rect> per run, keeping the inline SVG small.
FIGURE_SPANS: tuple[tuple[tuple[int, int], ...], ...] = (
    ((14, 15),),           # finial
    ((13, 16),),
    ((12, 17),),           # crown, tier 1
    ((12, 17),),
    ((11, 18),),           # crown, tier 2
    ((11, 18),),
    ((10, 19),),           # crown, tier 3
    ((10, 19),),
    ((9, 20),),            # crown base band
    ((12, 17),),           # head
    ((12, 17),),
    ((12, 17),),
    ((13, 16),),           # neck
    ((11, 18),),           # shoulders
    ((10, 19),),
    ((8, 21),),            # upper arms
    ((6, 23),),            # arms at full span
    ((6, 23),),
    ((7, 22),),            # forearms
    ((10, 19),),           # arms end, torso resumes
    ((10, 19),),
    ((10, 19),),
    ((9, 20),),
    ((9, 20),),            # garland
    ((9, 20),),
    ((8, 21),),
    ((8, 21),),            # waist sash
    ((8, 21),),
    ((7, 22),),
    ((7, 22),),            # robe
    ((7, 22),),
    ((6, 23),),
    ((6, 23),),            # robe flare
    ((5, 24),),
    ((5, 24),),
    ((4, 25),),            # pedestal, step 1
    ((3, 26),),            # pedestal, step 2 (widest)
    ((4, 25),),            # pedestal, step 3
)

# Lighter accent runs drawn over the silhouette: the vertical urdhva pundra
# (namam) down the crown and forehead, plus the garland and waist bands.
ACCENT_SPANS: dict[int, tuple[tuple[int, int], ...]] = {
    4: ((14, 15),),
    5: ((14, 15),),
    6: ((14, 15),),
    7: ((14, 15),),
    8: ((14, 15),),
    9: ((14, 15),),
    10: ((14, 15),),
    11: ((14, 15),),
    23: ((9, 20),),        # garland band
    26: ((8, 21),),        # waist sash
}

GRID_HEIGHT = len(FIGURE_SPANS)


# Artwork is looked up under assets/ in this order; the first hit wins.
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
ASSET_NAMES = (
    "deity.png",
    "deity.webp",
    "deity.jpg",
    "deity.jpeg",
    "deity.gif",
)

_MIME = {
    ".png": "image/png",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
}


def find_asset() -> Path | None:
    """Return the artwork file to use, or None when none is present."""
    for name in ASSET_NAMES:
        candidate = ASSET_DIR / name
        if candidate.is_file():
            return candidate
    return None


@functools.lru_cache(maxsize=4)
def _data_uri(path_str: str, mtime: float) -> str:
    """Base64 data URI for ``path_str``.

    ``mtime`` is part of the cache key so replacing the artwork on disk
    invalidates the cached copy rather than serving the old bytes.
    """
    path = Path(path_str)
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    mime = _MIME.get(path.suffix.lower(), "image/png")
    return f"data:{mime};base64,{encoded}"


def render_html(alt: str = "Pixel-art image of Sri Venkateswara") -> str:
    """The artwork as an HTML fragment: the asset if present, else the SVG."""
    asset = find_asset()
    if asset is None:
        return render_svg()

    uri = _data_uri(str(asset), asset.stat().st_mtime)
    # image-rendering keeps pixel art sharp when scaled up; without it the
    # browser smooths the pixel grid into mush. crisp-edges is declared first
    # as the older-browser fallback so that pixelated, the better choice for
    # upscaling, is the one that actually takes effect.
    return (
        f'<img src="{uri}" alt="{alt}" '
        'style="width:100%;height:auto;display:block;'
        'image-rendering:crisp-edges;image-rendering:pixelated;" />'
    )


def render_svg(
    fill: str = "#26272b",
    accent: str = "#303136",
    pixel: int = 12,
    gap: int = 1,
) -> str:
    """Render the silhouette as a standalone inline SVG string.

    ``pixel`` is the size of one art pixel and ``gap`` the space left between
    pixels, which is what gives the figure its blocky, tiled look.
    """
    step = pixel + gap
    width = GRID_WIDTH * step
    height = GRID_HEIGHT * step

    rects: list[str] = []

    def emit(row: int, spans, colour: str) -> None:
        for start, end in spans:
            x = start * step
            run_width = (end - start + 1) * step - gap
            rects.append(
                f'<rect x="{x}" y="{row * step}" '
                f'width="{run_width}" height="{pixel}" fill="{colour}"/>'
            )

    for row, spans in enumerate(FIGURE_SPANS):
        emit(row, spans, fill)
    for row, spans in ACCENT_SPANS.items():
        emit(row, spans, accent)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" height="100%" preserveAspectRatio="xMidYMin meet" '
        f'role="img" aria-label="Pixel-art silhouette of Sri Venkateswara" '
        f'shape-rendering="crispEdges">{"".join(rects)}</svg>'
    )

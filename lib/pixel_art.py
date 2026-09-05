"""Pixel-art deity silhouette used as the dashboard's backdrop motif.

The figure is stored as run-length spans (one ``(start_col, end_col)`` pair per
filled run) instead of a character bitmap. That keeps the source readable and
symmetric, and lets the renderer emit one ``<rect>`` per run rather than one
per pixel, so the inline SVG stays small.

This is decorative artwork, not data — it is the only fixed content in the
dashboard. Everything numeric is computed from the datasets at runtime.
"""
from __future__ import annotations

# Logical grid size of the artwork.
GRID_WIDTH = 32

# Standing Sri Venkateswara silhouette, top to bottom: the kireetam (crown),
# head, shoulders, arms with the detached shankha and chakra attributes, torso
# with garland, dhoti, legs and lotus pedestal.
#
# Each row is a tuple of filled column runs, so a row can contain gaps — which
# is what separates the attributes from the arms and keeps the figure reading as
# a body rather than a solid block.
FIGURE_SPANS: tuple[tuple[tuple[int, int], ...], ...] = (
    ((15, 16),),                          # crown finial
    ((14, 17),),
    ((13, 18),),                          # crown, upper tier
    ((12, 19),),
    ((12, 19),),
    ((11, 20),),                          # crown, lower tier
    ((11, 20),),
    ((10, 21),),                          # crown base band
    ((13, 18),),                          # forehead
    ((13, 18),),
    ((13, 18),),                          # face
    ((14, 17),),                          # chin
    ((14, 17),),                          # neck
    ((11, 20),),                          # shoulders
    ((9, 22),),
    ((5, 7), (9, 22), (24, 26)),          # attributes raised beside the arms
    ((4, 8), (8, 23), (23, 27)),
    ((4, 8), (7, 24), (23, 27)),          # arms at full span
    ((5, 7), (7, 24), (24, 26)),
    ((9, 22),),                           # forearms drop back to the body
    ((11, 20),),                          # underarm gap closes: upper torso
    ((11, 20),),
    ((12, 19),),
    ((12, 19),),                          # garland
    ((12, 19),),
    ((12, 19),),
    ((11, 20),),
    ((11, 20),),                          # waist
    ((10, 21),),
    ((10, 21),),                          # dhoti
    ((10, 21),),
    ((11, 20),),
    ((11, 20),),                          # legs
    ((12, 19),),
    ((12, 19),),
    ((9, 22),),                           # pedestal, upper step
    ((7, 24),),
    ((8, 23),),
)

# Lighter accent runs drawn over the silhouette: the vertical urdhva pundra
# (namam) down the crown and forehead, plus highlights on the two attributes.
ACCENT_SPANS: dict[int, tuple[tuple[int, int], ...]] = {
    5: ((15, 16),),
    6: ((15, 16),),
    7: ((15, 16),),
    8: ((15, 16),),
    9: ((15, 16),),
    10: ((15, 16),),
    16: ((7, 8), (23, 24)),
    22: ((12, 19),),   # garland band
    26: ((11, 20),),   # waist sash
}

GRID_HEIGHT = len(FIGURE_SPANS)


def render_svg(
    fill: str = "#24252c",
    accent: str = "#2f3038",
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

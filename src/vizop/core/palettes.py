"""Color palette definitions for vizop charts."""

HIGHLIGHT_MUTED_COLOR = "#D3D3D3"

# Each palette is an ordered list of hex colors.
# First color is used as the primary/accent when only one series is present.

PALETTES: dict[str, list[str]] = {
    "default": [
        "#4E79A7",
        "#F28E2B",
        "#E15759",
        "#76B7B2",
        "#59A14F",
        "#EDC948",
        "#B07AA1",
        "#FF9DA7",
        "#9C755F",
        "#BAB0AC",
    ],
    "warm": [
        "#E15759",
        "#F28E2B",
        "#EDC948",
        "#FF9DA7",
        "#B07AA1",
    ],
    "cool": [
        "#4E79A7",
        "#76B7B2",
        "#59A14F",
        "#A0CBE8",
        "#8CD17D",
    ],
    "diverging": [
        "#4E79A7",
        "#A0CBE8",
        "#BAB0AC",
        "#F28E2B",
        "#E15759",
    ],
    "muted": [
        "#8CD17D",
        "#A0CBE8",
        "#FFBE7D",
        "#D4A6C8",
        "#FABFD2",
        "#B6992D",
        "#D7B5A6",
    ],
}


def get_palette(name: str = "default") -> list[str]:
    """Return a palette by name, raising ValueError for unknown palettes."""
    if name not in PALETTES:
        available = ", ".join(sorted(PALETTES.keys()))
        raise ValueError(f"Unknown palette '{name}'. Available: {available}")
    return PALETTES[name]


def get_colors(
    n: int,
    *,
    palette: str = "default",
    accent_color: str | None = None,
) -> list[str]:
    """Return n colors from a palette.

    If accent_color is provided, it replaces the first color in the palette.
    Cycles if n exceeds palette length.
    """
    colors = list(get_palette(palette))
    if accent_color:
        colors[0] = accent_color

    if n <= len(colors):
        return colors[:n]

    # Cycle through palette for extra colors
    result = []
    for i in range(n):
        result.append(colors[i % len(colors)])
    return result

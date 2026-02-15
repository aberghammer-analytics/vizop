"""Color palette definitions and shared color-assignment logic for vizop charts."""

import warnings

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


def normalize_highlight(highlight: str | list[str] | None) -> set[str]:
    """Convert a highlight param to a set of names."""
    if highlight is None:
        return set()
    if isinstance(highlight, str):
        return {highlight}
    return set(highlight)


def assign_colors(
    series_names: list[str],
    *,
    accent_color: str | None,
    palette: str,
    highlight: str | list[str] | None,
    color_map: dict[str, str] | None = None,
    config_accent: str = "#4E79A7",
) -> dict[str, str]:
    """Map each series name to a color.

    Args:
        series_names: Ordered list of series/category names.
        accent_color: User-specified override for the primary color.
        palette: Palette name for multi-series.
        highlight: Name(s) to highlight; others muted.
        color_map: Explicit name→color mapping. Unmapped names get muted gray.
        config_accent: Accent color from VizopConfig (avoids importing config).
    """
    if color_map:
        unknown = set(color_map) - set(series_names)
        if unknown:
            warnings.warn(
                f"color_map contains keys not found in series: {sorted(unknown)}",
                stacklevel=3,
            )

    # Single-series: color_map wins over accent_color
    if len(series_names) == 1:
        name = series_names[0]
        if color_map and name in color_map:
            return {name: color_map[name]}
        color = accent_color or config_accent
        return {name: color}

    # Multi-series with color_map
    if color_map is not None:
        return {name: color_map.get(name, HIGHLIGHT_MUTED_COLOR) for name in series_names}

    # Multi-series with highlight
    highlight_set = normalize_highlight(highlight)
    if highlight_set:
        highlighted = [n for n in series_names if n in highlight_set]
        palette_colors = get_colors(len(highlighted), palette=palette, accent_color=accent_color)
        result: dict[str, str] = {}
        color_idx = 0
        for name in series_names:
            if name in highlight_set:
                result[name] = palette_colors[color_idx]
                color_idx += 1
            else:
                result[name] = HIGHLIGHT_MUTED_COLOR
        return result

    # Multi-series, no highlight, no color_map
    palette_colors = get_colors(len(series_names), palette=palette, accent_color=accent_color)
    return dict(zip(series_names, palette_colors, strict=False))

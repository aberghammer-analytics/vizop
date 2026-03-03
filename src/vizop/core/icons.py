"""Built-in icon definitions for waffle charts.

Each icon is a matplotlib.path.Path normalized to the unit square (0,0) -> (1,1).
"""

import numpy as np
from matplotlib.path import Path

# Path code shortcuts
_M = Path.MOVETO
_L = Path.LINETO
_C = Path.CURVE4
_Z = Path.CLOSEPOLY


def _make_path(vertices: list[tuple[float, float]], codes: list[int]) -> Path:
    """Create a Path from vertices and codes."""
    return Path(np.array(vertices, dtype=float), codes, readonly=True)


# ---------------------------------------------------------------------------
# Built-in icons — each fits within the unit square (0,0) -> (1,1)
# ---------------------------------------------------------------------------

_PERSON = _make_path(
    [
        # Head (circle approximated with bezier curves)
        (0.50, 1.00),
        (0.62, 1.00),
        (0.72, 0.90),
        (0.72, 0.78),
        (0.72, 0.66),
        (0.62, 0.56),
        (0.50, 0.56),
        (0.38, 0.56),
        (0.28, 0.66),
        (0.28, 0.78),
        (0.28, 0.90),
        (0.38, 1.00),
        (0.50, 1.00),
        (0.50, 1.00),
        # Body (torso + legs)
        (0.50, 0.52),
        (0.78, 0.42),
        (0.92, 0.28),
        (0.92, 0.28),
        (0.92, 0.18),
        (0.82, 0.00),
        (0.82, 0.00),
        (0.50, 0.14),
        (0.18, 0.00),
        (0.18, 0.00),
        (0.08, 0.18),
        (0.08, 0.28),
        (0.08, 0.28),
        (0.22, 0.42),
        (0.50, 0.52),
        (0.50, 0.52),
    ],
    [
        _M,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _Z,
        _M,
        _L,
        _C,
        _C,
        _C,
        _C,
        _C,
        _L,
        _L,
        _C,
        _C,
        _C,
        _C,
        _L,
        _L,
        _Z,
    ],
)

_CIRCLE = _make_path(
    [
        (0.50, 1.00),
        (0.78, 1.00),
        (1.00, 0.78),
        (1.00, 0.50),
        (1.00, 0.22),
        (0.78, 0.00),
        (0.50, 0.00),
        (0.22, 0.00),
        (0.00, 0.22),
        (0.00, 0.50),
        (0.00, 0.78),
        (0.22, 1.00),
        (0.50, 1.00),
        (0.50, 1.00),
    ],
    [_M, _C, _C, _C, _C, _C, _C, _C, _C, _C, _C, _C, _C, _Z],
)

_SQUARE = _make_path(
    [
        (0.05, 0.05),
        (0.95, 0.05),
        (0.95, 0.95),
        (0.05, 0.95),
        (0.05, 0.05),
    ],
    [_M, _L, _L, _L, _Z],
)

_HOUSE = _make_path(
    [
        # Roof
        (0.50, 1.00),
        (1.00, 0.55),
        (0.85, 0.55),
        # Right wall
        (0.85, 0.00),
        # Bottom
        (0.15, 0.00),
        # Left wall
        (0.15, 0.55),
        (0.00, 0.55),
        (0.50, 1.00),
    ],
    [_M, _L, _L, _L, _L, _L, _L, _Z],
)

_DOLLAR = _make_path(
    [
        # Top serif of the vertical bar
        (0.45, 1.00),
        (0.55, 1.00),
        (0.55, 0.88),
        # Top curve of S
        (0.72, 0.86),
        (0.82, 0.76),
        (0.82, 0.68),
        (0.82, 0.58),
        (0.68, 0.52),
        (0.55, 0.50),
        # Middle
        (0.45, 0.48),
        # Bottom curve of S
        (0.32, 0.46),
        (0.18, 0.38),
        (0.18, 0.30),
        (0.18, 0.22),
        (0.28, 0.14),
        (0.45, 0.12),
        # Bottom serif
        (0.45, 0.00),
        (0.55, 0.00),
        (0.55, 0.12),
        # Mirror bottom curve
        (0.72, 0.14),
        (0.82, 0.22),
        (0.82, 0.30),
        # Back up through middle
        (0.82, 0.38),
        (0.68, 0.46),
        (0.55, 0.48),
        (0.45, 0.50),
        # Mirror top curve
        (0.32, 0.52),
        (0.18, 0.58),
        (0.18, 0.68),
        (0.18, 0.76),
        (0.28, 0.86),
        (0.45, 0.88),
        (0.45, 1.00),
    ],
    [
        _M,
        _L,
        _L,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _L,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _L,
        _L,
        _L,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _C,
        _Z,
    ],
)

_HEART = _make_path(
    [
        # Bottom tip
        (0.50, 0.10),
        # Curve 1: right side going up
        (0.50, 0.25),
        (1.00, 0.50),
        (1.00, 0.72),
        # Curve 2: right lobe curving to center dip
        (1.00, 0.92),
        (0.72, 1.00),
        (0.50, 0.78),
        # Curve 3: left lobe from center dip
        (0.28, 1.00),
        (0.00, 0.92),
        (0.00, 0.72),
        # Curve 4: left side going down to bottom tip
        (0.00, 0.50),
        (0.50, 0.25),
        (0.50, 0.10),
        # CLOSEPOLY
        (0.50, 0.10),
    ],
    [_M, _C, _C, _C, _C, _C, _C, _C, _C, _C, _C, _C, _C, _Z],
)


ICONS: dict[str, Path] = {
    "person": _PERSON,
    "circle": _CIRCLE,
    "square": _SQUARE,
    "house": _HOUSE,
    "dollar": _DOLLAR,
    "heart": _HEART,
}


def get_icon(icon: str | Path) -> Path:
    """Look up a built-in icon by name, or pass through a custom Path.

    Args:
        icon: Built-in icon name (person, circle, square, house, dollar, heart)
              or a matplotlib.path.Path instance.

    Returns:
        A matplotlib Path normalized to the unit square.

    Raises:
        ValueError: If icon name is not recognized.
    """
    if isinstance(icon, Path):
        return icon
    name = icon.lower()
    if name not in ICONS:
        available = ", ".join(sorted(ICONS.keys()))
        raise ValueError(f"Unknown icon '{icon}'. Available: {available}")
    return ICONS[name]

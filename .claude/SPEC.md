# vizop — Implementation Spec (v0.1)

## Overview

vizop is an opinionated Python data visualization package that produces publication-quality charts (NYT, FiveThirtyEight style) with minimal configuration. The user thinks like an editor — they provide data, a title, and annotations. The package handles all visual design decisions.

v0.1 is matplotlib-only (static output). Plotly interactive backend is planned for v0.2 and is NOT in scope.

---

## Project Setup

### Tooling

| Tool | Purpose |
|------|---------|
| **uv** | Package/dependency management, virtual environments, building |
| **ruff** | Linting and formatting |
| **pytest** | Testing |
| **pydantic** | All data models and config (NO dataclasses anywhere) |
| **matplotlib** | Rendering engine |

### Python Version

- Minimum: Python 3.10
- Use modern syntax: `X | None` instead of `Optional[X]`, `list[str]` instead of `List[str]`, etc.

### Project Initialization

```bash
uv init vizop --lib
cd vizop
uv add matplotlib pydantic numpy pandas
uv add --dev pytest ruff
```

### pyproject.toml Configuration

```toml
[project]
name = "vizop"
version = "0.1.0"
description = "Opinionated, publication-quality data visualization"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
dependencies = [
    "matplotlib>=3.8",
    "pydantic>=2.0",
    "numpy>=1.24",
    "pandas>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "ruff>=0.4",
]

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "TCH"]

[tool.ruff.format]
quote-style = "double"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Package Structure

```
vizop/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── vizop/
│       ├── __init__.py              # Public API exports
│       ├── charts/
│       │   ├── __init__.py
│       │   ├── line.py              # vizop.line()
│       │   ├── bar.py               # vizop.bar()
│       │   ├── scatter.py           # vizop.scatter()
│       │   ├── slope.py             # vizop.slope()
│       │   └── waffle.py            # vizop.waffle()
│       ├── core/
│       │   ├── __init__.py
│       │   ├── chart.py             # Chart return object
│       │   ├── config.py            # Global config + configure()
│       │   ├── theme.py             # Theme constants, typography, layout
│       │   ├── annotations.py       # Annotation rendering + collision avoidance
│       │   ├── formatting.py        # Number formatting + auto-detection
│       │   ├── palettes.py          # Color palette definitions
│       │   └── fonts.py             # Font registration and management
│       ├── assets/
│       │   └── fonts/
│       │       ├── Inter/            # Default font (OFL license)
│       │       │   ├── Inter-Regular.ttf
│       │       │   ├── Inter-SemiBold.ttf
│       │       │   └── Inter-Bold.ttf
│       │       ├── LibreFranklin/    # NYT-style option
│       │       │   ├── LibreFranklin-Regular.ttf
│       │       │   ├── LibreFranklin-SemiBold.ttf
│       │       │   └── LibreFranklin-Bold.ttf
│       │       ├── SourceSansPro/   # Clean Adobe font
│       │       │   ├── SourceSansPro-Regular.ttf
│       │       │   ├── SourceSansPro-SemiBold.ttf
│       │       │   └── SourceSansPro-Bold.ttf
│       │       └── IBMPlexSans/     # Modern technical font
│       │           ├── IBMPlexSans-Regular.ttf
│       │           ├── IBMPlexSans-SemiBold.ttf
│       │           └── IBMPlexSans-Bold.ttf
│       └── py.typed                 # PEP 561 marker
├── tests/
│   ├── conftest.py                  # Shared fixtures (sample DataFrames, etc.)
│   ├── test_line.py
│   ├── test_bar.py
│   ├── test_scatter.py
│   ├── test_slope.py
│   ├── test_waffle.py
│   ├── test_config.py
│   ├── test_formatting.py
│   └── test_chart.py
└── examples/
    └── gallery.py                   # One script showing all 5 chart types
```

### Font Bundling

Fonts are bundled inside the package under `src/vizop/assets/fonts/`. On first import, vizop registers the bundled fonts with matplotlib's font manager. Users can override with `vizop.configure(font="Arial")` or any system-installed font — if the requested font isn't found, fall back to the default (Inter).

Each bundled font needs three weights: Regular, SemiBold, Bold. Download from Google Fonts (all are OFL-licensed). Include license files in each font directory.

---

## Public API

### `__init__.py` Exports

```python
from vizop.charts.line import line
from vizop.charts.bar import bar
from vizop.charts.scatter import scatter
from vizop.charts.slope import slope
from vizop.charts.waffle import waffle
from vizop.core.config import configure

__all__ = ["line", "bar", "scatter", "slope", "waffle", "configure"]
```

Usage:

```python
import vizop

vizop.configure(font="Libre Franklin", accent_color="#E15759")

chart = vizop.line(data=df, x="date", y="value", title="My Chart")
chart.show()
chart.save("chart.png")
```

---

## Core Models (Pydantic)

### `core/config.py` — Global Configuration

```python
from pydantic import BaseModel, Field

class VizopConfig(BaseModel):
    accent_color: str = "#E15759"
    font: str = "Inter"
    background: str = "white"  # "white" or "light_gray"
    size: str = "standard"     # "standard", "wide", "tall"
    source_label: str = ""
    preset: str | None = None  # "fivethirtyeight", "nytimes", "economist"

# Module-level singleton
_config = VizopConfig()

def configure(**kwargs) -> None:
    """Update global configuration."""
    global _config
    if "preset" in kwargs:
        _config = _apply_preset(kwargs["preset"])
    else:
        _config = _config.model_copy(update=kwargs)

def get_config() -> VizopConfig:
    return _config
```

### Preset Definitions

```python
PRESETS = {
    "fivethirtyeight": VizopConfig(
        accent_color="#FF6B35",
        font="Inter",
        background="light_gray",  # 538's signature warm gray: #F0F0F0
    ),
    "nytimes": VizopConfig(
        accent_color="#121212",
        font="Libre Franklin",
        background="white",
    ),
    "economist": VizopConfig(
        accent_color="#E3120B",
        font="Source Sans Pro",
        background="white",
    ),
}
```

### `core/chart.py` — Return Object

```python
import base64
from io import BytesIO
from pathlib import Path
from matplotlib.figure import Figure

class Chart:
    """Wrapper around a matplotlib Figure with convenience methods."""

    def __init__(self, fig: Figure, title: str):
        self.fig = fig
        self.title = title

    def show(self) -> None:
        """Display inline (notebooks) or in a window."""
        self.fig.show()

    def save(self, path: str | Path, dpi: int = 300) -> None:
        """Save as PNG, PDF, or SVG based on file extension."""
        path = Path(path)
        self.fig.savefig(
            path,
            dpi=dpi,
            bbox_inches="tight",
            facecolor=self.fig.get_facecolor(),
            pad_inches=0.3,
        )

    def to_base64(self, dpi: int = 150) -> str:
        """Return base64-encoded PNG string (for MCP server integration)."""
        buf = BytesIO()
        self.fig.savefig(
            buf,
            format="png",
            dpi=dpi,
            bbox_inches="tight",
            facecolor=self.fig.get_facecolor(),
            pad_inches=0.3,
        )
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    def __repr__(self) -> str:
        return f"Chart(title='{self.title}')"
```

---

## Theme System

### `core/theme.py`

This file defines all hardcoded visual constants. Nothing here is exposed to the user.

```python
from pydantic import BaseModel

class SizeSpec(BaseModel):
    width: float   # inches
    height: float  # inches

SIZES: dict[str, SizeSpec] = {
    "standard": SizeSpec(width=7.5, height=5.0),
    "wide": SizeSpec(width=10.0, height=5.0),
    "tall": SizeSpec(width=7.5, height=6.67),
}

class Typography(BaseModel):
    title_size: float = 20.0
    title_weight: str = "bold"
    title_color: str = "#1A1A1A"

    subtitle_size: float = 13.0
    subtitle_weight: str = "regular"
    subtitle_color: str = "#6B6B6B"

    axis_label_size: float = 11.0
    axis_label_color: str = "#6B6B6B"

    tick_size: float = 11.0
    tick_color: str = "#8E8E8E"

    annotation_size: float = 11.0
    annotation_color: str = "#4A4A4A"

    value_label_size: float = 11.0
    value_label_weight: str = "semibold"
    value_label_color: str = "#1A1A1A"

    source_size: float = 9.0
    source_color: str = "#8E8E8E"

class Layout(BaseModel):
    # Margins as fraction of figure
    title_pad: float = 12.0           # pts below title
    subtitle_pad: float = 16.0        # pts below subtitle before plot
    source_pad: float = 8.0           # pts below plot before source

    gridline_color: str = "#E5E5E5"
    gridline_width: float = 0.8
    gridline_style: str = "-"

    spine_visible: list[str] = ["bottom"]  # which spines to show
    spine_color: str = "#CCCCCC"
    spine_width: float = 0.8

    background_colors: dict[str, str] = {
        "white": "#FFFFFF",
        "light_gray": "#F0F0F0",
    }

    line_width_primary: float = 2.5
    line_width_secondary: float = 1.5
    line_width_muted: float = 1.0

    bar_width: float = 0.6
    bar_corner_radius: float = 2.0     # px, subtle rounding

    point_size: float = 40.0           # scatter marker size
    point_opacity: float = 0.7

    annotation_arrow_color: str = "#999999"
    annotation_arrow_width: float = 0.8
```

### Background Colors

| Config Value | Color | Description |
|---|---|---|
| `"white"` | `#FFFFFF` | Clean, NYT-style |
| `"light_gray"` | `#F0F0F0` | Warm gray, 538-style |

The figure `facecolor` AND axes `facecolor` should both be set so the background is consistent.

---

## Color Palettes

### `core/palettes.py`

```python
PALETTES: dict[str, list[str]] = {
    "default": [
        "#4E79A7",  # steel blue
        "#F28E2B",  # warm orange
        "#E15759",  # warm red
        "#76B7B2",  # teal
        "#59A14F",  # green
        "#EDC948",  # gold
    ],
    "warm": ["#E15759", "#F28E2B", "#EDC948", "#FF9DA7", "#FFBE7D", "#F1CE63"],
    "cool": ["#4E79A7", "#76B7B2", "#59A14F", "#499894", "#86BCB6", "#8CD17D"],
    "diverging": ["#4E79A7", "#A0CBE8", "#E8E8E8", "#FFB7B7", "#E15759"],
    "muted": ["#8C8C8C", "#A6A6A6", "#BFBFBF", "#737373", "#999999", "#B3B3B3"],
}

HIGHLIGHT_MUTED_COLOR = "#D3D3D3"
```

### Highlight Behavior

When `highlight` is set on any chart:
1. Items matching `highlight` get their palette color (or `accent_color` if single series)
2. All other items get `HIGHLIGHT_MUTED_COLOR` (#D3D3D3)
3. Highlighted items render ON TOP of muted items (z-order)

---

## Number Formatting

### `core/formatting.py`

```python
def auto_detect_format(column_name: str, values: pd.Series) -> str:
    """Detect number format from column name and value range."""
    name_lower = column_name.lower()

    # Check column name patterns
    pct_keywords = ["pct", "rate", "share", "percent", "ratio", "proportion"]
    dollar_keywords = ["price", "cost", "income", "wage", "salary", "revenue",
                       "gdp", "spend", "budget", "profit", "loss"]

    if any(kw in name_lower for kw in pct_keywords):
        return "percent"
    if any(kw in name_lower for kw in dollar_keywords):
        return "dollar"

    # Check value range
    if values.between(0, 1).all() and values.max() <= 1:
        return "percent"  # likely decimal percentages
    if values.abs().max() > 1000:
        return "comma"

    return "decimal"


def format_value(value: float, fmt: str) -> str:
    """Format a single value for display."""
    if fmt == "percent":
        if abs(value) < 1:
            return f"{value * 100:.1f}%"    # 0.452 → "45.2%"
        return f"{value:.1f}%"               # 45.2 → "45.2%"
    elif fmt == "dollar":
        if abs(value) >= 1_000_000_000:
            return f"${value / 1_000_000_000:.1f}B"
        elif abs(value) >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        elif abs(value) >= 1_000:
            return f"${value / 1_000:.0f}K"
        return f"${value:,.0f}"
    elif fmt == "comma":
        if abs(value) >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f}B"
        elif abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        return f"{value:,.0f}"
    else:  # decimal
        return f"{value:.2f}"


def format_tick(value: float, fmt: str) -> str:
    """Format for axis tick labels (shorter than value labels)."""
    # Same logic as format_value but can be tuned separately
    return format_value(value, fmt)
```

---

## Annotation Engine

### `core/annotations.py`

This is the hardest piece of engineering in the package. Annotations must:
1. Connect to the correct data point with a leader line
2. Not overlap each other
3. Not overlap data points
4. Position text legibly

#### v0.1 Approach (Simple but Functional)

For v0.1, use a simplified placement strategy:

1. For each annotation, calculate a default text position offset from the data point
2. Check for overlap against all other annotation bounding boxes
3. If overlapping, try alternate positions (above, below, left, right)
4. If all positions overlap, use the position with least overlap

```python
from pydantic import BaseModel

class AnnotationSpec(BaseModel):
    x: float               # data x coordinate
    y: float               # data y coordinate
    text: str              # annotation text
    label: str | None      # data point label (e.g., category name)

class PlacedAnnotation(BaseModel):
    spec: AnnotationSpec
    text_x: float          # text position x (axes coordinates)
    text_y: float          # text position y (axes coordinates)

def place_annotations(
    annotations: list[AnnotationSpec],
    ax,  # matplotlib Axes
    theme,  # Theme config
) -> list[PlacedAnnotation]:
    """Calculate non-overlapping positions for annotations."""
    # Implementation: greedy placement with overlap detection
    ...

def render_annotations(
    placed: list[PlacedAnnotation],
    ax,
    theme,
) -> None:
    """Draw annotation text and leader lines on the axes."""
    for ann in placed:
        ax.annotate(
            ann.spec.text,
            xy=(ann.spec.x, ann.spec.y),
            xytext=(ann.text_x, ann.text_y),
            fontsize=theme.typography.annotation_size,
            color=theme.typography.annotation_color,
            arrowprops=dict(
                arrowstyle="-",
                color=theme.layout.annotation_arrow_color,
                linewidth=theme.layout.annotation_arrow_width,
            ),
            textcoords="axes fraction",
            ha="left",
            va="center",
        )
```

#### Future (v0.2+)

Upgrade to a proper constraint-based placement algorithm (similar to adjustText library). For v0.1, the simple greedy approach is fine.

---

## Chart Implementations

Each chart function follows this pattern:

```python
def line(
    data: pd.DataFrame,
    x: str,
    y: str | list[str],
    title: str,
    # ... other params
) -> Chart:
    # 1. Validate inputs with pydantic
    # 2. Prepare data (shared logic, reusable for future plotly backend)
    # 3. Get config and theme
    # 4. Create matplotlib figure
    # 5. Apply theme (spines, grid, background, fonts)
    # 6. Render chart-specific elements
    # 7. Add title, subtitle, source
    # 8. Render annotations
    # 9. Return Chart object
```

### Shared Rendering Steps (factor into a helper)

Every chart needs these steps applied to the matplotlib figure. Build a helper function like `apply_theme(fig, ax, config, title, subtitle, source, note)` that handles:

- Set figure and axes facecolor
- Remove top/right spines, style bottom/left
- Configure gridlines (horizontal only, subtle)
- Register and apply fonts
- Render title (left-aligned, bold, positioned above plot area)
- Render subtitle (left-aligned, gray, below title)
- Render source line (left-aligned, small, below plot area)
- Render note (if provided, between plot and source)
- Apply figure size from config

**Critical visual rules:**
- Titles are LEFT-ALIGNED to the plot edge, not centered
- Subtitle sits directly below title with minimal gap
- Source/note text sits below the plot area, left-aligned
- Only horizontal gridlines (never vertical, except scatter which has both)
- Y-axis tick labels on the left, no label rotation
- X-axis: auto-thin ticks to prevent overlap, smart date formatting

---

## Chart Type 1: `vizop.line()`

### Function Signature

```python
def line(
    data: pd.DataFrame,
    x: str,
    y: str | list[str],
    title: str,
    subtitle: str = "",
    source: str = "",
    note: str = "",
    group: str | None = None,
    annotate: dict[str, str | None] | None = None,
    highlight: str | list[str] | None = None,
    highlight_range: tuple[str, str] | None = None,
    highlight_range_label: str = "",
    y_format: str | None = None,
    show_last_value: bool = False,
    show_area: bool = False,
    zero_baseline: bool = True,
    color: str | None = None,
    palette: str | list[str] = "default",
) -> Chart:
```

### Rendering Details

- **Single series:** Uses `accent_color` (or `color` override). Line width: 2.5px.
- **Multi-series (list of y columns or group):** Uses palette colors. Direct labels at the end of each line (right side), no legend box. Label text = column name or group value.
- **Highlight mode:** Highlighted series get color, all others get `#D3D3D3` at 1.0px width.
- **highlight_range:** `axvspan` with alpha=0.1 of accent color. Label centered at top of shaded area.
- **show_last_value:** Small text label at the rightmost data point showing the formatted value.
- **show_area:** `fill_between` with alpha=0.15 of line color. Single series only.
- **X-axis dates:** Use matplotlib's `AutoDateLocator` and `ConciseDateFormatter`. Never overlap.
- **Annotations:** Keys are x-values (strings that match values in the x column). Render with leader lines.

---

## Chart Type 2: `vizop.bar()`

### Function Signature

```python
def bar(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    subtitle: str = "",
    source: str = "",
    note: str = "",
    group: str | None = None,
    orientation: str = "horizontal",
    sort: str | None = "descending",
    limit: int | None = None,
    annotate: dict[str, str | None] | None = None,
    highlight: str | list[str] | None = None,
    show_values: bool = True,
    reference_line: float | None = None,
    reference_label: str = "",
    y_format: str | None = None,
    stacked: bool = False,
    color: str | None = None,
    palette: str | list[str] = "default",
) -> Chart:
```

### Rendering Details

- **Horizontal (default):** Categories on y-axis, values on x-axis. Category labels are easy to read.
- **Vertical:** Standard bar chart. Use only when x-axis is ordinal/temporal and order matters.
- **Sorting:** Sort by value before plotting. `"descending"` = largest at top (horizontal) or left (vertical).
- **limit:** After sorting, take top/bottom N.
- **show_values:** Formatted value label at the end of each bar. Right-aligned for horizontal, top for vertical.
- **Grouped bars:** When `group` is set, side-by-side bars. Max 4 groups — raise `ValueError` beyond that.
- **Stacked:** When `group` is set and `stacked=True`, stacked bars.
- **reference_line:** `axvline` (horizontal) or `axhline` (vertical) with dashed style and label.
- **Bar width:** 0.6 ratio. Consistent gap between bars.
- **No bar outlines/borders.** Flat color only.

---

## Chart Type 3: `vizop.scatter()`

### Function Signature

```python
def scatter(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    subtitle: str = "",
    source: str = "",
    note: str = "",
    size: str | None = None,
    group: str | None = None,
    annotate: dict[str, str | None] | None = None,
    label: str | None = None,
    highlight: str | list[str] | None = None,
    trend: bool = False,
    trend_type: str = "linear",
    x_format: str | None = None,
    y_format: str | None = None,
    log_x: bool = False,
    log_y: bool = False,
    jitter: bool = False,
    opacity: float = 0.7,
    color: str | None = None,
    palette: str | list[str] = "default",
) -> Chart:
```

### Rendering Details

- **Points:** Circle markers, default size 40. If `size` column specified, scale proportionally.
- **Group coloring:** Max 6 groups. Small legend below chart (horizontal layout).
- **Trend line:** `np.polyfit` for linear; for `"lowess"`, use `statsmodels.lowess` (add as optional dep — catch ImportError gracefully). Dashed line, muted color, with `fill_between` for 95% CI band (alpha=0.1).
- **Annotations:** Keys match values in the `label` column or the DataFrame index. Annotated points get a text label + optional additional text.
- **label column:** Auto-label ALL points. Use only with small datasets (<20 points). Apply simple overlap avoidance.
- **Gridlines:** Both horizontal AND vertical (scatter is the exception to horizontal-only rule).
- **jitter:** Add small random noise to prevent overplotting. Noise magnitude = 1% of axis range.
- **Log scales:** `ax.set_xscale("log")` / `ax.set_yscale("log")`.

---

## Chart Type 4: `vizop.slope()`

### Function Signature

```python
def slope(
    data: pd.DataFrame,
    label: str,
    left: str,
    right: str,
    title: str,
    subtitle: str = "",
    source: str = "",
    note: str = "",
    left_label: str = "",
    right_label: str = "",
    highlight: str | list[str] | None = None,
    show_change: bool = True,
    change_format: str = "percent",
    annotate: dict[str, str | None] | None = None,
    sort: str | None = "right",
    limit: int | None = 15,
    y_format: str | None = None,
    color_by_direction: bool = False,
    color: str | None = None,
    palette: str | list[str] = "default",
) -> Chart:
```

### Rendering Details

- **Each row = one slope line** connecting two points.
- **X-axis:** Only two positions (left, right). No ticks between them. Label at top.
- **Y-axis:** Hidden entirely. Values shown as labels next to each endpoint.
- **Labels:** Row label text on BOTH sides of the slope. Left-aligned on left, right-aligned on right.
- **Smart label stacking:** When endpoint values are close, offset labels vertically to prevent overlap. Use a greedy algorithm that shifts labels up/down.
- **Endpoint dots:** Circles (6px) at each data point on the line.
- **show_change:** Next to the right-side label, show delta. Format: `+15%`, `-$2.3K`, etc.
- **color_by_direction:** If True, lines going up get blue (`#4E79A7`), lines going down get red (`#E15759`).
- **sort:** Sort rows by left value, right value, or absolute change before rendering.
- **limit:** Max number of rows to display. Applied after sorting.
- **Highlight:** Highlighted rows get full color + thicker line (2.5px). Others get `#D3D3D3` at 1px.

---

## Chart Type 5: `vizop.waffle()`

### Function Signature

```python
def waffle(
    data: pd.DataFrame | None = None,
    category: str | None = None,
    value: str | None = None,
    values: dict[str, float] | None = None,
    title: str = "",
    subtitle: str = "",
    source: str = "",
    note: str = "",
    grid_size: int = 10,
    style: str = "square",
    icon: str | None = None,
    highlight: str | None = None,
    show_values: bool = True,
    show_legend: bool = True,
    per_row: int = 10,
    palette: str | list[str] = "default",
) -> Chart:
```

### Rendering Details

- **Data input:** Either `data` DataFrame with `category` and `value` columns, OR `values` dict. Validate that exactly one is provided.
- **Grid:** `grid_size x grid_size` squares (default 10x10 = 100 cells).
- **Normalization:** Values are normalized to sum to `grid_size^2`. Use largest remainder method for integer rounding so cells always sum exactly to 100.
- **Fill order:** Left-to-right, top-to-bottom. Group cells by category (all Solar cells together, then all Wind cells, etc.).
- **Styles:**
  - `"square"`: `matplotlib.patches.FancyBboxPatch` with slight rounding (pad=0.05). 2px gap between squares.
  - `"circle"`: `matplotlib.patches.Circle` at each grid position.
  - `"icon"`: Custom matplotlib path using Font Awesome glyph paths. See Icon Support below.
- **Legend:** Horizontal layout below the chart. Each entry: color swatch (small square) + category name + percentage value.
- **Max 7 categories.** If more provided, auto-merge the smallest categories into "Other."
- **Highlight:** Highlighted category gets full color, others get muted versions (alpha=0.3 of their palette color).
- **Colors:** Assigned from palette in order of value (largest category = first palette color).

### Icon Support

For `style="icon"`, use matplotlib's ability to render custom marker paths:

1. Bundle a small set of icon SVG paths as Python constants (don't depend on FontAwesome package)
2. Convert SVG path data to matplotlib `Path` objects
3. Render each cell as a marker with the icon path

Built-in icons for v0.1 (just the path data, no external deps):
- `"person"` — simple person silhouette
- `"circle"` — filled circle (same as circle style, but via path)
- `"square"` — filled square (same as square style)
- `"house"` — simple house shape
- `"dollar"` — dollar sign
- `"heart"` — heart shape

If `icon` is specified but not recognized, raise `ValueError` with list of available icons.

The SVG path data for these icons should be stored in `core/icons.py` as matplotlib `Path` objects. Keep them simple — 20-30 vertices max per icon.

---

## Font Management

### `core/fonts.py`

```python
from pathlib import Path
import matplotlib.font_manager as fm

ASSETS_DIR = Path(__file__).parent.parent / "assets" / "fonts"

BUNDLED_FONTS = {
    "Inter": ASSETS_DIR / "Inter",
    "Libre Franklin": ASSETS_DIR / "LibreFranklin",
    "Source Sans Pro": ASSETS_DIR / "SourceSansPro",
    "IBM Plex Sans": ASSETS_DIR / "IBMPlexSans",
}

_fonts_registered = False

def register_fonts() -> None:
    """Register all bundled fonts with matplotlib. Called once on first use."""
    global _fonts_registered
    if _fonts_registered:
        return
    for font_dir in BUNDLED_FONTS.values():
        if font_dir.exists():
            for ttf in font_dir.glob("*.ttf"):
                fm.fontManager.addfont(str(ttf))
    _fonts_registered = True

def get_font_family(font_name: str) -> str:
    """Return the font family name for matplotlib.
    If the font is bundled, ensure it's registered first.
    If not found, fall back to Inter, then system sans-serif.
    """
    register_fonts()
    available = {f.name for f in fm.fontManager.ttflist}
    if font_name in available:
        return font_name
    if "Inter" in available:
        return "Inter"
    return "sans-serif"
```

---

## Testing Strategy

### What to Test

For each chart type:
1. **Smoke test:** Call the function with minimal valid data, assert it returns a `Chart` object.
2. **Parameter validation:** Pass invalid data (missing columns, wrong types), assert appropriate errors.
3. **Output verification:** Call `chart.to_base64()`, assert it returns a non-empty string (confirms rendering works end-to-end).
4. **Figure properties:** Access `chart.fig`, assert figure size, title text, number of axes, etc.

### Sample Fixtures (`conftest.py`)

```python
import pandas as pd
import pytest

@pytest.fixture
def timeseries_df():
    """Simple time series DataFrame for line chart tests."""
    return pd.DataFrame({
        "date": pd.date_range("2020-01-01", periods=24, freq="MS"),
        "unemployment_rate": [3.5, 3.6, 14.7, 13.3, 11.1, 8.4,
                              7.9, 7.8, 7.7, 6.9, 6.7, 6.5,
                              6.3, 6.2, 6.0, 5.9, 5.8, 5.4,
                              5.2, 4.8, 4.6, 4.2, 3.9, 3.7],
    })

@pytest.fixture
def categorical_df():
    """Categorical DataFrame for bar chart tests."""
    return pd.DataFrame({
        "state": ["CA", "TX", "NY", "FL", "IL", "PA", "OH", "GA"],
        "median_income": [78672, 61874, 72108, 57703, 69187, 63627, 58116, 58700],
    })

@pytest.fixture
def scatter_df():
    """Two-variable DataFrame for scatter plot tests."""
    return pd.DataFrame({
        "gdp_per_capita": [65000, 45000, 12000, 35000, 55000, 8000, 42000, 28000],
        "life_expectancy": [78.5, 82.1, 71.2, 80.3, 81.0, 65.4, 83.2, 76.1],
        "country": ["USA", "Germany", "Brazil", "UK", "Australia", "India", "Japan", "Mexico"],
        "population": [331, 83, 212, 67, 26, 1380, 126, 129],
    })

@pytest.fixture
def slope_df():
    """Before/after DataFrame for slope chart tests."""
    return pd.DataFrame({
        "country": ["USA", "China", "Germany", "Japan", "UK"],
        "gdp_2020": [63000, 10500, 46000, 40000, 41000],
        "gdp_2024": [76000, 12500, 49000, 33000, 46000],
    })

@pytest.fixture
def waffle_data():
    """Proportional data for waffle chart tests."""
    return pd.DataFrame({
        "energy_source": ["Solar", "Wind", "Natural Gas", "Coal", "Nuclear", "Hydro"],
        "share": [15, 12, 38, 18, 10, 7],
    })
```

### Test Examples

```python
# test_line.py

def test_line_basic(timeseries_df):
    chart = vizop.line(
        data=timeseries_df,
        x="date",
        y="unemployment_rate",
        title="Test Chart",
    )
    assert isinstance(chart, Chart)
    assert chart.title == "Test Chart"

def test_line_returns_base64(timeseries_df):
    chart = vizop.line(
        data=timeseries_df,
        x="date",
        y="unemployment_rate",
        title="Test",
    )
    b64 = chart.to_base64()
    assert len(b64) > 0
    assert isinstance(b64, str)

def test_line_invalid_column(timeseries_df):
    with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
        vizop.line(
            data=timeseries_df,
            x="nonexistent",
            y="unemployment_rate",
            title="Test",
        )

def test_line_with_annotations(timeseries_df):
    chart = vizop.line(
        data=timeseries_df,
        x="date",
        y="unemployment_rate",
        title="Test",
        annotate={"2020-04-01": "Peak unemployment"},
    )
    assert isinstance(chart, Chart)

# test_config.py

def test_configure_accent_color():
    vizop.configure(accent_color="#00FF00")
    config = get_config()
    assert config.accent_color == "#00FF00"
    # Reset
    vizop.configure(accent_color="#E15759")

def test_configure_preset():
    vizop.configure(preset="fivethirtyeight")
    config = get_config()
    assert config.background == "light_gray"
    # Reset
    vizop.configure(preset=None)

# test_formatting.py

def test_auto_detect_percent():
    s = pd.Series([0.45, 0.32, 0.67])
    assert auto_detect_format("unemployment_rate", s) == "percent"

def test_format_dollar_millions():
    assert format_value(2_500_000, "dollar") == "$2.5M"

def test_format_dollar_thousands():
    assert format_value(65000, "dollar") == "$65K"
```

---

## Implementation Order

Build in this order to get to a working state fastest:

### Step 1: Scaffolding
1. Initialize project with `uv init`
2. Create full directory structure
3. Set up `pyproject.toml` with deps
4. Download and bundle fonts (Inter at minimum for step 1)
5. Implement `core/config.py` (VizopConfig, configure(), get_config())
6. Implement `core/chart.py` (Chart class)
7. Implement `core/fonts.py` (register_fonts, get_font_family)
8. Verify: `import vizop` works

### Step 2: Theme Engine
1. Implement `core/theme.py` (Typography, Layout, SizeSpec constants)
2. Implement `core/palettes.py` (palette definitions)
3. Implement `core/formatting.py` (auto_detect_format, format_value, format_tick)
4. Build the shared `apply_theme()` helper that configures any matplotlib figure
5. Verify: can create a blank themed figure with title/subtitle/source

### Step 3: Line Chart
1. Implement `charts/line.py` — start with single series
2. Add multi-series support (y as list, or group column)
3. Add highlight, highlight_range
4. Add show_last_value, show_area
5. Write tests

### Step 4: Bar Chart
1. Implement `charts/bar.py` — horizontal, sorted, with value labels
2. Add vertical orientation
3. Add grouped and stacked modes
4. Add reference_line, highlight
5. Write tests

### Step 5: Scatter Plot
1. Implement `charts/scatter.py` — basic scatter with single color
2. Add group coloring, size encoding
3. Add trend line (linear first, lowess optional)
4. Add label and annotation support
5. Write tests

### Step 6: Slope Chart
1. Implement `charts/slope.py` — basic slope with labels on both sides
2. Add smart label stacking for overlapping labels
3. Add show_change, color_by_direction
4. Add highlight, sort, limit
5. Write tests

### Step 7: Waffle Chart
1. Implement `charts/waffle.py` — square style first
2. Implement circle style
3. Build icon path data (`core/icons.py`)
4. Implement icon style
5. Add legend rendering
6. Write tests

### Step 8: Annotations
1. Implement `core/annotations.py` — basic placement
2. Integrate into all 5 chart types
3. Test with overlapping cases
4. Iterate on placement quality

### Step 9: Polish & Ship
1. Download and bundle all 4 fonts
2. Implement all 3 presets
3. Build `examples/gallery.py`
4. Write README with examples
5. Run full test suite
6. Publish to PyPI with `uv publish`

---

## Key Design Constraints (DO NOT VIOLATE)

1. **Every function returns a `Chart` object.** Never `plt.show()` directly. Never return a raw `Figure`.
2. **Always use pydantic models** for structured data. Never `@dataclass`. Never raw dicts for config.
3. **Always left-align titles.** Never centered. This is the #1 visual rule.
4. **Never show a legend box** for line charts. Use direct labels at line endpoints.
5. **Always sort bar charts by default.** Unsorted bars are almost always wrong.
6. **Horizontal gridlines only** (except scatter which gets both).
7. **No top or right spines.** Ever.
8. **Close all matplotlib figures** after wrapping in Chart to prevent memory leaks. Use `plt.close(fig)` after capturing the figure — but only if the user has called `show()`. Actually: keep the figure alive on the Chart object, let Python's GC handle it. Don't pre-close.
9. **Column validation:** Every chart function must validate that specified column names exist in the DataFrame before plotting. Raise `ValueError` with a clear message.
10. **Type hints everywhere.** Full type annotations on all public AND private functions.
11. **No print statements.** Use `warnings.warn()` for non-fatal issues (e.g., "font not found, falling back to Inter").

---

## Error Handling

- Missing column → `ValueError: "Column '{name}' not found in DataFrame. Available: {list}"`
- Too many groups → `ValueError: "bar() supports max 4 groups, got {n}. Consider filtering data."`
- Empty DataFrame → `ValueError: "DataFrame is empty. Cannot create chart."`
- Invalid orientation → `ValueError: "orientation must be 'horizontal' or 'vertical', got '{value}'"`
- Invalid sort → `ValueError: "sort must be 'ascending', 'descending', 'data', or None"`
- Invalid y_format → `ValueError: "y_format must be 'percent', 'dollar', 'comma', 'decimal', or None"`
- Unrecognized icon → `ValueError: "Unknown icon '{name}'. Available: person, circle, square, house, dollar, heart"`
- Both `data`+`category` and `values` provided to waffle → `ValueError: "Provide either data+category+value OR values dict, not both"`

All errors should be raised BEFORE any matplotlib figure is created to avoid resource leaks.

---

## Dependencies Summary

### Required
- `matplotlib>=3.8` — rendering engine
- `pydantic>=2.0` — data validation and config
- `numpy>=1.24` — numerical operations
- `pandas>=2.0` — DataFrame input

### Optional
- `statsmodels` — for LOWESS trend lines in scatter (catch ImportError, fall back to linear-only)
- `kaleido` — NOT needed for v0.1 (matplotlib handles static export natively)

### Dev
- `pytest>=7.0`
- `ruff>=0.4`
# vizop — Build Plan

Opinionated Python data visualization package. Publication-quality charts (storytelling-with-data meets NYT style) with minimal config. Matplotlib-only for v0.1.

**Tooling:** uv, ruff, pytest, pydantic (no dataclasses), matplotlib

**Python:** ≥3.10, modern syntax (`X | None`, `list[str]`)

---

## Steps

### Step 1: Project scaffold
Initialize with `uv init vizop --lib`. Create directory structure: `src/vizop/charts/`, `core/`, `assets/fonts/`, `tests/`, `examples/`. Set up `pyproject.toml` with deps (matplotlib, pydantic, numpy, pandas; dev: pytest, ruff). Drop font TTFs into `assets/fonts/` (Inter, Libre Franklin, Source Sans Pro, IBM Plex Sans — each needs Regular, SemiBold, Bold). Verify `uv run python -c "import vizop"` works.

### Step 2: Config + Chart object
`core/config.py` — `VizopConfig` pydantic model: accent_color, font, background (`"white"`/`"light_gray"`), size (`"standard"`/`"wide"`/`"tall"`), source_label. Module-level singleton with `configure(**kwargs)` and `get_config()`. `core/chart.py` — `Chart` class wrapping matplotlib `Figure` with `show()`, `save()`, `to_base64()`. `core/fonts.py` — register bundled fonts with matplotlib font manager on first use, fallback to Inter then sans-serif. Wire up `__init__.py` exports. Tests: config round-trips, Chart from dummy figure, font registration.

### Step 3: Theme engine + formatting
`core/theme.py` — `Typography`, `Layout`, `SizeSpec` pydantic models with hardcoded visual constants (title/subtitle/tick sizes+colors, gridline style, spine rules, line widths, bar width, point size). `core/palettes.py` — default/warm/cool/diverging/muted palettes + `HIGHLIGHT_MUTED_COLOR`. `core/formatting.py` — `auto_detect_format()` (column name keyword sniffing + value range detection), `format_value()`, `format_tick()`. Shared `apply_theme(fig, ax, config, title, subtitle, source, note)` helper: sets facecolor, removes top/right spines, adds horizontal gridlines, registers fonts, renders left-aligned title/subtitle, source line below plot, applies figure size. Tests: formatting with known inputs, apply_theme produces correct figure properties.

### Step 4: Line chart (single series)
`charts/line.py` — full function signature, implement: single y column, title/subtitle/source/note, accent_color, zero_baseline, show_area, show_last_value. Smart date formatting on x-axis (AutoDateLocator + ConciseDateFormatter). Uses apply_theme. Returns `Chart`. Tests: smoke, base64 output, invalid column ValueError, figure properties.

### Step 5: Line chart (multi-series + highlight)
Add to `line.py`: y as `list[str]`, group column. Direct labels at line endpoints (no legend box). Highlight — highlighted series get color, others get `#D3D3D3` at 1px. `highlight_range` with axvspan + label. Palette support. Tests for each feature.

### Step 6: Bar chart (basic)
`charts/bar.py` — horizontal (default), sorted descending, show_values with formatted labels at bar ends, accent_color, limit (top N after sort). No bar outlines. Uses apply_theme. Tests: smoke, sorting, value labels, invalid inputs.

### Step 7: Bar chart (grouped, stacked, extras)
Add to `bar.py`: vertical orientation, group column with side-by-side bars (max 4 groups → ValueError), stacked mode, reference_line (dashed + label), highlight, palette. Tests for each mode.

### Step 8: Scatter plot (basic)
`charts/scatter.py` — x/y columns, single color, opacity, both horizontal AND vertical gridlines (scatter exception), log scales, jitter (1% of axis range). Uses apply_theme. Tests.

### Step 9: Scatter plot (groups, trends, labels)
Add to `scatter.py`: group coloring (max 6, small legend below chart), size encoding from column, trend line (linear via np.polyfit; optional lowess via statsmodels with ImportError guard), label column for auto-labeling (<20 points), highlight. Tests.

### Step 10: Slope chart
`charts/slope.py` — each row = one line connecting left/right values. Labels on both sides, endpoint dots (6px circles), hidden y-axis. Smart label stacking (greedy vertical offset for close values). `show_change` with formatted delta (`+15%`, `-$2.3K`). `color_by_direction` (up=blue `#4E79A7`, down=red `#E15759`). sort, limit (default 15), highlight. Tests.

### Step 11: Waffle chart (square + circle)
`charts/waffle.py` — accept DataFrame OR values dict (validate exactly one). Normalize to `grid_size²` via largest remainder method. Square style (FancyBboxPatch with slight rounding, 2px gap), circle style. Fill left-to-right top-to-bottom grouped by category. Horizontal legend below chart. Max 7 categories (merge smallest → "Other"). Highlight (full color vs alpha=0.3). Tests.

### Step 12: Waffle icons
`core/icons.py` — matplotlib `Path` objects for: person, circle, square, house, dollar, heart (~20-30 vertices each). Add `style="icon"` to waffle.py with `icon` param. ValueError for unrecognized icon names. Tests.

### Step 13: Annotation engine
`core/annotations.py` — `AnnotationSpec` and `PlacedAnnotation` pydantic models. Placement: default offset from data point → check bounding box overlap against other annotations + data points → try alternate positions (above/below/left/right) → pick least overlap. Leader lines (subtle, no arrowhead). `place_annotations()` and `render_annotations()`. Standalone tests with mock axes.

### Step 14: Wire annotations into all charts
Integrate annotation engine into all 5 chart types via their `annotate` param. Test overlapping cases on each chart type. Visual verification with example scripts.

### Step 15: Gallery + polish
`examples/gallery.py` — one script generating all 5 chart types with realistic data. Run ruff format + lint. Full test suite green. Fix visual issues. README with install + code examples.

---

## Key Rules

- Every function returns a `Chart` object — never `plt.show()` directly
- All models are pydantic — no dataclasses, no raw dicts for config
- Titles always left-aligned, never centered
- Line charts use direct endpoint labels, never legend boxes
- Bar charts sorted by default
- Horizontal gridlines only (scatter gets both)
- No top or right spines ever
- Validate column names before creating any figure
- Type hints on all functions (public and private)
- No print statements — use `warnings.warn()` for non-fatal issues
- Raise errors before figure creation to avoid resource leaks

## Error Messages

- Missing column: `"Column '{name}' not found in DataFrame. Available: {list}"`
- Too many groups: `"bar() supports max 4 groups, got {n}"`
- Empty DataFrame: `"DataFrame is empty. Cannot create chart."`
- Invalid orientation/sort/format: clear message with valid options
- Unrecognized icon: `"Unknown icon '{name}'. Available: person, circle, square, house, dollar, heart"`
- Waffle input conflict: `"Provide either data+category+value OR values dict, not both"`
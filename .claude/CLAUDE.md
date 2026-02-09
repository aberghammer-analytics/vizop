# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

vizop is an opinionated Python data visualization package that produces publication-quality charts (NYT, FiveThirtyEight style) with minimal configuration. v0.1 is matplotlib-only. See `.claude/SPEC.md` for the full implementation specification.

## Development Commands

Package manager: **uv**

```bash
uv sync                    # Install dependencies
uv run pytest              # Run all tests
uv run pytest tests/test_line.py       # Run single test file
uv run pytest tests/test_line.py::test_line_basic  # Run single test
uv run ruff check src/     # Lint
uv run ruff format src/    # Format
uv run ruff check --fix src/  # Auto-fix lint issues
```

## Architecture

Source layout: `src/vizop/` (src-layout with hatchling build backend).

```
src/vizop/
├── __init__.py          # Public API: line, bar, scatter, slope, waffle, configure
├── charts/              # One module per chart type, each exports a single function
│   ├── line.py          # vizop.line()
│   ├── bar.py           # vizop.bar()
│   ├── scatter.py       # vizop.scatter()
│   ├── slope.py         # vizop.slope()
│   └── waffle.py        # vizop.waffle()
├── core/                # Shared infrastructure
│   ├── chart.py         # Chart wrapper (returned by all chart functions)
│   ├── config.py        # VizopConfig singleton + configure() + presets
│   ├── theme.py         # Typography, Layout, SizeSpec constants (not user-facing)
│   ├── annotations.py   # Annotation placement + rendering with collision avoidance
│   ├── formatting.py    # Number auto-detection and formatting (percent, dollar, comma)
│   ├── palettes.py      # Color palette definitions + highlight muted color
│   ├── fonts.py         # Bundled font registration with matplotlib
│   └── icons.py         # SVG path data for waffle chart icons
├── assets/fonts/        # Bundled OFL-licensed fonts (Inter, LibreFranklin, SourceSansPro, IBMPlexSans)
└── py.typed             # PEP 561 marker
```

### Data flow

Every chart function follows: validate inputs → prepare data → get config/theme → create matplotlib figure → apply theme → render chart elements → add title/subtitle/source → render annotations → return `Chart` object.

The shared `apply_theme()` helper configures spines, gridlines, background, fonts, title, subtitle, and source label on any matplotlib figure.

## Critical Design Rules

These are non-negotiable constraints. Violating them breaks the package's design intent:

1. **Every chart function returns a `Chart` object** — never call `plt.show()` directly, never return a raw `Figure`
2. **All data models use Pydantic** — no `@dataclass` anywhere, no raw dicts for config
3. **Titles are LEFT-ALIGNED** to the plot edge — never centered
4. **No legend boxes on line charts** — use direct labels at line endpoints
5. **Bar charts sort by default** (descending) — unsorted bars require explicit `sort=None`
6. **Horizontal gridlines only** — scatter is the sole exception (gets both)
7. **No top or right spines** — ever
8. **Column validation before plotting** — raise `ValueError` with available columns before creating any matplotlib figure
9. **No print statements** — use `warnings.warn()` for non-fatal issues
10. **Full type hints** on all public and private functions; use modern syntax (`X | None`, `list[str]`)

## Python Version

Target: Python 3.10+. Use modern union syntax (`X | None` not `Optional[X]`, `list[str]` not `List[str]`).

## Tooling Config

- **Ruff**: line-length 100, double quotes, rules: E, F, I, N, UP, B, SIM, TCH
- **pytest**: testpaths=`tests`, pythonpath=`src`
- **Build backend**: hatchling

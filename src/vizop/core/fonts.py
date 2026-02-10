"""Bundled font registration with matplotlib."""

import warnings
from pathlib import Path

from matplotlib import font_manager

from vizop.core.config import VizopConfig

_fonts_registered: bool = False

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

_BUNDLED_FONTS: dict[str, str] = {
    "Inter": "Inter",
    "Libre Franklin": "LibreFranklin",
    "Source Sans Pro": "SourceSansPro",
    "IBM Plex Sans": "IBMPlexSans",
}


def register_fonts() -> None:
    """Register all bundled TTF fonts with matplotlib's font manager.

    Idempotent — repeated calls are no-ops.
    """
    global _fonts_registered
    if _fonts_registered:
        return

    for folder_name in _BUNDLED_FONTS.values():
        font_dir = _ASSETS_DIR / folder_name
        if not font_dir.is_dir():
            continue
        for ttf_path in font_dir.glob("*.ttf"):
            font_manager.fontManager.addfont(str(ttf_path))

    _fonts_registered = True


def get_font_family(config: VizopConfig) -> str:
    """Return a validated font family name for the given config.

    Falls back to Inter if the requested font isn't available, then to sans-serif.
    """
    register_fonts()

    available = {f.name for f in font_manager.fontManager.ttflist}

    if config.font in available:
        return config.font

    warnings.warn(
        f"Font '{config.font}' not found. Falling back to Inter.",
        stacklevel=2,
    )

    if "Inter" in available:
        return "Inter"

    return "sans-serif"

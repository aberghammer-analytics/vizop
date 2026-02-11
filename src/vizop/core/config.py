"""Global configuration singleton for vizop."""

from typing import Literal

from pydantic import BaseModel


class VizopConfig(BaseModel):
    """Configuration for vizop chart defaults."""

    accent_color: str = "#4E79A7"
    font: str = "Inter"
    background: Literal["white", "light_gray"] = "white"
    size: Literal["standard", "wide", "tall"] = "standard"
    source_label: str | None = None
    gridlines: bool = False


_config: VizopConfig | None = None


def get_config() -> VizopConfig:
    """Return the current global config, creating defaults if needed."""
    global _config
    if _config is None:
        _config = VizopConfig()
    return _config


def configure(**kwargs: object) -> None:
    """Update global config with the provided values."""
    global _config
    current = get_config()
    _config = VizopConfig.model_validate(current.model_dump() | kwargs)


def reset_config() -> None:
    """Reset global config to defaults."""
    global _config
    _config = None

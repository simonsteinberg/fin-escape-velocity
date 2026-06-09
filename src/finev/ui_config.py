"""Load and validate UI configuration (layout width and color scheme).

`ui_config.json` is the authoritative source for the presentation-only UI
settings the page reads at build time. Like :mod:`finev.config`, this module is
pure: it parses and validates the JSON into a frozen typed dataclass and carries
no NiceGUI dependency, so it stays unit-testable without rendering a page. The
NiceGUI layer (:mod:`finev.ui`) maps the parsed values onto widgets/CSS.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

UI_CONFIG_PATH = Path(__file__).with_name("ui_config.json")


class ColorScheme(StrEnum):
    """Supported UI color schemes.

    ``AUTO`` defers to the operating system / browser preference (the CSS
    ``prefers-color-scheme`` media query); ``LIGHT`` and ``DARK`` force a fixed
    scheme regardless of the OS setting.
    """

    AUTO = "auto"
    LIGHT = "light"
    DARK = "dark"


#: Order the navbar toggle cycles through (wraps back to the start).
_SCHEME_CYCLE: tuple[ColorScheme, ...] = (
    ColorScheme.AUTO,
    ColorScheme.LIGHT,
    ColorScheme.DARK,
)

#: Material icon name shown for each scheme on the navbar toggle.
_SCHEME_ICONS: dict[ColorScheme, str] = {
    ColorScheme.AUTO: "brightness_auto",
    ColorScheme.LIGHT: "light_mode",
    ColorScheme.DARK: "dark_mode",
}


def scheme_to_dark_mode(scheme: ColorScheme) -> bool | None:
    """Map a color scheme to NiceGUI's ``ui.dark_mode`` value.

    Args:
        scheme: The active color scheme.

    Returns:
        ``True`` for dark, ``False`` for light, and ``None`` for auto — the value
        NiceGUI interprets as "follow the OS/browser preference".
    """
    if scheme is ColorScheme.DARK:
        return True
    if scheme is ColorScheme.LIGHT:
        return False
    return None


def next_color_scheme(scheme: ColorScheme) -> ColorScheme:
    """Return the next scheme in the navbar toggle cycle.

    Cycles ``auto → light → dark → auto``; an unrecognised scheme restarts the
    cycle at its first entry.

    Args:
        scheme: The current color scheme.

    Returns:
        The scheme to switch to on the next toggle.
    """
    try:
        index = _SCHEME_CYCLE.index(scheme)
    except ValueError:
        return _SCHEME_CYCLE[0]
    return _SCHEME_CYCLE[(index + 1) % len(_SCHEME_CYCLE)]


def color_scheme_icon(scheme: ColorScheme) -> str:
    """Return the Material icon name representing a color scheme.

    Args:
        scheme: The color scheme to depict.

    Returns:
        A Material icon name (e.g. ``"dark_mode"``).
    """
    return _SCHEME_ICONS[scheme]


@dataclass(frozen=True)
class UiConfig:
    """Typed UI configuration values.

    Attributes:
        max_width_px: Maximum content width in pixels. ``0`` means no constraint
            (the layout fills the full browser width, the historical behaviour).
        color_scheme: Active color scheme. ``AUTO`` follows the OS/browser
            ``prefers-color-scheme`` preference.
    """

    max_width_px: int
    color_scheme: ColorScheme

    @property
    def dark_mode_value(self) -> bool | None:
        """Map the color scheme to NiceGUI's ``ui.dark_mode`` value.

        Returns:
            ``True`` for dark, ``False`` for light, and ``None`` for auto — the
            value NiceGUI interprets as "follow the OS/browser preference".
        """
        return scheme_to_dark_mode(self.color_scheme)

    @property
    def content_max_width_style(self) -> str:
        """Return the CSS ``max-width`` declaration for the page content.

        Returns:
            A declaration such as ``"max-width: 1600px"``, or an empty string
            when :attr:`max_width_px` is ``0`` (full width — no constraint).
        """
        if self.max_width_px <= 0:
            return ""
        return f"max-width: {self.max_width_px}px"


def load_ui_config(path: Path | None = None) -> UiConfig:
    """Load and validate UI configuration from a JSON file.

    Args:
        path: Optional path to the JSON file; defaults to the packaged
            ``ui_config.json``.

    Returns:
        The parsed, validated configuration.

    Raises:
        KeyError: A required key is missing.
        ValueError: The file is not a JSON object or a value is invalid.
    """
    config_path = path or UI_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError("UI config file must contain a JSON object.")
    config = _parse_ui_config(raw)
    _validate_ui_config(config)
    return config


@lru_cache(maxsize=1)
def get_ui_config() -> UiConfig:
    """Return the cached UI configuration."""
    return load_ui_config()


def _parse_ui_config(raw: dict[str, Any]) -> UiConfig:
    if "MAX_WIDTH_PX" not in raw:
        raise KeyError("UI config missing required key: MAX_WIDTH_PX")
    max_width = raw["MAX_WIDTH_PX"]
    # bool is an int subclass; reject it so ``true``/``false`` is not a width.
    if not isinstance(max_width, int) or isinstance(max_width, bool):
        raise ValueError("MAX_WIDTH_PX must be an integer.")
    if "COLOR_SCHEME" not in raw:
        raise KeyError("UI config missing required key: COLOR_SCHEME")
    scheme_raw = raw["COLOR_SCHEME"]
    if not isinstance(scheme_raw, str):
        raise ValueError("COLOR_SCHEME must be a string.")
    try:
        color_scheme = ColorScheme(scheme_raw.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(scheme.value for scheme in ColorScheme)
        raise ValueError(f"COLOR_SCHEME must be one of: {allowed}.") from exc
    return UiConfig(max_width_px=max_width, color_scheme=color_scheme)


def _validate_ui_config(config: UiConfig) -> None:
    if config.max_width_px < 0:
        raise ValueError("MAX_WIDTH_PX must be non-negative.")

"""Unit tests for the pure UI configuration loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finev.ui_config import (
    ColorScheme,
    UiConfig,
    color_scheme_icon,
    get_ui_config,
    load_ui_config,
    next_color_scheme,
    scheme_to_dark_mode,
)


def _write_config(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "ui_config.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_packaged_config_loads() -> None:
    config = get_ui_config()
    assert config.max_width_px == 1600
    assert config.color_scheme is ColorScheme.AUTO


def test_load_valid_config(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path, {"MAX_WIDTH_PX": 1200, "COLOR_SCHEME": "dark"}
    )
    config = load_ui_config(path)
    assert config.max_width_px == 1200
    assert config.color_scheme is ColorScheme.DARK


def test_color_scheme_is_case_insensitive(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path, {"MAX_WIDTH_PX": 1000, "COLOR_SCHEME": "  LIGHT  "}
    )
    assert load_ui_config(path).color_scheme is ColorScheme.LIGHT


@pytest.mark.parametrize(
    ("scheme", "expected"),
    [
        (ColorScheme.DARK, True),
        (ColorScheme.LIGHT, False),
        (ColorScheme.AUTO, None),
    ],
)
def test_dark_mode_value(scheme: ColorScheme, expected: bool | None) -> None:
    config = UiConfig(max_width_px=1600, color_scheme=scheme)
    assert config.dark_mode_value is expected


def test_content_max_width_style_when_set() -> None:
    config = UiConfig(max_width_px=1600, color_scheme=ColorScheme.AUTO)
    assert config.content_max_width_style == "max-width: 1600px"


def test_content_max_width_style_when_zero_is_full_width() -> None:
    config = UiConfig(max_width_px=0, color_scheme=ColorScheme.AUTO)
    assert config.content_max_width_style == ""


def test_missing_max_width_raises(tmp_path: Path) -> None:
    path = _write_config(tmp_path, {"COLOR_SCHEME": "auto"})
    with pytest.raises(KeyError, match="MAX_WIDTH_PX"):
        load_ui_config(path)


def test_missing_color_scheme_raises(tmp_path: Path) -> None:
    path = _write_config(tmp_path, {"MAX_WIDTH_PX": 1600})
    with pytest.raises(KeyError, match="COLOR_SCHEME"):
        load_ui_config(path)


def test_non_integer_max_width_raises(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path, {"MAX_WIDTH_PX": "wide", "COLOR_SCHEME": "auto"}
    )
    with pytest.raises(ValueError, match="MAX_WIDTH_PX"):
        load_ui_config(path)


def test_boolean_max_width_raises(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path, {"MAX_WIDTH_PX": True, "COLOR_SCHEME": "auto"}
    )
    with pytest.raises(ValueError, match="MAX_WIDTH_PX"):
        load_ui_config(path)


def test_negative_max_width_raises(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path, {"MAX_WIDTH_PX": -10, "COLOR_SCHEME": "auto"}
    )
    with pytest.raises(ValueError, match="MAX_WIDTH_PX"):
        load_ui_config(path)


def test_unknown_color_scheme_raises(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path, {"MAX_WIDTH_PX": 1600, "COLOR_SCHEME": "sepia"}
    )
    with pytest.raises(ValueError, match="COLOR_SCHEME"):
        load_ui_config(path)


def test_non_object_config_raises(tmp_path: Path) -> None:
    path = _write_config(tmp_path, [1, 2, 3])
    with pytest.raises(ValueError, match="JSON object"):
        load_ui_config(path)


@pytest.mark.parametrize(
    ("scheme", "expected"),
    [
        (ColorScheme.DARK, True),
        (ColorScheme.LIGHT, False),
        (ColorScheme.AUTO, None),
    ],
)
def test_scheme_to_dark_mode(
    scheme: ColorScheme, expected: bool | None
) -> None:
    assert scheme_to_dark_mode(scheme) is expected


def test_next_color_scheme_cycles() -> None:
    # auto → light → dark → auto
    assert next_color_scheme(ColorScheme.AUTO) is ColorScheme.LIGHT
    assert next_color_scheme(ColorScheme.LIGHT) is ColorScheme.DARK
    assert next_color_scheme(ColorScheme.DARK) is ColorScheme.AUTO


def test_next_color_scheme_round_trips_every_scheme() -> None:
    scheme = ColorScheme.AUTO
    seen = []
    for _ in range(len(ColorScheme)):
        scheme = next_color_scheme(scheme)
        seen.append(scheme)
    assert set(seen) == set(ColorScheme)
    assert scheme is ColorScheme.AUTO


def test_color_scheme_icon_is_distinct_per_scheme() -> None:
    icons = {color_scheme_icon(scheme) for scheme in ColorScheme}
    assert len(icons) == len(ColorScheme)
    assert color_scheme_icon(ColorScheme.DARK) == "dark_mode"
    assert color_scheme_icon(ColorScheme.LIGHT) == "light_mode"

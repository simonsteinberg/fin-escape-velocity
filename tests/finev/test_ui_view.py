"""Unit tests for the pure UI presentation helpers."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from finev.models import Asset, AssetType
from finev.ui_view import (
    DARK_PAGE_BG,
    DARK_SCROLLBAR_THUMB,
    DARK_SURFACE_BG,
    NAVBAR_CLASS,
    NAVBAR_DARK_BG,
    NAVBAR_LIGHT_BG,
    asset_value_columns,
    chart_series,
    export_csv_filename,
    favicon_svg,
    forecast_csv,
    forecast_table_columns,
    inline_logo_svg,
    theme_css,
)


def test_theme_css_drives_scheme_from_quasar_dark_class() -> None:
    css = theme_css()
    # Navbar follows the scheme: brand teal in light, gray in dark.
    assert f".{NAVBAR_CLASS} {{ background-color: {NAVBAR_LIGHT_BG}; }}" in css
    assert (
        f".body--dark .{NAVBAR_CLASS} {{ background-color: {NAVBAR_DARK_BG}; }}"
        in css
    )
    # Dark palette overrides Quasar's near-black page default with a gray.
    assert f"--q-dark-page: {DARK_PAGE_BG}" in css
    # Cards and the data table sit on the lighter surface gray, not near-black.
    assert f"--q-dark: {DARK_SURFACE_BG}" in css
    assert ".q-card" in css
    assert ".q-table" in css
    assert f"background-color: {DARK_SURFACE_BG}" in css
    # Dark scrollbars (WebKit thumb + Firefox shorthand) are themed, not white.
    assert DARK_SCROLLBAR_THUMB in css
    assert "::-webkit-scrollbar-thumb" in css
    assert "scrollbar-color:" in css


def test_favicon_svg_returns_inline_svg() -> None:
    svg = favicon_svg()
    # NiceGUI only treats a string starting with "<svg" as an inline favicon.
    assert svg.lstrip().startswith("<svg")
    assert "</svg>" in svg


def test_inline_logo_svg_scales_root_dimensions_to_container() -> None:
    svg = inline_logo_svg()
    # The fixed 128px root dimensions are replaced so the icon fills its box.
    assert 'width="128"' not in svg
    assert 'height="128"' not in svg
    assert 'width="100%"' in svg
    assert 'height="100%"' in svg
    # Inner drawing attributes (e.g. stroke-width) must be left untouched.
    assert "stroke-width=" in svg
    assert svg.lstrip().startswith("<svg")


def test_asset_value_columns_excludes_inheritance_and_appends_total() -> None:
    assets = [
        Asset("ETF", AssetType.ETF, 100.0),
        Asset("Cash", AssetType.CASH, 50.0),
        Asset(
            "Erbe",
            AssetType.INHERITANCE,
            0.0,
            inheritance_gross_amount=1000.0,
        ),
    ]
    assert asset_value_columns(assets) == ["ETF", "Cash", "total"]


def test_forecast_table_columns_has_fixed_then_value_columns() -> None:
    columns = forecast_table_columns(["ETF", "total"])
    names = [column["name"] for column in columns]
    assert names == [
        "year_index",
        "age",
        "net_cashflow",
        "taxes",
        "ETF",
        "total",
    ]
    # The age column is intentionally not sortable; everything else is.
    age_column = next(c for c in columns if c["name"] == "age")
    assert age_column["sortable"] is False
    assert all(c["sortable"] is True for c in columns if c["name"] != "age")


def test_forecast_table_columns_translates_fixed_labels() -> None:
    from finev.i18n import make_translator

    columns = forecast_table_columns(["ETF", "total"], make_translator("de"))
    labels = {c["name"]: c["label"] for c in columns}
    # Fixed columns are localized; per-asset value columns keep their names.
    assert labels["year_index"] == "Jahr"
    assert labels["net_cashflow"] == "Netto-Cashflow mtl."
    assert labels["ETF"] == "ETF"
    assert labels["total"] == "total"


def test_forecast_csv_keeps_all_columns_and_rows_without_index() -> None:
    frame = pd.DataFrame(
        {
            "month_index": [0, 1],
            "age_years": [40, 40],
            "net_cashflow": [0.0, 100.0],
            "ETF": [1000.0, 1100.0],
            "total": [1000.0, 1100.0],
        }
    )

    csv = forecast_csv(frame)

    lines = csv.strip().splitlines()
    # Header carries every backend column; the pandas index is not exported.
    assert lines[0] == "month_index,age_years,net_cashflow,ETF,total"
    # One row per month is preserved (header + two data rows).
    assert len(lines) == 3
    assert lines[1] == "0,40,0,1000,1000"


def test_forecast_csv_rounds_euro_columns_to_integers() -> None:
    frame = pd.DataFrame(
        {
            "month_index": [0, 1],
            "age_years": [40, 40],
            "net_cashflow": [12.4, -50.6],
            "ETF": [1000.5, 1100.49],
            "total": [1000.5, 1049.89],
        }
    )

    lines = forecast_csv(frame).strip().splitlines()

    # EURO floats are rounded to whole euros and rendered without a decimal
    # point; integer age/index columns are untouched. (0.5 rounds to even.)
    assert lines[1] == "0,40,12,1000,1000"
    assert lines[2] == "1,40,-51,1100,1050"


def test_export_csv_filename_is_timestamped() -> None:
    moment = datetime(2026, 6, 6, 15, 30, 0)
    assert export_csv_filename(moment) == "wealth-forecast-20260606-153000.csv"


def test_export_csv_filename_defaults_to_now() -> None:
    name = export_csv_filename()
    assert name.startswith("wealth-forecast-")
    assert name.endswith(".csv")


def test_chart_series_builds_one_smooth_line_per_column() -> None:
    frame = pd.DataFrame(
        {
            "ETF": [1.0, 2.0, 3.0],
            "total": [1.0, 2.0, 3.0],
            "ignored": [9.0, 9.0, 9.0],
        }
    )
    series = chart_series(frame, ["ETF", "total"])
    assert [s["name"] for s in series] == ["ETF", "total"]
    assert series[0]["data"] == [1.0, 2.0, 3.0]
    assert all(s["type"] == "line" and s["smooth"] for s in series)

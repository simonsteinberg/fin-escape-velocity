"""Unit tests for the pure UI presentation helpers."""

from __future__ import annotations

import pandas as pd

from finev.models import Asset, AssetType
from finev.ui_view import (
    asset_value_columns,
    chart_series,
    favicon_svg,
    forecast_table_columns,
)


def test_favicon_svg_returns_inline_svg() -> None:
    svg = favicon_svg()
    # NiceGUI only treats a string starting with "<svg" as an inline favicon.
    assert svg.lstrip().startswith("<svg")
    assert "</svg>" in svg


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

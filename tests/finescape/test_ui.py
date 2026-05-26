import pandas as pd
import pytest

from finev.models import AssetType, DEFAULT_ANNUAL_GAIN_RATES
from finev.ui import (
    _build_chart_options,
    _default_asset_rows,
    _format_currency,
    _yearly_display_frame,
)


def test_yearly_display_frame_samples_every_12_months() -> None:
    data = pd.DataFrame(
        {
            "month_index": list(range(0, 25)),
            "age_years": [40] * 25,
            "age_months": list(range(0, 25)),
            "total": [float(value) for value in range(25)],
        }
    )

    result = _yearly_display_frame(data)

    assert result["month_index"].tolist() == [0, 12, 24]
    assert result["year_index"].tolist() == [0, 1, 2]
    assert result.index.tolist() == [0, 1, 2]


def test_yearly_display_frame_handles_empty() -> None:
    result = _yearly_display_frame(pd.DataFrame())

    assert result.empty


def test_format_currency_rounds_and_appends_suffix() -> None:
    assert _format_currency(1234.6, "EUR") == "1,235 EUR"
    assert _format_currency(1000.0, "") == "1,000"


def test_default_asset_rows_match_expected_defaults() -> None:
    rows = _default_asset_rows()

    assert [row["name"] for row in rows] == [
        "ETF MSCI World",
        "bAV",
        "Daily account",
    ]
    assert [row["type"] for row in rows] == [
        AssetType.ETF.value,
        AssetType.BAV.value,
        AssetType.CASH.value,
    ]
    assert rows[0]["annual_gain_rate_pct"] == pytest.approx(
        DEFAULT_ANNUAL_GAIN_RATES[AssetType.ETF] * 100
    )
    assert rows[1]["annual_gain_rate_pct"] == pytest.approx(
        DEFAULT_ANNUAL_GAIN_RATES[AssetType.BAV] * 100
    )
    assert rows[2]["annual_gain_rate_pct"] == pytest.approx(
        DEFAULT_ANNUAL_GAIN_RATES[AssetType.CASH] * 100
    )


def test_build_chart_options_has_expected_shape() -> None:
    options = _build_chart_options()

    assert options["tooltip"]["trigger"] == "axis"
    assert options["legend"]["top"] == 0
    assert options["xAxis"]["type"] == "category"
    assert options["xAxis"]["data"] == []
    assert options["yAxis"]["type"] == "value"
    assert options["series"] == []

import pandas as pd
import pytest

from finev.models import DEFAULT_ANNUAL_GAIN_RATES, AssetType, BAVStrategy
from finev.ui import (
    _asset_from_row,
    _build_chart_options,
    _default_asset_rows,
    _default_withdrawal_state,
    _format_currency,
    _load_cached_state,
    _normalize_asset_row,
    _save_cached_state,
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
    assert rows[0]["unrealized_gains"] == pytest.approx(0.0)
    assert rows[1]["unrealized_gains"] == pytest.approx(0.0)
    assert rows[2]["unrealized_gains"] == pytest.approx(0.0)
    assert rows[1]["bav_strategy"] == BAVStrategy.TRANSFER.value
    assert rows[1]["bav_transfer_start_age"] == 67
    assert rows[1]["bav_transfer_end_age"] == 72
    assert rows[1]["bav_transfer_etf_ratio_pct"] == pytest.approx(50.0)


def test_build_chart_options_has_expected_shape() -> None:
    options = _build_chart_options()

    assert options["tooltip"]["trigger"] == "axis"
    assert options["legend"]["top"] == 0
    assert options["xAxis"]["type"] == "category"
    assert options["xAxis"]["data"] == []
    assert options["yAxis"]["type"] == "value"
    assert options["series"] == []


def test_default_withdrawal_state_includes_state_pension_inputs() -> None:
    state = _default_withdrawal_state()

    assert state["monthly_withdrawal"] == pytest.approx(3000.0)
    assert state["state_pension_current_monthly_amount"] == pytest.approx(0.0)
    assert state["state_pension_growth_per_working_year"] == pytest.approx(0.0)
    assert state["state_pension_start_age"] == 67


def test_asset_from_row_maps_unrealized_gains_to_cost_basis() -> None:
    asset = _asset_from_row(
        {
            "name": "ETF",
            "type": AssetType.ETF.value,
            "current_value": 400_000.0,
            "unrealized_gains": 100_000.0,
            "annual_gain_rate_pct": 5.0,
            "monthly_contribution": 0.0,
        }
    )

    assert asset.initial_cost_basis == pytest.approx(300_000.0)
    assert asset.bav_strategy == BAVStrategy.TRANSFER


def test_asset_from_row_maps_unrealized_gains_for_non_etf() -> None:
    asset = _asset_from_row(
        {
            "name": "Cash",
            "type": AssetType.CASH.value,
            "current_value": 10_000.0,
            "unrealized_gains": 2_000.0,
            "annual_gain_rate_pct": 0.5,
            "monthly_contribution": 0.0,
        }
    )

    assert asset.initial_cost_basis == pytest.approx(8_000.0)


def test_asset_from_row_maps_bav_ratio_pct() -> None:
    asset = _asset_from_row(
        {
            "name": "bAV",
            "type": AssetType.BAV.value,
            "current_value": 100_000.0,
            "unrealized_gains": 20_000.0,
            "annual_gain_rate_pct": 2.0,
            "monthly_contribution": 0.0,
            "bav_strategy": BAVStrategy.INCOME.value,
            "bav_transfer_start_age": 68,
            "bav_transfer_end_age": 70,
            "bav_transfer_etf_ratio_pct": 75.0,
        }
    )

    assert asset.bav_strategy == BAVStrategy.INCOME
    assert asset.bav_transfer_etf_ratio == pytest.approx(0.75)


def test_normalize_asset_row_clamps_unrealized_gains() -> None:
    normalized = _normalize_asset_row(
        {
            "name": "Cash",
            "type": AssetType.CASH.value,
            "current_value": 100.0,
            "unrealized_gains": 200.0,
            "annual_gain_rate_pct": 0.5,
            "monthly_contribution": 0.0,
            "bav_transfer_etf_ratio_pct": 140.0,
        }
    )

    assert normalized["unrealized_gains"] == pytest.approx(100.0)
    assert normalized["bav_transfer_etf_ratio_pct"] == pytest.approx(100.0)


def test_cached_state_roundtrip(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_path = tmp_path / "state.json"
    monkeypatch.setenv("WEALTH_APP_STATE_PATH", str(cache_path))
    state = {
        "assets": _default_asset_rows(),
        "profile": {"current_age_years": 42},
        "withdrawal": {"monthly_withdrawal": 2500.0},
    }

    _save_cached_state(state)
    loaded = _load_cached_state()

    assert loaded == state


def test_load_cached_state_missing_returns_none(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_path = tmp_path / "missing.json"
    monkeypatch.setenv("WEALTH_APP_STATE_PATH", str(cache_path))

    assert _load_cached_state() is None

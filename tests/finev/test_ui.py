import pandas as pd
import pytest

from finev.forecast import forecast_wealth
from finev.models import (
    DEFAULT_ANNUAL_GAIN_RATES,
    Asset,
    AssetType,
    BAVStrategy,
    InvestmentKind,
    UserProfile,
)
from finev.ui_state import (
    asset_from_row as _asset_from_row,
)
from finev.ui_state import (
    default_asset_rows as _default_asset_rows,
)
from finev.ui_state import (
    default_profile_state as _default_profile_state,
)
from finev.ui_state import (
    default_withdrawal_state as _default_withdrawal_state,
)
from finev.ui_state import (
    load_cached_state as _load_cached_state,
)
from finev.ui_state import (
    new_asset_row as _new_asset_row,
)
from finev.ui_state import (
    normalize_asset_row as _normalize_asset_row,
)
from finev.ui_state import (
    save_cached_state as _save_cached_state,
)
from finev.ui_view import (
    asset_value_columns as _asset_value_columns,
)
from finev.ui_view import (
    build_chart_options as _build_chart_options,
)
from finev.ui_view import (
    format_currency as _format_currency,
)
from finev.ui_view import (
    yearly_display_frame as _yearly_display_frame,
)


def _monthly_frame(
    start_age_years: int, start_age_months: int, months: int
) -> pd.DataFrame:
    """Build a synthetic monthly frame starting at the given age."""
    start = start_age_years * 12 + start_age_months
    ages = [start + offset for offset in range(months)]
    return pd.DataFrame(
        {
            "month_index": list(range(months)),
            "age_years": [age // 12 for age in ages],
            "age_months": [age % 12 for age in ages],
            "total": [float(value) for value in range(months)],
        }
    )


def test_yearly_display_frame_samples_every_12_months() -> None:
    data = _monthly_frame(40, 0, months=25)

    result = _yearly_display_frame(data)

    assert result["month_index"].tolist() == [0, 12, 24]
    assert result["age_years"].tolist() == [40, 41, 42]
    assert result["year_index"].tolist() == [0, 1, 2]
    assert result.index.tolist() == [0, 1, 2]


def test_yearly_display_frame_samples_on_birthdays_from_mid_year() -> None:
    data = _monthly_frame(40, 1, months=25)

    result = _yearly_display_frame(data)

    # Start row plus each birthday; the age-41 row is 11 months in, not 12.
    assert result["month_index"].tolist() == [0, 11, 23]
    assert result["age_years"].tolist() == [40, 41, 42]
    assert result["age_months"].tolist() == [1, 0, 0]
    assert result["year_index"].tolist() == [0, 1, 2]


def test_yearly_display_frame_start_month_shortens_first_year() -> None:
    """A later start month means fewer contributions before the next birthday."""
    etf = Asset(
        name="ETF",
        asset_type=AssetType.ETF,
        current_value=10_000.0,
        monthly_contribution=1_000.0,
        annual_gain_rate=0.05,
    )

    def total_at_age_26(start_age_months: int) -> float:
        profile = UserProfile(
            current_age_years=25,
            current_age_months=start_age_months,
            retirement_age=30,
            end_age=30,
        )
        display = _yearly_display_frame(
            forecast_wealth(profile=profile, assets=[etf])
        )
        row = display[display["age_years"] == 26].iloc[0]
        assert int(row["age_months"]) == 0
        return float(row["total"])

    from_birthday = total_at_age_26(0)
    from_one_month_later = total_at_age_26(1)

    # 11 monthly contributions instead of 12, so roughly one rate less.
    assert from_one_month_later < from_birthday
    assert from_birthday - from_one_month_later == pytest.approx(
        1_000, abs=150
    )


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
        "Notgroschen",
        "Inheritance",
        "Car",
    ]
    assert [row["type"] for row in rows] == [
        AssetType.ETF.value,
        AssetType.CASH.value,
        AssetType.INHERITANCE.value,
        AssetType.INVESTMENT.value,
    ]
    assert rows[0]["current_value"] == pytest.approx(100_000.0)
    assert rows[0]["monthly_contribution"] == pytest.approx(500.0)
    assert rows[0]["annual_gain_rate_pct"] == pytest.approx(
        DEFAULT_ANNUAL_GAIN_RATES[AssetType.ETF] * 100
    )
    assert rows[1]["current_value"] == pytest.approx(15_000.0)
    assert rows[1]["notgroschen"] is True
    assert rows[1]["annual_gain_rate_pct"] == pytest.approx(
        DEFAULT_ANNUAL_GAIN_RATES[AssetType.CASH] * 100
    )
    assert rows[2]["inheritance_age"] == 70
    assert rows[3]["investment_amount"] == pytest.approx(50_000.0)
    assert rows[3]["investment_age"] == 40
    # Nothing starts with unrealized gains, so cost basis == current value.
    assert all(row["unrealized_gains"] == pytest.approx(0.0) for row in rows)


def test_default_asset_rows_carry_the_full_row_shape() -> None:
    # Every default row must hold every field, or a row editor reading a
    # missing key would fall back to a different value than the cache does.
    shape = set(_new_asset_row())

    for row in _default_asset_rows():
        assert set(row) == shape, row["name"]


def test_default_scenario_forecasts_without_error() -> None:
    # The shipped defaults must be a valid scenario end to end: a first run
    # with no cache builds exactly these rows.
    profile = _default_profile_state()
    assets = [_asset_from_row(row) for row in _default_asset_rows()]

    df = forecast_wealth(
        profile=UserProfile(
            current_age_years=profile["current_age_years"],
            retirement_age=profile["retirement_age"],
            end_age=profile["end_age"],
        ),
        assets=assets,
    )

    assert profile["current_age_years"] == 30
    assert df["age_years"].iloc[0] == 30
    # The purchase at 40 is paid out of the ETF, and the buffer is untouched.
    purchase_month = (40 - 30) * 12
    assert (
        df.loc[purchase_month, "ETF MSCI World"]
        < df.loc[purchase_month - 1, "ETF MSCI World"]
    )
    assert df.loc[purchase_month, "Notgroschen"] == pytest.approx(
        df.loc[purchase_month - 1, "Notgroschen"], rel=1e-3
    )


def test_build_chart_options_has_expected_shape() -> None:
    options = _build_chart_options()

    assert options["tooltip"]["trigger"] == "axis"
    assert options["legend"]["top"] == 0
    assert options["xAxis"]["type"] == "category"
    assert options["xAxis"]["data"] == []
    assert options["yAxis"]["type"] == "value"
    assert options["series"] == []


def test_build_chart_options_log_scale_sets_log_y_axis() -> None:
    log_axis = _build_chart_options(log_scale=True)["yAxis"]
    assert log_axis["type"] == "log"
    # Visible axis bottom stays at 1000 EUR; series falling below it slide off
    # the bottom of the chart.
    assert log_axis["min"] == 1000

    linear_axis = _build_chart_options(log_scale=False)["yAxis"]
    assert linear_axis["type"] == "value"
    assert "min" not in linear_axis


def test_default_withdrawal_state_includes_state_pension_inputs() -> None:
    state = _default_withdrawal_state()

    assert state["monthly_withdrawal"] == pytest.approx(3000.0)
    assert state["state_pension_current_monthly_amount"] == pytest.approx(
        350.0
    )
    assert state["state_pension_growth_per_working_year"] == pytest.approx(0.0)
    assert state["state_pension_start_age"] == 67
    assert state["state_pension_adjustment_rate_pct"] == pytest.approx(1.0)


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
            "bav_retirement_age": 68,
            "bav_transfer_etf_ratio_pct": 75.0,
        }
    )

    assert asset.bav_strategy == BAVStrategy.INCOME
    assert asset.bav_transfer_etf_ratio == pytest.approx(0.75)


def test_asset_from_row_vbl_points_to_pension() -> None:
    asset = _asset_from_row(
        {
            "name": "VBL",
            "type": AssetType.VBL_KLASSIK.value,
            "vbl_input_mode": "points",
            "vbl_points": 250.0,
            "vbl_still_working": True,
            "vbl_start_age": 67,
        }
    )

    assert asset.asset_type == AssetType.VBL_KLASSIK
    assert asset.current_value == pytest.approx(0.0)
    # 250 points x €4/point = €1 000 gross monthly pension.
    assert asset.vbl_monthly_pension == pytest.approx(1_000.0)
    # Still working -> one point (€4) of extra pension per working year.
    assert asset.vbl_monthly_growth_per_working_year == pytest.approx(4.0)
    assert asset.vbl_start_age == 67


def test_asset_from_row_vbl_euro_mode_and_no_growth_when_not_working() -> None:
    asset = _asset_from_row(
        {
            "name": "VBL",
            "type": AssetType.VBL_KLASSIK.value,
            "vbl_input_mode": "euro",
            "vbl_monthly_pension": 800.0,
            "vbl_points": 999.0,  # ignored in euro mode
            "vbl_still_working": False,
            "vbl_tax_rate_pct": 10.0,
        }
    )

    assert asset.vbl_monthly_pension == pytest.approx(800.0)
    assert asset.vbl_monthly_growth_per_working_year == pytest.approx(0.0)
    assert asset.vbl_tax_rate == pytest.approx(0.10)


def test_normalize_asset_row_coerces_vbl_fields() -> None:
    normalized = _normalize_asset_row(
        {
            "name": "VBL",
            "type": AssetType.VBL_KLASSIK.value,
            "vbl_input_mode": "bogus",
            "vbl_points": "100",
            "vbl_still_working": "true",
            "vbl_start_age": "65",
            "vbl_tax_rate_pct": "150",
        }
    )

    assert normalized["vbl_input_mode"] == "points"
    assert normalized["vbl_points"] == pytest.approx(100.0)
    assert normalized["vbl_still_working"] is True
    assert normalized["vbl_start_age"] == 65
    assert normalized["vbl_tax_rate_pct"] == pytest.approx(100.0)


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


def test_asset_from_row_maps_contribution_growth_pct() -> None:
    asset = _asset_from_row(
        {
            "name": "ETF",
            "type": AssetType.ETF.value,
            "current_value": 1_000.0,
            "monthly_contribution": 500.0,
            "monthly_contribution_growth_pct": 2.5,
        }
    )

    assert asset.monthly_contribution_growth_rate == pytest.approx(0.025)


def test_normalize_asset_row_defaults_contribution_growth_to_zero() -> None:
    # A row cached before the field existed must load as a flat contribution.
    normalized = _normalize_asset_row(
        {
            "name": "Daily account",
            "type": AssetType.CASH.value,
            "current_value": 50_000.0,
            "monthly_contribution": 0.0,
        }
    )

    assert normalized["monthly_contribution_growth_pct"] == pytest.approx(0.0)


def test_asset_from_row_maps_investment_fields() -> None:
    asset = _asset_from_row(
        {
            "name": "House",
            "type": AssetType.INVESTMENT.value,
            "investment_kind": "long_term",
            "investment_amount": 400_000.0,
            "investment_age": 45,
            "investment_interest_rate_pct": 3.5,
            "investment_monthly_payment": 1_800.0,
        }
    )

    assert asset.investment_kind is InvestmentKind.LONG_TERM
    assert asset.investment_amount == pytest.approx(400_000.0)
    assert asset.investment_age == 45
    assert asset.investment_interest_rate == pytest.approx(0.035)
    assert asset.investment_monthly_payment == pytest.approx(1_800.0)
    # A purchase holds no balance of its own.
    assert asset.current_value == pytest.approx(0.0)


def test_asset_from_row_zeroes_inactive_investment() -> None:
    asset = _asset_from_row(
        {
            "name": "House",
            "type": AssetType.INVESTMENT.value,
            "investment_kind": "long_term",
            "investment_amount": 400_000.0,
            "investment_monthly_payment": 1.0,
            "active": False,
        }
    )

    # Hidden rows must never block the forecast with an unserviceable loan.
    assert asset.investment_amount == pytest.approx(0.0)


def test_investment_has_no_value_column() -> None:
    assets = [
        _asset_from_row(
            {
                "name": "Cash",
                "type": AssetType.CASH.value,
                "current_value": 1_000.0,
            }
        ),
        _asset_from_row(
            {
                "name": "Car",
                "type": AssetType.INVESTMENT.value,
                "investment_amount": 10_000.0,
            }
        ),
    ]

    assert _asset_value_columns(assets) == ["Cash", "total"]


def test_asset_from_row_maps_notgroschen_for_cash() -> None:
    asset = _asset_from_row(
        {
            "name": "Daily account",
            "type": AssetType.CASH.value,
            "current_value": 20_000.0,
            "notgroschen": True,
            "notgroschen_keep_inflation": True,
            "notgroschen_inflation_rate_pct": 2.0,
        }
    )

    assert asset.notgroschen is True
    assert asset.notgroschen_keep_inflation is True
    assert asset.notgroschen_inflation_rate == pytest.approx(0.02)


def test_asset_from_row_drops_notgroschen_for_non_cash() -> None:
    # A row switched from Cash to ETF keeps the stale flag; the conversion
    # drops it so the engine never sees an invalid combination.
    asset = _asset_from_row(
        {
            "name": "ETF",
            "type": AssetType.ETF.value,
            "current_value": 20_000.0,
            "notgroschen": True,
            "notgroschen_keep_inflation": True,
            "notgroschen_inflation_rate_pct": 2.0,
        }
    )

    assert asset.notgroschen is False
    assert asset.notgroschen_keep_inflation is False
    assert asset.notgroschen_inflation_rate == pytest.approx(0.0)

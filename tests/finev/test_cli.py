"""Unit tests for the console forecast entrypoint."""

from __future__ import annotations

import pytest

from finev.cli import (
    balance_asset_names,
    build_default_assets,
    build_default_profile,
    build_default_withdrawal,
    print_yearly_summary,
    run,
    summarize_yearly,
)
from finev.forecast import forecast_wealth


def test_default_scenario_builders_are_consistent() -> None:
    profile = build_default_profile()
    assets = build_default_assets()
    withdrawal = build_default_withdrawal()

    assert profile.retirement_age == 67
    assert profile.current_age_years == 30
    assert {asset.name for asset in assets} == {
        "ETF MSCI World",
        "Notgroschen",
        "Inheritance",
        "Car",
    }
    # Only the balance-holding assets get a printed column.
    assert balance_asset_names(assets) == ["ETF MSCI World", "Notgroschen"]
    assert withdrawal.monthly_withdrawal == 3000.0


def test_summarize_yearly_has_one_row_per_age_year() -> None:
    profile = build_default_profile()
    assets = build_default_assets()
    asset_names = balance_asset_names(assets)

    monthly = forecast_wealth(
        profile=profile,
        assets=assets,
        withdrawal=build_default_withdrawal(),
    )
    yearly = summarize_yearly(monthly, asset_names=asset_names)

    expected_years = profile.end_age - profile.current_age_years + 1
    assert len(yearly) == expected_years
    assert yearly["age_years"].is_monotonic_increasing
    # Yearly balances are end-of-year snapshots, so columns must be present.
    for name in [*asset_names, "total", "taxes", "net_cashflow"]:
        assert name in yearly.columns


def test_print_yearly_summary_emits_header_and_rows(
    capsys: pytest.CaptureFixture[str],
) -> None:
    profile = build_default_profile()
    assets = build_default_assets()
    asset_names = balance_asset_names(assets)
    monthly = forecast_wealth(
        profile=profile,
        assets=assets,
        withdrawal=build_default_withdrawal(),
    )
    yearly = summarize_yearly(monthly, asset_names=asset_names)

    print_yearly_summary(yearly, assets=assets, currency=profile.currency)

    out = capsys.readouterr().out
    assert "Age" in out
    assert "total" in out
    assert "EUR" in out


def test_run_prints_a_forecast(
    capsys: pytest.CaptureFixture[str],
) -> None:
    run()

    out = capsys.readouterr().out
    assert "ETF MSCI World" in out
    assert "total" in out

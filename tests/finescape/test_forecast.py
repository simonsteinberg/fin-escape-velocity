import pytest

from finev.forecast import forecast_wealth
from finev.models import Asset, AssetType, UserProfile, WithdrawalPlan


def test_default_rate_used_for_missing_rate() -> None:
    """Use the default annual rate when none is provided."""
    profile = UserProfile(current_age_years=30, retirement_age=30, end_age=31)
    asset = Asset(
        name="ETF",
        asset_type=AssetType.ETF,
        current_value=100.0,
        annual_gain_rate=None,
        monthly_contribution=0.0,
    )

    result = forecast_wealth(profile=profile, assets=[asset])

    monthly_rate = (1 + 0.05) ** (1 / 12) - 1
    expected = 100.0 * (1 + monthly_rate)

    assert result.loc[0, "ETF"] == pytest.approx(100.0)
    assert result.loc[1, "ETF"] == pytest.approx(expected)


def test_contributions_applied_before_retirement() -> None:
    """Apply contributions before retirement and stop afterward."""
    profile = UserProfile(current_age_years=30, retirement_age=31, end_age=31)
    asset = Asset(
        name="ETF",
        asset_type=AssetType.ETF,
        current_value=100.0,
        annual_gain_rate=0.0,
        monthly_contribution=10.0,
    )

    result = forecast_wealth(profile=profile, assets=[asset])

    assert result.loc[1, "ETF"] == pytest.approx(110.0)
    assert result.loc[1, "net_cashflow"] == pytest.approx(10.0)


def test_withdrawal_proportional_after_retirement() -> None:
    """Withdraw proportionally across assets after retirement."""
    profile = UserProfile(current_age_years=67, retirement_age=67, end_age=68)
    assets = [
        Asset(
            name="Asset A",
            asset_type=AssetType.ETF,
            current_value=50.0,
            annual_gain_rate=0.0,
            monthly_contribution=0.0,
        ),
        Asset(
            name="Asset B",
            asset_type=AssetType.CASH,
            current_value=150.0,
            annual_gain_rate=0.0,
            monthly_contribution=0.0,
        ),
    ]
    withdrawal = WithdrawalPlan(monthly_withdrawal=100.0)

    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )

    assert result.loc[1, "Asset A"] == pytest.approx(25.0)
    assert result.loc[1, "Asset B"] == pytest.approx(75.0)
    assert result.loc[1, "net_cashflow"] == pytest.approx(-100.0)


def test_withdrawal_exceeding_total_floors_balances() -> None:
    """Floor balances to zero when withdrawals exceed total."""
    profile = UserProfile(current_age_years=67, retirement_age=67, end_age=68)
    assets = [
        Asset(
            name="Asset A",
            asset_type=AssetType.ETF,
            current_value=10.0,
            annual_gain_rate=0.0,
            monthly_contribution=0.0,
        ),
        Asset(
            name="Asset B",
            asset_type=AssetType.CASH,
            current_value=20.0,
            annual_gain_rate=0.0,
            monthly_contribution=0.0,
        ),
    ]
    withdrawal = WithdrawalPlan(monthly_withdrawal=40.0)

    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )

    assert result.loc[1, "Asset A"] == pytest.approx(0.0)
    assert result.loc[1, "Asset B"] == pytest.approx(0.0)
    assert result.loc[1, "net_cashflow"] == pytest.approx(-30.0)


def test_withdrawal_inflates_with_average_rate() -> None:
    """Increase withdrawal target using average inflation rate."""
    profile = UserProfile(
        current_age_years=40,
        retirement_age=41,
        end_age=42,
        average_inflation_rate=0.12,
    )
    asset = Asset(
        name="Cash",
        asset_type=AssetType.CASH,
        current_value=20_000.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    withdrawal = WithdrawalPlan(monthly_withdrawal=1_000.0)

    result = forecast_wealth(
        profile=profile, assets=[asset], withdrawal=withdrawal
    )

    monthly_rate = (1 + 0.12) ** (1 / 12) - 1
    expected_first = 1_000.0 * (1 + monthly_rate) ** 12
    expected_next = 1_000.0 * (1 + monthly_rate) ** 13

    assert result.loc[12, "net_cashflow"] == pytest.approx(-expected_first)
    assert result.loc[13, "net_cashflow"] == pytest.approx(-expected_next)
    assert result.loc[12, "taxes"] == pytest.approx(0.0)


def test_etf_withdrawal_applies_tax_on_gains() -> None:
    """Apply ETF taxes based on the gains portion of the withdrawal."""
    profile = UserProfile(current_age_years=67, retirement_age=67, end_age=68)
    asset = Asset(
        name="ETF",
        asset_type=AssetType.ETF,
        current_value=100_000.0,
        initial_cost_basis=60_000.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    withdrawal = WithdrawalPlan(monthly_withdrawal=1_000.0)

    result = forecast_wealth(
        profile=profile, assets=[asset], withdrawal=withdrawal
    )

    assert result.loc[1, "ETF"] == pytest.approx(99_000.0)
    assert result.loc[1, "taxes"] == pytest.approx(73.5)
    assert result.loc[1, "net_cashflow"] == pytest.approx(-926.5)


def test_non_etf_withdrawal_has_no_tax() -> None:
    """Do not apply taxes to non-ETF withdrawals."""
    profile = UserProfile(current_age_years=67, retirement_age=67, end_age=68)
    asset = Asset(
        name="Cash",
        asset_type=AssetType.CASH,
        current_value=10_000.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    withdrawal = WithdrawalPlan(monthly_withdrawal=500.0)

    result = forecast_wealth(
        profile=profile, assets=[asset], withdrawal=withdrawal
    )

    assert result.loc[1, "taxes"] == pytest.approx(0.0)
    assert result.loc[1, "net_cashflow"] == pytest.approx(-500.0)

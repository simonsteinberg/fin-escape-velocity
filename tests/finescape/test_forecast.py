import pytest

from finev.forecast import forecast_wealth
from finev.models import (
    Asset,
    AssetType,
    BAVStrategy,
    UserProfile,
    WithdrawalPlan,
)


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
    profile = UserProfile(
        current_age_years=67,
        retirement_age=67,
        end_age=68,
        average_inflation_rate=0.0,
    )
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
    profile = UserProfile(
        current_age_years=67,
        retirement_age=67,
        end_age=68,
        average_inflation_rate=0.0,
    )
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
    profile = UserProfile(
        current_age_years=67,
        retirement_age=67,
        end_age=68,
        average_inflation_rate=0.0,
    )
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

    tax_factor = 0.4 * 0.7 * 0.2625
    gross_withdrawal = 1_000.0 / (1 - tax_factor)
    expected_taxes = gross_withdrawal * tax_factor
    expected_balance = 100_000.0 - gross_withdrawal

    assert result.loc[1, "ETF"] == pytest.approx(expected_balance)
    assert result.loc[1, "taxes"] == pytest.approx(expected_taxes)
    assert result.loc[1, "net_cashflow"] == pytest.approx(-1_000.0)


def test_non_etf_withdrawal_has_no_tax() -> None:
    """Do not apply taxes to non-ETF withdrawals."""
    profile = UserProfile(
        current_age_years=67,
        retirement_age=67,
        end_age=68,
        average_inflation_rate=0.0,
    )
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


def test_bav_transfer_moves_balance_to_targets_and_taxes_gains() -> None:
    profile = UserProfile(
        current_age_years=67,
        retirement_age=67,
        end_age=68,
        average_inflation_rate=0.0,
    )
    assets = [
        Asset(
            name="bAV",
            asset_type=AssetType.BAV,
            current_value=100_000.0,
            initial_cost_basis=60_000.0,
            annual_gain_rate=0.0,
            monthly_contribution=0.0,
            bav_strategy=BAVStrategy.TRANSFER,
            bav_transfer_start_age=67,
            bav_transfer_end_age=67,
            bav_transfer_etf_ratio=0.75,
        ),
        Asset(
            name="ETF",
            asset_type=AssetType.ETF,
            current_value=0.0,
            annual_gain_rate=0.0,
            monthly_contribution=0.0,
        ),
        Asset(
            name="Cash",
            asset_type=AssetType.CASH,
            current_value=0.0,
            annual_gain_rate=0.0,
            monthly_contribution=0.0,
        ),
    ]
    withdrawal = WithdrawalPlan(monthly_withdrawal=0.0)

    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )

    start_months = 67 * 12
    end_months = (67 + 1) * 12 - 1
    age_months = start_months + 1
    remaining_months = end_months - age_months + 1
    transfer_fraction = 1 / remaining_months

    gross_transfer = 100_000.0 * transfer_fraction
    gains = 40_000.0 * transfer_fraction
    expected_tax = gains * 0.2625
    expected_net = gross_transfer - expected_tax
    expected_etf = expected_net * 0.75
    expected_cash = expected_net * 0.25
    expected_bav = 100_000.0 - gross_transfer

    assert result.loc[1, "bAV"] == pytest.approx(expected_bav)
    assert result.loc[1, "ETF"] == pytest.approx(expected_etf)
    assert result.loc[1, "Cash"] == pytest.approx(expected_cash)
    assert result.loc[1, "taxes"] == pytest.approx(expected_tax)
    assert result.loc[1, "net_cashflow"] == pytest.approx(-expected_tax)


def test_bav_income_pays_monthly_gains_after_retirement() -> None:
    profile = UserProfile(
        current_age_years=67,
        retirement_age=67,
        end_age=68,
        average_inflation_rate=0.0,
    )
    asset = Asset(
        name="bAV",
        asset_type=AssetType.BAV,
        current_value=120_000.0,
        annual_gain_rate=0.12,
        monthly_contribution=0.0,
        bav_strategy=BAVStrategy.INCOME,
    )
    withdrawal = WithdrawalPlan(monthly_withdrawal=0.0)

    result = forecast_wealth(
        profile=profile, assets=[asset], withdrawal=withdrawal
    )

    monthly_rate = (1 + 0.12) ** (1 / 12) - 1
    expected_gain = 120_000.0 * monthly_rate
    expected_tax = expected_gain * 0.2625
    expected_net = expected_gain - expected_tax

    assert result.loc[1, "bAV"] == pytest.approx(120_000.0)
    assert result.loc[1, "taxes"] == pytest.approx(expected_tax)
    assert result.loc[1, "net_cashflow"] == pytest.approx(expected_net)

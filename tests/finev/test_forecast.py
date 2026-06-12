import pytest

from finev.config import get_config
from finev.forecast import forecast_wealth
from finev.models import (
    Asset,
    AssetType,
    BAVStrategy,
    InheritanceRelationship,
    StatePension,
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


def test_withdrawal_exceeding_total_goes_into_debt() -> None:
    """Drain balances to zero and book the unmet need as negative wealth."""
    profile = UserProfile(
        current_age_years=67,
        retirement_age=67,
        end_age=68,
        average_inflation_rate=0.0,
        debt_interest_rate=0.0,
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

    # Assets are exhausted, the 10 unmet need becomes debt, and the total goes
    # negative; net cashflow reflects the full 40 funded need.
    assert result.loc[1, "Asset A"] == pytest.approx(0.0)
    assert result.loc[1, "Asset B"] == pytest.approx(0.0)
    assert result.loc[1, "total"] == pytest.approx(-10.0)
    assert result.loc[1, "net_cashflow"] == pytest.approx(-40.0)


def test_debt_accrues_interest_each_month() -> None:
    """Negative wealth compounds at the configured annual debt interest rate."""
    profile = UserProfile(
        current_age_years=67,
        retirement_age=67,
        end_age=69,
        average_inflation_rate=0.0,
        debt_interest_rate=0.12,
    )
    # No assets to draw on, so the whole withdrawal is borrowed every month.
    assets = [
        Asset(
            name="Cash",
            asset_type=AssetType.CASH,
            current_value=0.0,
            annual_gain_rate=0.0,
            monthly_contribution=0.0,
        )
    ]
    withdrawal = WithdrawalPlan(monthly_withdrawal=100.0)

    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )

    monthly_rate = (1 + 0.12) ** (1 / 12) - 1
    # Month 1: borrow 100, then a month of interest.
    debt_month_1 = 100.0 * (1 + monthly_rate)
    # Month 2: prior debt plus another 100 borrowed, then interest again.
    debt_month_2 = (debt_month_1 + 100.0) * (1 + monthly_rate)
    assert result.loc[1, "total"] == pytest.approx(-debt_month_1)
    assert result.loc[2, "total"] == pytest.approx(-debt_month_2)


def test_inheritance_repays_outstanding_debt() -> None:
    """Net inheritance proceeds pay down debt before being invested."""
    profile = UserProfile(
        current_age_years=67,
        retirement_age=67,
        end_age=69,
        average_inflation_rate=0.0,
        debt_interest_rate=0.0,
    )
    assets = [
        Asset(
            name="ETF",
            asset_type=AssetType.ETF,
            current_value=0.0,
            annual_gain_rate=0.0,
            monthly_contribution=0.0,
        ),
        # Kind Freibetrag is 400 000 €; 50 000 € is tax-free, received at 68.
        Asset(
            name="Estate",
            asset_type=AssetType.INHERITANCE,
            current_value=0.0,
            inheritance_gross_amount=50_000.0,
            inheritance_age=68,
            inheritance_relationship=InheritanceRelationship.KIND,
        ),
    ]
    withdrawal = WithdrawalPlan(monthly_withdrawal=1_000.0)

    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )

    inheritance_month = (68 - 67) * 12
    # By the inheritance month, 11 prior months borrowed 1 000 each (11 000
    # debt). That month: inheritance repays the 11 000 and invests the rest in
    # ETF, then a further 1 000 is withdrawn from ETF — netting 38 000 in ETF
    # and no remaining debt.
    assert result.loc[inheritance_month, "ETF"] == pytest.approx(38_000.0)
    assert result.loc[inheritance_month, "total"] == pytest.approx(38_000.0)


def test_privatinsolvenz_floors_total_wealth() -> None:
    """Total wealth never falls below the configured insolvency floor."""
    floor = get_config().insolvency.schwelle_euro
    profile = UserProfile(
        current_age_years=67,
        retirement_age=67,
        end_age=100,
        average_inflation_rate=0.0,
        debt_interest_rate=0.08,
    )
    # No assets to draw on, so debt would grow far past the floor unchecked.
    assets = [
        Asset(
            name="Cash",
            asset_type=AssetType.CASH,
            current_value=0.0,
            annual_gain_rate=0.0,
            monthly_contribution=0.0,
        )
    ]
    withdrawal = WithdrawalPlan(monthly_withdrawal=3_000.0)

    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )

    assert (result["total"] >= -floor - 1e-6).all()
    assert result["total"].min() == pytest.approx(-floor)
    # Without any rescue, the forecast ends pinned at the floor.
    assert result["total"].iloc[-1] == pytest.approx(-floor)


def test_inheritance_lets_forecast_escape_privatinsolvenz() -> None:
    """A later inheritance repays the capped debt and lifts wealth back green."""
    floor = get_config().insolvency.schwelle_euro
    profile = UserProfile(
        current_age_years=67,
        retirement_age=67,
        end_age=100,
        average_inflation_rate=0.0,
        debt_interest_rate=0.0,
    )
    assets = [
        Asset(
            name="Cash",
            asset_type=AssetType.CASH,
            current_value=0.0,
            annual_gain_rate=0.0,
            monthly_contribution=0.0,
        ),
        # Kind: gross 500 000, Freibetrag 400 000, taxable 100 000 @ 11% = 11 000
        # tax, so 489 000 net arrives at age 70.
        Asset(
            name="Estate",
            asset_type=AssetType.INHERITANCE,
            current_value=0.0,
            inheritance_gross_amount=500_000.0,
            inheritance_age=70,
            inheritance_relationship=InheritanceRelationship.KIND,
        ),
    ]
    withdrawal = WithdrawalPlan(monthly_withdrawal=5_000.0)

    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )

    # Age 69: debt has been capped at the floor (Privatinsolvenz).
    assert result.loc[24, "total"] == pytest.approx(-floor)
    # Age 70: the 489 000 net inheritance repays the 100 000 capped debt and the
    # remaining 389 000 (less that month's 5 000 withdrawal) is invested — wealth
    # is firmly green again.
    inheritance_month = (70 - 67) * 12
    assert result.loc[inheritance_month, "total"] == pytest.approx(384_000.0)
    # End of life: spent down again and back at the floor, never below it.
    assert result.loc[396, "total"] == pytest.approx(-floor)
    assert (result["total"] >= -floor - 1e-6).all()


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


def test_etf_withdrawal_uses_allowance_before_taxes() -> None:
    """Use the ETF allowance before applying taxes."""
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

    expected_balance = 100_000.0 - 1_000.0

    assert result.loc[1, "ETF"] == pytest.approx(expected_balance)
    assert result.loc[1, "taxes"] == pytest.approx(0.0)
    assert result.loc[1, "net_cashflow"] == pytest.approx(-1_000.0)


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
    withdrawal = WithdrawalPlan(monthly_withdrawal=20_000.0)

    result = forecast_wealth(
        profile=profile, assets=[asset], withdrawal=withdrawal
    )

    config = get_config()
    gains_ratio = 0.4
    taxable_gains_ratio = gains_ratio * config.etf.taxable_share
    allowance = config.etf.steuerfreibetrag_euro
    tax_rate = config.capital_gains_tax_rate
    allowance_threshold = allowance / taxable_gains_ratio
    if withdrawal.monthly_withdrawal <= allowance_threshold:
        gross_withdrawal = withdrawal.monthly_withdrawal
    else:
        gross_withdrawal = (
            withdrawal.monthly_withdrawal - (tax_rate * allowance)
        ) / (1 - tax_rate * taxable_gains_ratio)
    taxable_gains = gross_withdrawal * taxable_gains_ratio
    taxable_after_allowance = max(taxable_gains - allowance, 0.0)
    expected_taxes = taxable_after_allowance * tax_rate
    expected_balance = 100_000.0 - gross_withdrawal

    assert result.loc[1, "ETF"] == pytest.approx(expected_balance)
    assert result.loc[1, "taxes"] == pytest.approx(expected_taxes)
    assert result.loc[1, "net_cashflow"] == pytest.approx(-20_000.0)


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
            bav_retirement_age=67,
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

    config = get_config()
    gross_transfer = 100_000.0 * transfer_fraction
    gains = 40_000.0 * transfer_fraction
    expected_tax = gains * config.capital_gains_tax_rate
    expected_net = gross_transfer - expected_tax
    expected_etf = expected_net * 0.75
    expected_cash = expected_net * 0.25
    expected_bav = 100_000.0 - gross_transfer

    assert result.loc[1, "bAV"] == pytest.approx(expected_bav)
    assert result.loc[1, "ETF"] == pytest.approx(expected_etf)
    assert result.loc[1, "Cash"] == pytest.approx(expected_cash)
    assert result.loc[1, "taxes"] == pytest.approx(expected_tax)
    assert result.loc[1, "net_cashflow"] == pytest.approx(-expected_tax)


def test_bav_income_grows_before_withdraw_start_age() -> None:
    """bAV INCOME balance compounds at annual_gain_rate before bav_retirement_age."""
    profile = UserProfile(
        current_age_years=62,
        retirement_age=62,
        end_age=63,
        average_inflation_rate=0.0,
    )
    asset = Asset(
        name="bAV",
        asset_type=AssetType.BAV,
        current_value=100_000.0,
        annual_gain_rate=0.12,
        monthly_contribution=0.0,
        bav_strategy=BAVStrategy.INCOME,
        bav_retirement_age=67,
    )
    withdrawal = WithdrawalPlan(monthly_withdrawal=0.0)

    result = forecast_wealth(
        profile=profile, assets=[asset], withdrawal=withdrawal
    )

    monthly_rate = (1 + 0.12) ** (1 / 12) - 1
    expected_balance = 100_000.0 * (1 + monthly_rate)

    # Balance must grow — income not yet active before withdraw start age
    assert result.loc[1, "bAV"] == pytest.approx(expected_balance)
    assert result.loc[1, "net_cashflow"] == pytest.approx(0.0)
    assert result.loc[1, "taxes"] == pytest.approx(0.0)


def test_bav_income_pays_from_withdraw_start_age() -> None:
    """bAV INCOME pays monthly gains and freezes balance once withdraw start age is reached."""
    profile = UserProfile(
        current_age_years=67,
        retirement_age=62,
        end_age=68,
        average_inflation_rate=0.0,
    )
    asset = Asset(
        name="bAV",
        asset_type=AssetType.BAV,
        current_value=100_000.0,
        annual_gain_rate=0.12,
        monthly_contribution=0.0,
        bav_strategy=BAVStrategy.INCOME,
        bav_retirement_age=67,
    )
    withdrawal = WithdrawalPlan(monthly_withdrawal=0.0)

    result = forecast_wealth(
        profile=profile, assets=[asset], withdrawal=withdrawal
    )

    config = get_config()
    monthly_rate = (1 + 0.12) ** (1 / 12) - 1
    expected_gain = 100_000.0 * monthly_rate
    expected_tax = expected_gain * config.capital_gains_tax_rate
    expected_net = expected_gain - expected_tax

    # Balance must stay flat — all gain paid as income
    assert result.loc[1, "bAV"] == pytest.approx(100_000.0)
    assert result.loc[1, "taxes"] == pytest.approx(expected_tax)
    assert result.loc[1, "net_cashflow"] == pytest.approx(expected_net)


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

    config = get_config()
    monthly_rate = (1 + 0.12) ** (1 / 12) - 1
    expected_gain = 120_000.0 * monthly_rate
    expected_tax = expected_gain * config.capital_gains_tax_rate
    expected_net = expected_gain - expected_tax

    assert result.loc[1, "bAV"] == pytest.approx(120_000.0)
    assert result.loc[1, "taxes"] == pytest.approx(expected_tax)
    assert result.loc[1, "net_cashflow"] == pytest.approx(expected_net)


def test_state_pension_reduces_withdrawal_from_start_age() -> None:
    profile = UserProfile(
        current_age_years=40,
        retirement_age=42,
        end_age=68,
        average_inflation_rate=0.0,
    )
    asset = Asset(
        name="Cash",
        asset_type=AssetType.CASH,
        current_value=2_000_000.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    withdrawal = WithdrawalPlan(
        monthly_withdrawal=3_000.0,
        state_pension=StatePension(
            current_monthly_amount=1_000.0,
            monthly_growth_per_working_year=30.0,
            start_age=67,
        ),
    )

    result = forecast_wealth(
        profile=profile, assets=[asset], withdrawal=withdrawal
    )

    config = get_config()
    pre_start_month = (67 - 40) * 12 - 1
    start_month = (67 - 40) * 12
    expected_net_pension = (1_000.0 + 2 * 30.0) * (
        1 - config.drv.brutto_rente_steuersatz
    )
    expected_withdrawal = 3_000.0 - expected_net_pension

    assert result.loc[pre_start_month, "net_cashflow"] == pytest.approx(
        -3_000.0
    )
    assert result.loc[start_month, "net_cashflow"] == pytest.approx(
        -expected_withdrawal
    )


def test_state_pension_applies_early_retirement_reduction() -> None:
    profile = UserProfile(
        current_age_years=60,
        retirement_age=60,
        end_age=66,
        average_inflation_rate=0.0,
    )
    asset = Asset(
        name="Cash",
        asset_type=AssetType.CASH,
        current_value=500_000.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    withdrawal = WithdrawalPlan(
        monthly_withdrawal=3_000.0,
        state_pension=StatePension(
            current_monthly_amount=1_000.0,
            monthly_growth_per_working_year=0.0,
            start_age=65,
        ),
    )

    result = forecast_wealth(
        profile=profile, assets=[asset], withdrawal=withdrawal
    )

    config = get_config()
    reduction_years = 67 - 65
    reduction_factor = 1 - (
        config.drv.rentenabschlag_pro_jahr * reduction_years
    )
    expected_net_pension = (
        1_000.0 * reduction_factor * (1 - config.drv.brutto_rente_steuersatz)
    )
    start_month = (65 - 60) * 12
    expected_withdrawal = 3_000.0 - expected_net_pension

    assert result.loc[start_month, "net_cashflow"] == pytest.approx(
        -expected_withdrawal
    )


def test_state_pension_inflation_adjusted_with_time() -> None:
    profile = UserProfile(
        current_age_years=40,
        retirement_age=42,
        end_age=68,
        average_inflation_rate=0.02,
    )
    asset = Asset(
        name="Cash",
        asset_type=AssetType.CASH,
        current_value=2_000_000.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    withdrawal = WithdrawalPlan(
        monthly_withdrawal=3_000.0,
        state_pension=StatePension(
            current_monthly_amount=1_000.0,
            monthly_growth_per_working_year=30.0,
            start_age=67,
        ),
    )

    result = forecast_wealth(
        profile=profile, assets=[asset], withdrawal=withdrawal
    )

    config = get_config()
    start_month = (67 - 40) * 12
    monthly_rate = (1 + 0.02) ** (1 / 12) - 1
    inflation_multiplier = (1 + monthly_rate) ** start_month
    base_net_gap = 3_000.0 - (
        (1_000.0 + 2 * 30.0) * (1 - config.drv.brutto_rente_steuersatz)
    )
    expected_withdrawal = base_net_gap * inflation_multiplier

    assert result.loc[start_month, "net_cashflow"] == pytest.approx(
        -expected_withdrawal
    )


def test_pre_retirement_state_pension_invested_in_highest_rate_etf() -> None:
    """Pension drawn while still working flows into the highest-rate ETF.

    With the pension starting before retirement, the gap-year pension income is
    invested in the ETF with the highest annual gain rate (not the lowest), and
    booked as positive net cashflow.
    """
    profile = UserProfile(
        current_age_years=60,
        retirement_age=65,
        end_age=66,
        average_inflation_rate=0.0,
    )
    etf_low = Asset(
        name="ETF_low",
        asset_type=AssetType.ETF,
        current_value=0.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    # ETF_high carries the higher rate, so it is the pension target.
    etf_high = Asset(
        name="ETF_high",
        asset_type=AssetType.ETF,
        current_value=0.0,
        annual_gain_rate=0.05,
        monthly_contribution=0.0,
    )
    withdrawal = WithdrawalPlan(
        monthly_withdrawal=3_000.0,
        state_pension=StatePension(
            current_monthly_amount=1_000.0,
            monthly_growth_per_working_year=0.0,
            start_age=63,
        ),
    )

    result = forecast_wealth(
        profile=profile, assets=[etf_low, etf_high], withdrawal=withdrawal
    )

    config = get_config()
    reduction_years = 67 - 63
    reduction_factor = 1 - (
        config.drv.rentenabschlag_pro_jahr * reduction_years
    )
    net_pension = (
        1_000.0 * reduction_factor * (1 - config.drv.brutto_rente_steuersatz)
    )
    pre_pension_month = (63 - 60) * 12 - 1
    gap_month = (63 - 60) * 12 + 1

    # Before the pension starts there is no inflow while still working.
    assert result.loc[pre_pension_month, "net_cashflow"] == pytest.approx(0.0)
    # During the gap the net pension is invested as positive net cashflow.
    assert result.loc[gap_month, "net_cashflow"] == pytest.approx(net_pension)
    # The high-rate ETF receives the money; the low-rate one stays empty.
    assert result.loc[gap_month, "ETF_high"] > 0.0
    assert result.loc[gap_month, "ETF_low"] == pytest.approx(0.0)


def test_pre_retirement_state_pension_falls_back_to_cash_without_etf() -> None:
    """With no ETF, the gap-year pension is invested in the highest-rate cash."""
    profile = UserProfile(
        current_age_years=60,
        retirement_age=65,
        end_age=66,
        average_inflation_rate=0.0,
    )
    cash_low = Asset(
        name="Cash_low",
        asset_type=AssetType.CASH,
        current_value=0.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    cash_high = Asset(
        name="Cash_high",
        asset_type=AssetType.CASH,
        current_value=0.0,
        annual_gain_rate=0.01,
        monthly_contribution=0.0,
    )
    withdrawal = WithdrawalPlan(
        monthly_withdrawal=3_000.0,
        state_pension=StatePension(
            current_monthly_amount=1_000.0,
            monthly_growth_per_working_year=0.0,
            start_age=63,
        ),
    )

    result = forecast_wealth(
        profile=profile, assets=[cash_low, cash_high], withdrawal=withdrawal
    )

    config = get_config()
    reduction_years = 67 - 63
    reduction_factor = 1 - (
        config.drv.rentenabschlag_pro_jahr * reduction_years
    )
    net_pension = (
        1_000.0 * reduction_factor * (1 - config.drv.brutto_rente_steuersatz)
    )
    gap_month = (63 - 60) * 12 + 1

    assert result.loc[gap_month, "net_cashflow"] == pytest.approx(net_pension)
    assert result.loc[gap_month, "Cash_high"] > 0.0
    assert result.loc[gap_month, "Cash_low"] == pytest.approx(0.0)


def test_pre_retirement_state_pension_accrues_working_years_progressively() -> (
    None
):
    """During the gap the invested pension reflects years worked so far, not the
    full to-retirement accrual.

    The user works through the gap, so working-year growth must accrue month by
    month (capped at retirement) rather than crediting future working years up
    front.
    """
    profile = UserProfile(
        current_age_years=60,
        retirement_age=65,
        end_age=66,
        average_inflation_rate=0.0,
    )
    etf = Asset(
        name="ETF",
        asset_type=AssetType.ETF,
        current_value=0.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    withdrawal = WithdrawalPlan(
        monthly_withdrawal=3_000.0,
        state_pension=StatePension(
            current_monthly_amount=1_500.0,
            monthly_growth_per_working_year=30.0,
            start_age=63,
        ),
    )

    result = forecast_wealth(
        profile=profile, assets=[etf], withdrawal=withdrawal
    )

    config = get_config()
    reduction_factor = 1 - config.drv.rentenabschlag_pro_jahr * (67 - 63)
    tax_factor = 1 - config.drv.brutto_rente_steuersatz

    def expected(worked_years: int) -> float:
        accrued = 1_500.0 + worked_years * 30.0
        return accrued * reduction_factor * tax_factor

    age63_month = (63 - 60) * 12  # exactly 3 years worked by age 63
    age64_month = (64 - 60) * 12  # exactly 4 years worked by age 64

    assert result.loc[age63_month, "net_cashflow"] == pytest.approx(
        expected(3)
    )
    assert result.loc[age64_month, "net_cashflow"] == pytest.approx(
        expected(4)
    )


def test_state_pension_starting_at_retirement_has_no_gap_injection() -> None:
    """When the pension starts at retirement, no pre-retirement inflow occurs."""
    profile = UserProfile(
        current_age_years=60,
        retirement_age=65,
        end_age=66,
        average_inflation_rate=0.0,
    )
    etf = Asset(
        name="ETF",
        asset_type=AssetType.ETF,
        current_value=0.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    withdrawal = WithdrawalPlan(
        monthly_withdrawal=3_000.0,
        state_pension=StatePension(
            current_monthly_amount=1_000.0,
            start_age=65,
        ),
    )

    result = forecast_wealth(
        profile=profile, assets=[etf], withdrawal=withdrawal
    )

    working_month = (65 - 60) * 12 - 1
    assert result.loc[working_month, "net_cashflow"] == pytest.approx(0.0)
    assert result.loc[working_month, "ETF"] == pytest.approx(0.0)


# ── Inheritance tests ─────────────────────────────────────────────────────────


def test_inheritance_below_freibetrag_is_tax_free() -> None:
    """Net inheritance equals gross when amount is within the Freibetrag."""
    profile = UserProfile(
        current_age_years=40,
        retirement_age=67,
        end_age=68,
        average_inflation_rate=0.0,
    )
    etf = Asset(
        name="ETF",
        asset_type=AssetType.ETF,
        current_value=0.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    # Kind Freibetrag is 400 000 €; 100 000 € is fully below it.
    inheritance = Asset(
        name="Inheritance",
        asset_type=AssetType.INHERITANCE,
        current_value=0.0,
        inheritance_gross_amount=100_000.0,
        inheritance_age=50,
        inheritance_relationship=InheritanceRelationship.KIND,
    )
    result = forecast_wealth(profile=profile, assets=[etf, inheritance])

    injection_month = (50 - 40) * 12
    assert result.loc[injection_month, "ETF"] == pytest.approx(100_000.0)
    assert result.loc[injection_month, "taxes"] == pytest.approx(0.0)
    assert result.loc[injection_month, "net_cashflow"] == pytest.approx(
        100_000.0
    )
    # INHERITANCE asset has no balance column in output
    assert "Inheritance" not in result.columns


def test_inheritance_above_freibetrag_applies_correct_rate() -> None:
    """Tax is applied to the taxable portion above the Freibetrag."""
    profile = UserProfile(
        current_age_years=40,
        retirement_age=67,
        end_age=68,
        average_inflation_rate=0.0,
    )
    etf = Asset(
        name="ETF",
        asset_type=AssetType.ETF,
        current_value=0.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    # Kind Freibetrag = 400 000 €; gross = 500 000 €; taxable = 100 000 €.
    # 100 000 € falls in the "bis 300 000" bracket -> 11% rate.
    gross = 500_000.0
    freibetrag = 400_000.0
    taxable = gross - freibetrag
    expected_tax = taxable * 0.11
    inheritance = Asset(
        name="Erbschaft",
        asset_type=AssetType.INHERITANCE,
        current_value=0.0,
        inheritance_gross_amount=gross,
        inheritance_age=55,
        inheritance_relationship=InheritanceRelationship.KIND,
    )
    result = forecast_wealth(profile=profile, assets=[etf, inheritance])

    injection_month = (55 - 40) * 12
    assert result.loc[injection_month, "taxes"] == pytest.approx(expected_tax)
    assert result.loc[injection_month, "ETF"] == pytest.approx(
        gross - expected_tax
    )


def test_inheritance_klasse_iii_applies_higher_rate() -> None:
    """Klasse III applies a higher rate than Klasse I for the same gross amount."""
    profile = UserProfile(
        current_age_years=40,
        retirement_age=67,
        end_age=68,
        average_inflation_rate=0.0,
    )
    etf = Asset(
        name="ETF",
        asset_type=AssetType.ETF,
        current_value=0.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    # Klasse III Freibetrag = 20 000 €; gross = 100 000 €; taxable = 80 000 €.
    # 80 000 € is in "bis 300 000" bracket -> 30% for Klasse III.
    gross = 100_000.0
    freibetrag_iii = 20_000.0
    taxable = gross - freibetrag_iii
    expected_tax = taxable * 0.30
    inheritance = Asset(
        name="Erbschaft",
        asset_type=AssetType.INHERITANCE,
        current_value=0.0,
        inheritance_gross_amount=gross,
        inheritance_age=55,
        inheritance_relationship=InheritanceRelationship.KLASSE_III,
    )
    result = forecast_wealth(profile=profile, assets=[etf, inheritance])

    injection_month = (55 - 40) * 12
    assert result.loc[injection_month, "taxes"] == pytest.approx(expected_tax)


def test_inactive_inheritance_is_not_injected() -> None:
    """An inactive inheritance asset contributes nothing to the portfolio."""
    profile = UserProfile(
        current_age_years=40,
        retirement_age=67,
        end_age=68,
        average_inflation_rate=0.0,
    )
    etf = Asset(
        name="ETF",
        asset_type=AssetType.ETF,
        current_value=1_000.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    inheritance = Asset(
        name="Erbschaft",
        asset_type=AssetType.INHERITANCE,
        current_value=0.0,
        active=False,
        inheritance_gross_amount=500_000.0,
        inheritance_age=50,
        inheritance_relationship=InheritanceRelationship.KIND,
    )
    result = forecast_wealth(profile=profile, assets=[etf, inheritance])

    injection_month = (50 - 40) * 12
    assert result.loc[injection_month, "ETF"] == pytest.approx(1_000.0)
    assert result.loc[injection_month, "taxes"] == pytest.approx(0.0)


# ── VBLklassik tests ──────────────────────────────────────────────────────────


def _vbl_setup(
    *,
    vbl_monthly_pension: float = 1_000.0,
    vbl_monthly_growth_per_working_year: float = 0.0,
    vbl_start_age: int = 67,
    vbl_tax_rate: float | None = None,
    retirement_age: int = 42,
    average_inflation_rate: float = 0.0,
) -> tuple[UserProfile, list[Asset], WithdrawalPlan]:
    """Build a Cash + VBLklassik scenario with a large cash buffer."""
    profile = UserProfile(
        current_age_years=40,
        retirement_age=retirement_age,
        end_age=68,
        average_inflation_rate=average_inflation_rate,
    )
    cash = Asset(
        name="Cash",
        asset_type=AssetType.CASH,
        current_value=2_000_000.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    vbl = Asset(
        name="VBL",
        asset_type=AssetType.VBL_KLASSIK,
        current_value=0.0,
        vbl_monthly_pension=vbl_monthly_pension,
        vbl_monthly_growth_per_working_year=vbl_monthly_growth_per_working_year,
        vbl_start_age=vbl_start_age,
        vbl_tax_rate=vbl_tax_rate,
    )
    return profile, [cash, vbl], WithdrawalPlan(monthly_withdrawal=3_000.0)


def test_vbl_holds_no_balance_column() -> None:
    """A VBLklassik asset is income-only and produces no balance column."""
    profile, assets, withdrawal = _vbl_setup()
    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )
    assert "VBL" not in result.columns
    assert "Cash" in result.columns


def test_vbl_reduces_withdrawal_from_start_age_income_taxed() -> None:
    """VBL pays from its start age, income-taxed, offsetting withdrawals."""
    profile, assets, withdrawal = _vbl_setup(vbl_monthly_pension=1_000.0)
    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )
    config = get_config()
    pre_start = (67 - 40) * 12 - 1
    start = (67 - 40) * 12
    net_pension = 1_000.0 * (1 - config.vbl.brutto_rente_steuersatz)
    assert result.loc[pre_start, "net_cashflow"] == pytest.approx(-3_000.0)
    assert result.loc[start, "net_cashflow"] == pytest.approx(
        -(3_000.0 - net_pension)
    )


def test_vbl_still_working_growth_accrues_over_working_years() -> None:
    """Growth-per-working-year adds to the pension over the working window."""
    # 2 working years (age 40 -> retirement 42) at €4 extra per year.
    profile, assets, withdrawal = _vbl_setup(
        vbl_monthly_pension=1_000.0,
        vbl_monthly_growth_per_working_year=4.0,
        retirement_age=42,
    )
    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )
    config = get_config()
    start = (67 - 40) * 12
    accrued_gross = 1_000.0 + 2 * 4.0
    net_pension = accrued_gross * (1 - config.vbl.brutto_rente_steuersatz)
    assert result.loc[start, "net_cashflow"] == pytest.approx(
        -(3_000.0 - net_pension)
    )


def test_vbl_is_not_inflation_compensated() -> None:
    """Unlike the DRV pension, the VBL pension stays nominal under inflation."""
    profile, assets, withdrawal = _vbl_setup(
        vbl_monthly_pension=1_000.0, average_inflation_rate=0.02
    )
    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )
    config = get_config()
    start = (67 - 40) * 12
    monthly_rate = (1 + 0.02) ** (1 / 12) - 1
    inflation_multiplier = (1 + monthly_rate) ** start
    # The withdrawal target inflates; the VBL pension does not.
    net_pension = 1_000.0 * (1 - config.vbl.brutto_rente_steuersatz)
    expected = 3_000.0 * inflation_multiplier - net_pension
    assert result.loc[start, "net_cashflow"] == pytest.approx(-expected)


def test_vbl_does_not_offset_before_start_age() -> None:
    """A VBL start age after retirement leaves early withdrawals unoffset."""
    profile, assets, withdrawal = _vbl_setup(vbl_start_age=67)
    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )
    # Retirement at 42, VBL starts at 67: the year before VBL is unoffset.
    just_before_vbl = (67 - 40) * 12 - 1
    assert result.loc[just_before_vbl, "net_cashflow"] == pytest.approx(
        -3_000.0
    )


def test_vbl_per_asset_tax_rate_override() -> None:
    """A VBL asset's own tax rate overrides the configured default."""
    profile, assets, withdrawal = _vbl_setup(
        vbl_monthly_pension=1_000.0, vbl_tax_rate=0.0
    )
    result = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )
    start = (67 - 40) * 12
    # Tax rate 0 -> full €1 000 gross offsets the €3 000 target.
    assert result.loc[start, "net_cashflow"] == pytest.approx(-2_000.0)


def test_pre_retirement_vbl_pension_invested_in_highest_rate_etf() -> None:
    """VBL pension drawn while still working flows into the highest-rate ETF."""
    profile = UserProfile(
        current_age_years=60,
        retirement_age=65,
        end_age=66,
        average_inflation_rate=0.0,
    )
    etf_low = Asset(
        name="ETF_low",
        asset_type=AssetType.ETF,
        current_value=0.0,
        annual_gain_rate=0.0,
        monthly_contribution=0.0,
    )
    etf_high = Asset(
        name="ETF_high",
        asset_type=AssetType.ETF,
        current_value=0.0,
        annual_gain_rate=0.05,
        monthly_contribution=0.0,
    )
    vbl = Asset(
        name="VBL",
        asset_type=AssetType.VBL_KLASSIK,
        current_value=0.0,
        vbl_monthly_pension=1_000.0,
        vbl_start_age=63,
        vbl_tax_rate=0.0,
    )
    withdrawal = WithdrawalPlan(monthly_withdrawal=3_000.0)

    result = forecast_wealth(
        profile=profile,
        assets=[etf_low, etf_high, vbl],
        withdrawal=withdrawal,
    )

    pre_pension_month = (63 - 60) * 12 - 1
    gap_month = (63 - 60) * 12 + 1

    # Tax rate 0 -> the full €1 000 gross VBL pension is invested each gap month.
    assert result.loc[pre_pension_month, "net_cashflow"] == pytest.approx(0.0)
    assert result.loc[gap_month, "net_cashflow"] == pytest.approx(1_000.0)
    assert result.loc[gap_month, "ETF_high"] > 0.0
    assert result.loc[gap_month, "ETF_low"] == pytest.approx(0.0)

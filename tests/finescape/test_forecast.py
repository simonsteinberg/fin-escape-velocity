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
    """bAV INCOME balance compounds at annual_gain_rate before bav_transfer_start_age."""
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
        bav_transfer_start_age=67,
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
        bav_transfer_start_age=67,
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

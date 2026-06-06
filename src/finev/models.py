"""Domain models for the wealth forecast app."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AssetType(StrEnum):
    """Enum for supported asset categories."""

    ETF = "ETF"
    BAV = "bAV"
    CASH = "Cash"
    INHERITANCE = "Inheritance"


class BAVStrategy(StrEnum):
    """Enum for bAV handling strategies."""

    TRANSFER = "transfer"
    INCOME = "income"


class AllocationStrategy(StrEnum):
    """Strategy for allocating post-retirement withdrawals across assets."""

    PROPORTIONAL = "proportional"


class InheritanceRelationship(StrEnum):
    """Heir relationship determining Erbschaftsteuer class and Freibetrag.

    Attributes:
        EHEGATTE: Ehegatten / eingetragene Lebenspartner (Klasse I, 500 000 €).
        KIND: Kinder und Stiefkinder (Klasse I, 400 000 €).
        ENKEL: Enkel (Klasse I, 200 000 €).
        ELTERNTEIL: Eltern (Klasse I, 100 000 €).
        KLASSE_II: Geschwister, Nichten, Neffen etc. (Klasse II, 20 000 €).
        KLASSE_III: Alle übrigen Erben (Klasse III, 20 000 €).
    """

    EHEGATTE = "ehegatte"
    KIND = "kind"
    ENKEL = "enkel"
    ELTERNTEIL = "elternteil"
    KLASSE_II = "klasse_ii"
    KLASSE_III = "klasse_iii"


DEFAULT_ANNUAL_GAIN_RATES: dict[AssetType, float] = {
    AssetType.ETF: 0.05,
    AssetType.BAV: 0.02,
    AssetType.CASH: 0.005,
    AssetType.INHERITANCE: 0.0,
}


@dataclass(frozen=True)
class UserProfile:
    """User profile inputs for the forecast.

    Attributes:
        current_age_years: Current age in whole years.
        current_age_months: Additional months beyond whole years.
        retirement_age: Retirement age in years.
        end_age: Forecast end age in years.
        currency: Currency code used for display.
        average_inflation_rate: Average annual inflation rate as a decimal.
        debt_interest_rate: Annual interest rate (as a decimal) charged on
            negative total wealth — the cost of borrowing once assets are
            depleted. Compounds monthly on any outstanding debt.
    """

    current_age_years: int
    current_age_months: int = 0
    retirement_age: int = 67
    end_age: int = 100
    currency: str = "EUR"
    average_inflation_rate: float = 0.02
    debt_interest_rate: float = 0.08


@dataclass(frozen=True)
class Asset:
    """Asset definition and cashflow inputs.

    Attributes:
        name: Display name for the asset.
        asset_type: Asset category used for default gain rates.
        current_value: Starting balance for the asset (unused for INHERITANCE).
        initial_cost_basis: Optional cost basis at forecast start.
        annual_gain_rate: Optional annual gain rate override.
        monthly_contribution: Monthly contribution before retirement.
        active: Whether this asset is included in the forecast.
        bav_strategy: Strategy for handling bAV assets.
        bav_retirement_age: Age (years) at which bAV retirement occurs (transfer
            year for the transfer strategy; payout start for the income strategy).
        bav_transfer_etf_ratio: Share of transfer allocated to ETF assets.
        inheritance_gross_amount: Gross inheritance amount before tax (INHERITANCE only).
        inheritance_age: Age (years) at which the inheritance is received (INHERITANCE only).
        inheritance_relationship: Heir relationship key for tax computation (INHERITANCE only).
    """

    name: str
    asset_type: AssetType
    current_value: float
    initial_cost_basis: float | None = None
    annual_gain_rate: float | None = None
    monthly_contribution: float = 0.0
    active: bool = True
    bav_strategy: BAVStrategy = BAVStrategy.TRANSFER
    bav_retirement_age: int = 67
    bav_transfer_etf_ratio: float = 0.5
    inheritance_gross_amount: float = 0.0
    inheritance_age: int = 67
    inheritance_relationship: InheritanceRelationship = (
        InheritanceRelationship.KIND
    )

    def effective_cost_basis(self) -> float:
        """Return the starting cost basis for this asset.

        Returns:
            Starting cost basis as a float.
        """
        return (
            self.initial_cost_basis
            if self.initial_cost_basis is not None
            else self.current_value
        )

    def effective_annual_gain_rate(self) -> float:
        """Return the annual gain rate, falling back to defaults.

        Returns:
            Annual gain rate as a decimal fraction.
        """
        if self.annual_gain_rate is None:
            return DEFAULT_ANNUAL_GAIN_RATES[self.asset_type]
        return self.annual_gain_rate


@dataclass(frozen=True)
class StatePension:
    """State pension configuration.

    Attributes:
        current_monthly_amount: Current gross monthly state pension value in
            today's currency.
        monthly_growth_per_working_year: Additional gross monthly pension earned
            per year the user keeps working until retirement.
        start_age: Age (years) when state pension starts, between 63 and 67.
        tax_rate: Optional flat tax rate applied to monthly state pension. When
            omitted, the configured default is used.
    """

    current_monthly_amount: float = 0.0
    monthly_growth_per_working_year: float = 0.0
    start_age: int = 67
    tax_rate: float | None = None


@dataclass(frozen=True)
class WithdrawalPlan:
    """Withdrawal configuration for retirement.

    Attributes:
        monthly_withdrawal: Amount withdrawn each month after retirement.
        allocation_strategy: Strategy for allocating withdrawals.
        state_pension: Optional state pension inputs.
    """

    monthly_withdrawal: float = 0.0
    allocation_strategy: AllocationStrategy = AllocationStrategy.PROPORTIONAL
    state_pension: StatePension | None = None

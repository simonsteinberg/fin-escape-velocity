"""Domain models for the wealth forecast app."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AssetType(StrEnum):
    """Enum for supported asset categories."""

    ETF = "ETF"
    BAV = "bAV"
    CASH = "Cash"


DEFAULT_ANNUAL_GAIN_RATES: dict[AssetType, float] = {
    AssetType.ETF: 0.05,
    AssetType.BAV: 0.02,
    AssetType.CASH: 0.005,
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
    """

    current_age_years: int
    current_age_months: int = 0
    retirement_age: int = 67
    end_age: int = 100
    currency: str = "EUR"
    average_inflation_rate: float = 0.02


@dataclass(frozen=True)
class Asset:
    """Asset definition and cashflow inputs.

    Attributes:
        name: Display name for the asset.
        asset_type: Asset category used for default gain rates.
        current_value: Starting balance for the asset.
        initial_cost_basis: Optional cost basis at forecast start.
        annual_gain_rate: Optional annual gain rate override.
        monthly_contribution: Monthly contribution before retirement.
    """

    name: str
    asset_type: AssetType
    current_value: float
    initial_cost_basis: float | None = None
    annual_gain_rate: float | None = None
    monthly_contribution: float = 0.0

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
class WithdrawalPlan:
    """Withdrawal configuration for retirement.

    Attributes:
        monthly_withdrawal: Amount withdrawn each month after retirement.
        allocation_strategy: Strategy for allocating withdrawals.
    """

    monthly_withdrawal: float = 0.0
    allocation_strategy: str = "proportional"

"""Console entrypoint for wealth forecasts."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from finev.forecast import forecast_wealth
from finev.models import (
    Asset,
    AssetType,
    BAVStrategy,
    UserProfile,
    WithdrawalPlan,
)


def build_default_profile() -> UserProfile:
    """Build the default profile used by the CLI task.

    Returns:
        Default user profile.
    """
    return UserProfile(
        current_age_years=40,
        current_age_months=0,
        retirement_age=67,
        end_age=100,
        currency="EUR",
        average_inflation_rate=0.02,
    )


def build_default_assets() -> list[Asset]:
    """Build the default asset list used by the CLI task.

    Returns:
        List of default assets.
    """
    return [
        Asset(
            name="ETF MSCI World",
            asset_type=AssetType.ETF,
            current_value=100_000.0,
            monthly_contribution=500.0,
        ),
        Asset(
            name="bAV",
            asset_type=AssetType.BAV,
            current_value=20_000.0,
            monthly_contribution=100.0,
            bav_strategy=BAVStrategy.TRANSFER,
            bav_transfer_start_age=67,
            bav_transfer_end_age=72,
            bav_transfer_etf_ratio=0.5,
        ),
        Asset(
            name="Daily account",
            asset_type=AssetType.CASH,
            current_value=50_000.0,
            monthly_contribution=0.0,
        ),
    ]


def build_default_withdrawal() -> WithdrawalPlan:
    """Build the default withdrawal plan used by the CLI task.

    Returns:
        Default withdrawal plan.
    """
    return WithdrawalPlan(monthly_withdrawal=3000.0)


def summarize_yearly(df: pd.DataFrame, asset_names: list[str]) -> pd.DataFrame:
    """Reduce a monthly forecast to one row per age-year.

    Args:
        df: Monthly forecast dataframe.
        asset_names: Asset columns to keep as end-of-year balances.

    Returns:
        DataFrame containing yearly balances and summed cashflows.
    """
    aggregation: dict[str, str] = {
        "total": "last",
        "net_cashflow": "sum",
        "taxes": "sum",
    }
    for name in asset_names:
        aggregation[name] = "last"

    yearly = df.groupby("age_years", as_index=False).agg(aggregation)
    return yearly.sort_values("age_years")


def print_yearly_summary(
    df: pd.DataFrame,
    assets: Iterable[Asset],
    currency: str,
) -> None:
    """Print yearly totals for each asset and the portfolio.

    Args:
        df: Monthly forecast dataframe.
        assets: Assets to include in the output.
        currency: Currency string to display.
    """
    asset_names = [asset.name for asset in assets]
    summary_columns = ["total", "taxes", "net_cashflow"]
    columns = ["Age", *asset_names, *summary_columns]
    widths = {"Age": 6}
    for name in [*asset_names, *summary_columns]:
        widths[name] = max(len(name), 14)

    header = " ".join(f"{name:>{widths[name]}}" for name in columns)
    print(header)
    print("-" * len(header))

    for _, row in df.iterrows():
        age_value = f"{int(row['age_years'])}"
        values = [age_value]
        for name in asset_names:
            values.append(f"{row[name]:,.0f} {currency}")
        values.append(f"{row['total']:,.0f} {currency}")
        values.append(f"{row['taxes']:,.0f} {currency}")
        values.append(f"{row['net_cashflow']:+,.0f} {currency}")
        line_parts = [f"{values[0]:>{widths['Age']}}"]
        for name, value in zip(
            [*asset_names, *summary_columns],
            values[1:],
            strict=True,
        ):
            line_parts.append(f"{value:>{widths[name]}}")
        print(" ".join(line_parts))


def run() -> None:
    """Run a default forecast and print yearly totals."""
    profile = build_default_profile()
    assets = build_default_assets()
    withdrawal = build_default_withdrawal()
    forecast = forecast_wealth(
        profile=profile, assets=assets, withdrawal=withdrawal
    )
    asset_names = [asset.name for asset in assets]
    yearly = summarize_yearly(forecast, asset_names=asset_names)
    print_yearly_summary(yearly, assets=assets, currency=profile.currency)


if __name__ == "__main__":
    run()

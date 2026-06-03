"""Pure DRV state-pension estimates shown in the UI.

These helpers translate user inputs and configured DRV parameters into the
read-only state-pension figures displayed in the UI. They contain no I/O and no
UI code, so they can be unit-tested in isolation.

The forecast engine computes the *net* pension actually used to offset
withdrawals in :func:`finev.forecast._net_state_pension_for_month`; the functions
here produce the **display-only** estimates the design doc calls for.
"""

from __future__ import annotations

from finev.config import DrvConfig

# Statutory full-pension reference age (Regelaltersgrenze) used as the baseline
# for early-retirement reductions.
FULL_PENSION_AGE = 67


def estimate_monthly_growth_per_working_year(
    annual_income: float,
    drv: DrvConfig,
) -> float:
    """Estimate the extra monthly gross pension earned per additional working year.

    The estimate converts annual income into DRV pension points (capped at the
    configured maximum) and multiplies by the euro value of one pension point.

    Args:
        annual_income: User's gross annual income in euros.
        drv: Configured DRV parameters.

    Returns:
        Additional gross monthly pension earned per working year, in euros.
        Returns ``0.0`` for non-positive income.
    """
    if annual_income <= 0:
        return 0.0
    points_per_year = min(
        annual_income / drv.durchschnitts_jahresentgelt_euro,
        drv.maximale_rentenpunkte_pro_jahr,
    )
    return points_per_year * drv.rente_pro_rentenpunkt_euro


def early_retirement_penalty_fraction(
    pension_start_age: int,
    drv: DrvConfig,
) -> float:
    """Return the early-retirement reduction fraction for a pension start age.

    Args:
        pension_start_age: Age (years) at which the state pension starts.
        drv: Configured DRV parameters.

    Returns:
        Reduction as a decimal fraction (e.g. ``0.072`` for a 7.2 % cut). Zero
        when the start age is at or after the full-pension age.
    """
    years_early = max(0, FULL_PENSION_AGE - pension_start_age)
    return drv.rentenabschlag_pro_jahr * years_early


def estimate_pension_at_start(
    current_monthly_amount: float,
    monthly_growth_per_working_year: float,
    years_until_retirement: int,
    penalty_fraction: float,
) -> float:
    """Estimate the net monthly pension at the chosen start age (display-only).

    Args:
        current_monthly_amount: Today's gross monthly pension if the user stopped
            working now.
        monthly_growth_per_working_year: Extra gross monthly pension per working
            year (see :func:`estimate_monthly_growth_per_working_year`).
        years_until_retirement: Whole years the user keeps working until
            retirement.
        penalty_fraction: Early-retirement reduction fraction (see
            :func:`early_retirement_penalty_fraction`).

    Returns:
        Estimated net monthly pension at the start age, in euros.
    """
    base_pension = (
        current_monthly_amount
        + monthly_growth_per_working_year * max(years_until_retirement, 0)
    )
    return base_pension * (1 - penalty_fraction)

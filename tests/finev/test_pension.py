"""Unit tests for the pure DRV state-pension estimate helpers."""

from __future__ import annotations

import pytest

from finev.config import DrvConfig
from finev.pension import (
    early_retirement_penalty_fraction,
    estimate_monthly_growth_per_working_year,
    estimate_pension_at_start,
)


def _drv() -> DrvConfig:
    """Return a DrvConfig with simple round numbers for assertions."""
    return DrvConfig(
        rentenabschlag_pro_jahr=0.036,
        rente_pro_rentenpunkt_euro=40.0,
        durchschnitts_jahresentgelt_euro=50_000.0,
        maximale_rentenpunkte_pro_jahr=2.0,
        brutto_rente_steuersatz=0.16,
    )


def test_growth_is_zero_for_non_positive_income() -> None:
    assert estimate_monthly_growth_per_working_year(0.0, _drv()) == 0.0
    assert estimate_monthly_growth_per_working_year(-1000.0, _drv()) == 0.0


def test_growth_scales_with_income_below_cap() -> None:
    # 25 000 / 50 000 = 0.5 points/year * 40 €/point = 20 €/month.
    assert estimate_monthly_growth_per_working_year(25_000.0, _drv()) == 20.0


def test_growth_is_capped_at_max_points() -> None:
    # Income implies 4 points/year but the cap is 2.0 -> 2.0 * 40 = 80 €.
    assert estimate_monthly_growth_per_working_year(200_000.0, _drv()) == 80.0


def test_penalty_is_zero_at_or_after_full_pension_age() -> None:
    assert early_retirement_penalty_fraction(67, _drv()) == 0.0
    assert early_retirement_penalty_fraction(70, _drv()) == 0.0


def test_penalty_grows_with_years_early() -> None:
    # 4 years early * 3.6 % = 14.4 %.
    assert early_retirement_penalty_fraction(63, _drv()) == pytest.approx(
        0.144
    )


def test_pension_at_start_applies_growth_and_penalty() -> None:
    # (1000 + 20 * 10) * (1 - 0.1) = 1200 * 0.9 = 1080.
    result = estimate_pension_at_start(
        current_monthly_amount=1000.0,
        monthly_growth_per_working_year=20.0,
        years_until_retirement=10,
        penalty_fraction=0.1,
    )
    assert result == pytest.approx(1080.0)


def test_pension_at_start_clamps_negative_years() -> None:
    # Negative working years must not reduce the base pension.
    result = estimate_pension_at_start(
        current_monthly_amount=1000.0,
        monthly_growth_per_working_year=20.0,
        years_until_retirement=-5,
        penalty_fraction=0.0,
    )
    assert result == pytest.approx(1000.0)

"""Unit tests for the _WealthPage controller's event handlers.

These exercise the interactive handlers (which a server-side page render does not
trigger) by constructing the controller and calling the handler methods directly,
with the widget-bound refresh methods stubbed out.
"""

from __future__ import annotations

from typing import Any

import pytest

from finev.models import Asset, AssetType, BAVStrategy
from finev.ui import _WealthPage
from finev.ui_state import default_gain_pct


class _Recorder:
    """Captures which refresh methods a handler invoked."""

    def __init__(self) -> None:
        self.calls: list[Any] = []


@pytest.fixture
def page(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> _WealthPage:
    # Point state at a nonexistent file so the controller loads defaults and
    # never touches the repo's real cache.
    monkeypatch.setenv("WEALTH_APP_STATE_PATH", str(tmp_path / "missing.json"))
    controller = _WealthPage()
    recorder = _Recorder()
    monkeypatch.setattr(
        controller,
        "render_asset_rows",
        lambda: recorder.calls.append("render"),
    )
    monkeypatch.setattr(
        controller,
        "run_immediate",
        lambda rebuild_assets=False: recorder.calls.append(
            ("immediate", rebuild_assets)
        ),
    )
    monkeypatch.setattr(
        controller,
        "schedule_forecast",
        lambda rebuild_assets=False: recorder.calls.append(
            ("schedule", rebuild_assets)
        ),
    )
    monkeypatch.setattr(
        controller, "run_forecast", lambda: recorder.calls.append("forecast")
    )
    # Expose the recorder for assertions.
    controller.calls = recorder.calls  # type: ignore[attr-defined]
    return controller


def _calls(page: _WealthPage) -> list[Any]:
    return page.calls  # type: ignore[attr-defined]


def test_loads_default_rows(page: _WealthPage) -> None:
    names = [row["name"] for row in page.asset_rows]
    assert names == ["ETF MSCI World", "bAV", "Daily account"]


def test_simple_field_edit_debounces_without_rerender(
    page: _WealthPage,
) -> None:
    page.update_asset_row(0, "monthly_contribution", 999)
    assert page.asset_rows[0]["monthly_contribution"] == 999
    assert _calls(page) == [("schedule", False)]


def test_current_value_edit_clamps_gains_and_rebuilds(
    page: _WealthPage,
) -> None:
    page.asset_rows[0]["unrealized_gains"] = 80_000.0
    page.update_asset_row(0, "current_value", 5_000)
    assert page.asset_rows[0]["current_value"] == 5_000
    # Unrealized gains cannot exceed the new current value.
    assert page.asset_rows[0]["unrealized_gains"] == 5_000
    assert _calls(page) == [("schedule", True)]


def test_type_change_rerenders_and_updates_default_rate(
    page: _WealthPage,
) -> None:
    page.update_asset_row(0, "type", AssetType.CASH.value)
    assert page.asset_rows[0]["type"] == AssetType.CASH.value
    assert page.asset_rows[0]["annual_gain_rate_pct"] == default_gain_pct(
        AssetType.CASH
    )
    assert _calls(page) == ["render", ("immediate", False)]


def test_invalid_enum_value_is_coerced(page: _WealthPage) -> None:
    page.update_asset_row(0, "bav_strategy", "bogus")
    assert page.asset_rows[0]["bav_strategy"] == BAVStrategy.TRANSFER.value
    assert _calls(page) == ["render", ("immediate", False)]


def test_add_asset_row_appends_and_refreshes(page: _WealthPage) -> None:
    before = len(page.asset_rows)
    page.add_asset_row()
    assert len(page.asset_rows) == before + 1
    assert page.asset_rows[-1]["name"] == "New asset"
    assert _calls(page) == ["render", ("immediate", False)]


def test_remove_asset_row_drops_and_refreshes(page: _WealthPage) -> None:
    before = len(page.asset_rows)
    page.remove_asset_row(1)
    assert len(page.asset_rows) == before - 1
    assert [row["name"] for row in page.asset_rows] == [
        "ETF MSCI World",
        "Daily account",
    ]
    assert _calls(page) == ["render", ("immediate", False)]


def test_build_assets_converts_every_row(page: _WealthPage) -> None:
    assets = page.build_assets()
    assert len(assets) == len(page.asset_rows)
    assert all(isinstance(asset, Asset) for asset in assets)
    assert [asset.name for asset in assets] == [
        row["name"] for row in page.asset_rows
    ]


class _FakeWidget:
    """Minimal stand-in for a NiceGUI input/label during reset tests."""

    def __init__(self) -> None:
        self.value: Any = None
        self.text: str = ""

    def update(self) -> None:
        """No-op to match the NiceGUI widget API."""


def test_reset_state_restores_defaults_and_clears_cache(
    page: _WealthPage, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Give every widget attribute a fake so reset_state can assign to them.
    for name in (
        "current_age_years",
        "current_age_months",
        "retirement_age",
        "end_age",
        "currency",
        "average_inflation_rate",
        "withdrawal_input",
        "annual_income",
        "state_pension_current_monthly_amount",
        "state_pension_growth_display",
        "state_pension_penalty_display",
        "state_pension_achieved_display",
        "state_pension_start_age",
    ):
        setattr(page, name, _FakeWidget())
    cleared: list[bool] = []
    monkeypatch.setattr(
        "finev.ui._clear_cached_state", lambda: cleared.append(True)
    )

    # Mutate state, then reset.
    page.add_asset_row()
    page.reset_state()

    assert [row["name"] for row in page.asset_rows] == [
        "ETF MSCI World",
        "bAV",
        "Daily account",
    ]
    assert page.suppress_cache_save is False
    assert cleared == [True]
    assert page.current_age_years.value == 40

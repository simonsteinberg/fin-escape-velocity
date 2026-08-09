"""Unit tests for the _WealthPage controller's event handlers.

These exercise the interactive handlers (which a server-side page render does not
trigger) by constructing the controller and calling the handler methods directly,
with the widget-bound refresh methods stubbed out.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import finev.ui as ui_module
from finev.models import Asset, AssetType, BAVStrategy
from finev.ui import _WealthPage
from finev.ui_config import ColorScheme
from finev.ui_state import default_gain_pct


class _DummyDarkMode:
    """Stand-in for ``ui.dark_mode`` capturing the assigned value."""

    def __init__(self) -> None:
        self.value: bool | None = None

    def update(self) -> None:
        pass


class _DummyButton:
    """Stand-in for the navbar toggle capturing ``props``/``update`` calls."""

    def __init__(self) -> None:
        self.props_calls: list[str] = []

    def props(self, value: str) -> _DummyButton:
        self.props_calls.append(value)
        return self

    def update(self) -> None:
        pass


class _Recorder:
    """Captures which refresh methods a handler invoked."""

    def __init__(self) -> None:
        self.calls: list[Any] = []


@pytest.fixture
def page(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> _WealthPage:
    # Point state at a nonexistent file so the controller loads defaults and
    # never touches the repo's real cache, and isolate the profiles directory.
    monkeypatch.setenv("WEALTH_APP_STATE_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setenv("WEALTH_APP_PROFILES_DIR", str(tmp_path / "profiles"))
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


def test_simple_field_edit_reruns_without_rerender(
    page: _WealthPage,
) -> None:
    # A committed text edit re-runs the forecast immediately (commits arrive on
    # Enter/blur, so there is nothing to debounce) without rebuilding the rows.
    page.update_asset_row(0, "monthly_contribution", 999)
    assert page.asset_rows[0]["monthly_contribution"] == 999
    assert _calls(page) == [("immediate", False)]


def test_current_value_edit_clamps_gains_and_rebuilds(
    page: _WealthPage,
) -> None:
    page.asset_rows[0]["unrealized_gains"] = 80_000.0
    page.update_asset_row(0, "current_value", 5_000)
    assert page.asset_rows[0]["current_value"] == 5_000
    # Unrealized gains cannot exceed the new current value.
    assert page.asset_rows[0]["unrealized_gains"] == 5_000
    # current_value commit rebuilds the rows (to re-clamp the gains field).
    assert _calls(page) == [("immediate", True)]


class _OnWidget:
    """Fake NiceGUI input recording ``.on`` registrations and exposing value."""

    def __init__(self, value: Any = None) -> None:
        self.value: Any = value
        self.handlers: dict[str, Any] = {}

    def on(self, event: str, handler: Any) -> _OnWidget:
        self.handlers[event] = handler
        return self


def test_commit_on_enter_wires_enter_blur_and_change_to_current_value() -> (
    None
):
    widget = _OnWidget(value=123)
    committed: list[Any] = []

    returned = ui_module._commit_on_enter(widget, committed.append)

    # The widget is returned for chaining and all three commit events are wired.
    assert returned is widget
    assert set(widget.handlers) == {"keydown.enter", "blur", "change"}
    # Firing any event commits the widget's value as read at fire time (the
    # value is synced live, so the latest typed text is always picked up).
    widget.value = 456
    widget.handlers["keydown.enter"]()
    widget.handlers["blur"]()
    widget.handlers["change"]()
    assert committed == [456, 456, 456]


def test_commit_profile_edit_reruns_immediately(page: _WealthPage) -> None:
    # Committing a profile/withdrawal text field re-runs the forecast now,
    # without rebuilding the asset rows.
    page._commit_profile_edit("ignored")
    assert _calls(page) == [("immediate", False)]


def test_cycle_color_scheme_advances_persists_and_updates_widgets(
    page: _WealthPage, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved: list[dict[str, Any]] = []
    monkeypatch.setattr(ui_module, "_save_cached_state", saved.append)
    # The snapshot reads many bound widgets that the unit fixture never builds;
    # stub it so the test exercises the scheme handler in isolation.
    monkeypatch.setattr(
        page,
        "_state_snapshot",
        lambda: {"color_scheme": page.color_scheme.value},
    )
    page.dark_mode = _DummyDarkMode()  # type: ignore[assignment]
    page.color_scheme_button = _DummyButton()  # type: ignore[assignment]
    page.color_scheme = ColorScheme.AUTO

    page.cycle_color_scheme()

    # auto → light: dark mode disabled, icon updated, choice persisted.
    assert page.color_scheme is ColorScheme.LIGHT
    assert page.dark_mode.value is False
    assert page.color_scheme_button.props_calls == ["icon=light_mode"]
    assert saved == [{"color_scheme": "light"}]


def test_set_color_scheme_to_dark_enables_dark_mode(
    page: _WealthPage, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ui_module, "_save_cached_state", lambda _state: None)
    monkeypatch.setattr(page, "_state_snapshot", dict)
    page.dark_mode = _DummyDarkMode()  # type: ignore[assignment]
    page.color_scheme_button = _DummyButton()  # type: ignore[assignment]

    page.set_color_scheme(ColorScheme.DARK)

    assert page.color_scheme is ColorScheme.DARK
    assert page.dark_mode.value is True


def test_type_change_rerenders_and_updates_default_rate(
    page: _WealthPage,
) -> None:
    page.update_asset_row(0, "type", AssetType.CASH.value)
    assert page.asset_rows[0]["type"] == AssetType.CASH.value
    assert page.asset_rows[0]["annual_gain_rate_pct"] == default_gain_pct(
        AssetType.CASH
    )
    assert _calls(page) == ["render", ("immediate", False)]


def test_change_to_vbl_fills_defaults_and_rerenders(
    page: _WealthPage,
) -> None:
    page.update_asset_row(0, "type", AssetType.VBL_KLASSIK.value)
    assert page.asset_rows[0]["type"] == AssetType.VBL_KLASSIK.value
    assert page.asset_rows[0]["vbl_input_mode"] == "points"
    assert page.asset_rows[0]["vbl_start_age"] == 67
    assert _calls(page) == ["render", ("immediate", False)]


def test_toggle_vbl_still_working_rerenders(page: _WealthPage) -> None:
    page.update_asset_row(0, "type", AssetType.VBL_KLASSIK.value)
    page.update_asset_row(0, "vbl_still_working", True)
    assert page.asset_rows[0]["vbl_still_working"] is True
    # Both the type change and the checkbox toggle force a rerender.
    assert _calls(page) == [
        "render",
        ("immediate", False),
        "render",
        ("immediate", False),
    ]


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
    """Minimal stand-in for a NiceGUI input/label/select during tests."""

    def __init__(self, value: Any = None) -> None:
        self.value: Any = value
        self.text: str = ""
        self.options: Any = None

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
        "debt_interest_rate",
        "withdrawal_input",
        "annual_income",
        "state_pension_current_monthly_amount",
        "state_pension_growth_display",
        "state_pension_penalty_display",
        "state_pension_achieved_display",
        "state_pension_start_age",
        "state_pension_adjustment_rate",
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


_WIDGET_NAMES = (
    "current_age_years",
    "current_age_months",
    "retirement_age",
    "end_age",
    "currency",
    "average_inflation_rate",
    "debt_interest_rate",
    "withdrawal_input",
    "annual_income",
    "state_pension_current_monthly_amount",
    "state_pension_growth_display",
    "state_pension_penalty_display",
    "state_pension_achieved_display",
    "state_pension_start_age",
    "state_pension_adjustment_rate",
)


def _wire_widgets(page: _WealthPage) -> None:
    """Give the controller fake widgets so handlers can read/write them."""
    for name in _WIDGET_NAMES:
        setattr(page, name, _FakeWidget())
    page.profile_name_input = _FakeWidget()  # type: ignore[assignment]
    page.profile_select = _FakeWidget()  # type: ignore[assignment]


@pytest.fixture
def notifications(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Any]]:
    """Capture ui.notify calls instead of requiring a live client."""
    records: list[tuple[str, Any]] = []
    monkeypatch.setattr(
        "finev.ui.ui.notify",
        lambda message, **kwargs: records.append(
            (message, kwargs.get("type"))
        ),
    )
    return records


def test_save_profile_persists_snapshot_and_refreshes_select(
    page: _WealthPage,
    monkeypatch: pytest.MonkeyPatch,
    notifications: list[tuple[str, Any]],
) -> None:
    _wire_widgets(page)
    page.profile_name_input.value = "My Wife"
    monkeypatch.setattr(page, "_state_snapshot", lambda: {"marker": 1})

    page.save_profile()

    assert page.profile_store.load_profile("my-wife") == {"marker": 1}
    assert page.profile_select.options == ["my-wife"]
    assert page.profile_select.value == "my-wife"
    assert notifications[-1] == ("Saved profile 'my-wife'.", "positive")


def test_save_profile_rejects_blank_name(
    page: _WealthPage, notifications: list[tuple[str, Any]]
) -> None:
    _wire_widgets(page)
    page.profile_name_input.value = "   "

    page.save_profile()

    assert page.profile_store.list_profiles() == []
    assert notifications[-1][1] == "warning"


def test_load_profile_applies_saved_state(
    page: _WealthPage, notifications: list[tuple[str, Any]]
) -> None:
    _wire_widgets(page)
    page.profile_store.save_profile(
        "wife",
        {"profile": {"current_age_years": 55, "currency": "USD"}},
    )
    page.profile_select.value = "wife"

    page.load_profile()

    assert page.current_age_years.value == 55
    assert page.currency.value == "USD"
    # No asset list in the profile falls back to the default rows; the page
    # re-renders and re-runs immediately.
    assert [row["name"] for row in page.asset_rows] == [
        "ETF MSCI World",
        "bAV",
        "Daily account",
    ]
    assert "render" in _calls(page)
    assert ("immediate", False) in _calls(page)
    assert notifications[-1] == ("Loaded profile 'wife'.", "positive")


def test_load_profile_without_selection_warns(
    page: _WealthPage, notifications: list[tuple[str, Any]]
) -> None:
    _wire_widgets(page)
    page.profile_select.value = None

    page.load_profile()

    assert notifications[-1][1] == "warning"


def test_delete_profile_removes_and_refreshes(
    page: _WealthPage, notifications: list[tuple[str, Any]]
) -> None:
    _wire_widgets(page)
    page.profile_store.save_profile("wife", {})
    page.profile_store.save_profile("child", {})
    page.profile_select.value = "wife"

    page.delete_profile()

    assert page.profile_store.list_profiles() == ["child"]
    assert page.profile_select.options == ["child"]
    assert notifications[-1] == ("Deleted profile 'wife'.", "positive")


class _FakeDialog:
    """Minimal stand-in for a NiceGUI dialog during tests."""

    def __init__(self) -> None:
        self.opened = 0

    def open(self) -> None:
        """Record that the dialog was opened."""
        self.opened += 1


def test_open_file_dialog_refreshes_options_and_opens(
    page: _WealthPage,
) -> None:
    _wire_widgets(page)
    page.profile_store.save_profile("wife", {})
    dialog = _FakeDialog()
    page.file_dialog = dialog  # type: ignore[assignment]

    page.open_file_dialog()

    # The saved-profiles list is refreshed from the store before opening.
    assert page.profile_select.options == ["wife"]
    assert dialog.opened == 1


def _wire_valid_profile(page: _WealthPage) -> None:
    """Wire fake widgets and populate a forecastable profile/withdrawal."""
    _wire_widgets(page)
    page.current_age_years.value = 40
    page.current_age_months.value = 0
    page.retirement_age.value = 67
    page.end_age.value = 100
    page.currency.value = "EUR"
    page.average_inflation_rate.value = 2.0
    page.debt_interest_rate.value = 5.0
    page.withdrawal_input.value = 3000
    page.annual_income.value = 50000
    page.state_pension_current_monthly_amount.value = 0
    page.state_pension_start_age.value = 67


def test_export_forecast_csv_downloads_detailed_csv(
    page: _WealthPage, monkeypatch: pytest.MonkeyPatch
) -> None:
    _wire_valid_profile(page)
    downloads: list[tuple[Any, Any, Any]] = []
    monkeypatch.setattr(
        "finev.ui.ui.download.content",
        lambda content, filename=None, media_type="": downloads.append(
            (content, filename, media_type)
        ),
    )

    page.export_forecast_csv()

    assert len(downloads) == 1
    content, filename, media_type = downloads[0]
    assert media_type == "text/csv"
    assert filename.startswith("wealth-forecast-") and filename.endswith(
        ".csv"
    )
    header = content.splitlines()[0]
    # Detailed export: monthly granularity columns plus every asset and total.
    assert "month_index" in header
    assert "total" in header
    for name in ("ETF MSCI World", "bAV", "Daily account"):
        assert name in header
    # Full monthly detail (age 40→100 inclusive) far exceeds the yearly view.
    assert len(content.strip().splitlines()) > 12 * 60


def test_export_forecast_csv_notifies_on_invalid_inputs(
    page: _WealthPage,
    monkeypatch: pytest.MonkeyPatch,
    notifications: list[tuple[str, Any]],
) -> None:
    _wire_widgets(page)  # all-zero profile fails forecast validation
    downloads: list[Any] = []
    monkeypatch.setattr(
        "finev.ui.ui.download.content",
        lambda *args, **kwargs: downloads.append(args),
    )

    page.export_forecast_csv()

    # No download is emitted; the error surfaces as a negative notification.
    assert downloads == []
    assert notifications[-1][1] == "negative"


def test_controller_defaults_to_english(page: _WealthPage) -> None:
    assert page.language == "en"
    assert page.t("nav.file") == "File"


def test_set_language_switches_translator_persists_and_reloads(
    page: _WealthPage,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wire_widgets(page)
    reloads: list[bool] = []
    monkeypatch.setattr(
        "finev.ui.ui.navigate.reload", lambda: reloads.append(True)
    )

    page.set_language("de")

    # The translator now resolves to German and the choice is persisted so a
    # reload restores it.
    assert page.language == "de"
    assert page.t("nav.file") == "Datei"
    assert reloads == [True]
    persisted = json.loads((tmp_path / "missing.json").read_text())
    assert persisted["language"] == "de"


def test_set_language_to_current_is_a_noop(
    page: _WealthPage, monkeypatch: pytest.MonkeyPatch
) -> None:
    reloads: list[bool] = []
    monkeypatch.setattr(
        "finev.ui.ui.navigate.reload", lambda: reloads.append(True)
    )

    page.set_language("en")

    # Selecting the active language neither persists nor reloads.
    assert page.language == "en"
    assert reloads == []


def test_tooltip_show_delay_is_configured() -> None:
    # Importing finev.ui applies the class-level hover-show delay to every
    # tooltip (re-applied here so the test is order-independent).
    from nicegui import ui as nicegui_ui

    ui_module._apply_tooltip_delay()

    assert ui_module._TOOLTIP_DELAY_MS == 1500
    assert nicegui_ui.tooltip._default_props.get("delay") == str(
        ui_module._TOOLTIP_DELAY_MS
    )


def test_help_tip_css_caps_width_with_important() -> None:
    # Quasar's tooltip position engine writes its own inline ``max-width``, so
    # the panel-help width cap only sticks if the stylesheet rule is
    # ``!important`` and targets the help-tip class.
    css = ui_module._help_tip_css()

    assert f".{ui_module._HELP_TIP_CLASS}" in css
    assert f"max-width: {ui_module._HELP_MAX_WIDTH_CH}ch" in css
    assert "!important" in css


def test_change_to_investment_fills_defaults_and_rerenders(
    page: _WealthPage,
) -> None:
    page.update_asset_row(0, "type", AssetType.INVESTMENT.value)
    assert page.asset_rows[0]["type"] == AssetType.INVESTMENT.value
    assert page.asset_rows[0]["investment_kind"] == "one_time"
    assert page.asset_rows[0]["investment_age"] == 67
    assert _calls(page) == ["render", ("immediate", False)]


def test_investment_kind_change_rerenders_row(page: _WealthPage) -> None:
    # Switching to a financed purchase reveals the loan fields, so the row
    # must be rebuilt rather than only re-forecast.
    page.update_asset_row(0, "type", AssetType.INVESTMENT.value)
    page.update_asset_row(0, "investment_kind", "long_term")
    assert page.asset_rows[0]["investment_kind"] == "long_term"
    assert _calls(page)[-2:] == ["render", ("immediate", False)]


def test_notgroschen_toggle_rerenders_row(page: _WealthPage) -> None:
    # The daily-account row (index 2) is the Cash asset in the defaults.
    page.update_asset_row(2, "notgroschen", True)
    assert page.asset_rows[2]["notgroschen"] is True
    assert _calls(page) == ["render", ("immediate", False)]


def test_contribution_growth_edit_only_reforecasts(page: _WealthPage) -> None:
    page.update_asset_row(0, "monthly_contribution_growth_pct", 2.5)
    assert page.asset_rows[0]["monthly_contribution_growth_pct"] == 2.5
    assert _calls(page) == [("immediate", False)]

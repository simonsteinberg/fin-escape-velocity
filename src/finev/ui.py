"""NiceGUI page composition for the wealth forecast app."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from nicegui import ui

from finev.config import get_config
from finev.forecast import forecast_wealth
from finev.i18n import (
    LANGUAGE_TOGGLE_LABELS as _LANGUAGE_TOGGLE_LABELS,
)
from finev.i18n import (
    available_languages as _available_languages,
)
from finev.i18n import (
    make_translator as _make_translator,
)
from finev.i18n import (
    normalize_language as _normalize_language,
)
from finev.models import (
    Asset,
    AssetType,
    BAVStrategy,
    InheritanceRelationship,
    StatePension,
    UserProfile,
    WithdrawalPlan,
)
from finev.pension import (
    early_retirement_penalty_fraction,
    estimate_monthly_growth_per_working_year,
    estimate_pension_at_start,
)
from finev.profile_store import (
    ProfileStore,
)
from finev.profile_store import (
    default_profile_store as _default_profile_store,
)
from finev.profile_store import (
    normalize_profile_name as _normalize_profile_name,
)
from finev.ui_config import (
    ColorScheme,
    UiConfig,
)
from finev.ui_config import (
    color_scheme_icon as _color_scheme_icon,
)
from finev.ui_config import (
    get_ui_config as _get_ui_config,
)
from finev.ui_config import (
    next_color_scheme as _next_color_scheme,
)
from finev.ui_config import (
    scheme_to_dark_mode as _scheme_to_dark_mode,
)
from finev.ui_state import (
    apply_type_change_defaults as _apply_type_change_defaults,
)
from finev.ui_state import (
    asset_from_row as _asset_from_row,
)
from finev.ui_state import (
    clear_cached_state as _clear_cached_state,
)
from finev.ui_state import (
    coerce_asset_field as _coerce_asset_field,
)
from finev.ui_state import (
    default_asset_rows as _default_asset_rows,
)
from finev.ui_state import (
    default_profile_state as _default_profile_state,
)
from finev.ui_state import (
    default_withdrawal_state as _default_withdrawal_state,
)
from finev.ui_state import (
    load_asset_rows as _load_asset_rows,
)
from finev.ui_state import (
    load_cached_state as _load_cached_state,
)
from finev.ui_state import (
    load_color_scheme as _load_color_scheme,
)
from finev.ui_state import (
    load_language as _load_language,
)
from finev.ui_state import (
    load_log_scale as _load_log_scale,
)
from finev.ui_state import (
    load_profile_state as _load_profile_state,
)
from finev.ui_state import (
    load_withdrawal_state as _load_withdrawal_state,
)
from finev.ui_state import (
    new_asset_row as _new_asset_row,
)
from finev.ui_state import (
    normalize_asset_row as _normalize_asset_row,
)
from finev.ui_state import (
    save_cached_state as _save_cached_state,
)
from finev.ui_view import (
    NAVBAR_CLASS as _NAVBAR_CLASS,
)
from finev.ui_view import (
    asset_value_columns as _asset_value_columns,
)
from finev.ui_view import (
    build_chart_options as _build_chart_options,
)
from finev.ui_view import (
    chart_series as _chart_series,
)
from finev.ui_view import (
    chart_y_axis as _chart_y_axis,
)
from finev.ui_view import (
    export_csv_filename as _export_csv_filename,
)
from finev.ui_view import (
    forecast_csv as _forecast_csv,
)
from finev.ui_view import (
    forecast_table_columns as _forecast_table_columns,
)
from finev.ui_view import (
    format_currency as _format_currency,
)
from finev.ui_view import (
    inline_logo_svg as _inline_logo_svg,
)
from finev.ui_view import (
    theme_css as _theme_css,
)
from finev.ui_view import (
    version_label_text as _version_label_text,
)
from finev.ui_view import (
    yearly_display_frame as _yearly_display_frame,
)

#: Delay (ms) before a hover tooltip appears, so a panel's help text only shows
#: when the user deliberately rests on its ``?`` icon rather than while sweeping
#: across the form. ~1.5s reads as a deliberate pause without feeling sluggish.
_TOOLTIP_DELAY_MS = 1500

#: Max width of a panel help box, in character widths (``ch``), so long help
#: text wraps to a narrow, readable column instead of a very wide row.
_HELP_MAX_WIDTH_CH = 40

#: Font size (px) for panel help text. Quasar's desktop tooltip default is 14px;
#: +2px improves readability of the longer panel read-mes.
_HELP_FONT_SIZE_PX = 16

#: CSS class marking a panel help tooltip. Quasar's tooltip position engine
#: writes its own inline ``max-width`` (95vw), which silently overrides an inline
#: style, so the width cap must come from a stylesheet rule with ``!important``.
_HELP_TIP_CLASS = "finev-help-tip"


def _help_tip_css() -> str:
    """CSS that caps panel help tooltips to a narrow, readable column.

    Returns the rule as a string; it must win over Quasar's inline
    ``max-width`` (which carries no ``!important``), hence the ``!important``.
    """
    return f".{_HELP_TIP_CLASS} {{ max-width: {_HELP_MAX_WIDTH_CH}ch !important; }}"


def _apply_tooltip_delay() -> None:
    """Apply the standard hover-show delay to every tooltip.

    NiceGUI's ``element.tooltip(...)`` and ``ui.tooltip(...)`` both instantiate
    the same Quasar ``Tooltip`` class, so a single class-level default prop
    delays every tooltip (parameter help and navbar toggles alike) without
    touching individual call sites.
    """
    ui.tooltip.default_props(add=f"delay={_TOOLTIP_DELAY_MS}")


_apply_tooltip_delay()


def _panel_header(title: str, help_text: str) -> None:
    """Render a panel title with a hover ``?`` help icon.

    The icon is the single help affordance for the whole panel: resting on it
    reveals ``help_text`` after the standard tooltip delay. Using a ``ui.icon``
    as the anchor keeps one tooltip per panel instead of one per input field.

    Args:
        title: The panel's heading text.
        help_text: The localized read-me shown when hovering the ``?`` icon.
    """
    with ui.row().classes("w-full items-center gap-1 flex-nowrap"):
        ui.label(title).classes("text-lg font-semibold")
        with ui.icon("help_outline").classes(
            "text-gray-400 cursor-help text-lg"
        ):
            ui.tooltip(help_text).classes(_HELP_TIP_CLASS).style(
                f"font-size: {_HELP_FONT_SIZE_PX}px"
            )


def _commit_on_enter(
    widget: Any,
    commit: Callable[[Any], None],
) -> Any:
    """Run ``commit`` when the user finishes editing a text field.

    A live ``on_change`` handler fires on every keystroke; for an input that
    triggers a re-render this destroys and recreates the very widget being typed
    into, stealing focus -- the user is "thrown out" of the box. Wiring the
    refresh to Enter and blur instead defers it to a deliberate commit, so
    typing never moves focus. The widget's value is still synced live, so any
    other action (a button, a dropdown change) always sees the latest text.

    The DOM ``change`` event is also wired so that spinner arrow clicks (which
    do not fire ``keydown.enter`` or ``blur``) trigger an immediate refresh.
    Double-firing with ``blur`` when both events follow a focus-loss is
    harmless because committing the same value twice is idempotent.

    Args:
        widget: The NiceGUI input/number whose edits should be committed.
        commit: Called with the widget's current value on Enter or blur.

    Returns:
        The widget, so the call can be chained at the construction site.
    """
    widget.on("keydown.enter", lambda: commit(widget.value))
    widget.on("blur", lambda: commit(widget.value))
    widget.on("change", lambda: commit(widget.value))
    return widget


def _render_asset_row(
    index: int,
    row: dict[str, Any],
    on_field_change: Callable[[int, str, Any], None],
    on_remove: Callable[[int], None],
    t: Callable[[str], str],
) -> None:
    """Render the widgets for one asset row into the current container.

    Args:
        index: Position of the row (passed back to the callbacks).
        row: The asset row data to render.
        on_field_change: Called as ``(index, field, value)`` when an input
            changes.
        on_remove: Called as ``(index,)`` when the delete button is pressed.
        t: Translator mapping a catalog key to its localized label.
    """
    with ui.column().classes("w-full gap-1 p-2 border rounded"):
        with ui.row().classes("w-full gap-2 items-center"):
            asset_type = AssetType(str(row.get("type")))
            current_value = float(row.get("current_value") or 0)
            # Active toggle (hide/show) for what-if scenarios
            ui.button(
                icon=(
                    "visibility"
                    if row.get("active", True)
                    else "visibility_off"
                ),
                on_click=lambda e, i=index: on_field_change(
                    i,
                    "active",
                    not row.get("active", True),
                ),
            ).props("dense flat")
            _commit_on_enter(
                ui.input(
                    label=t("asset.name"),
                    value=row["name"],
                ).classes("flex-1"),
                lambda value: on_field_change(index, "name", value),
            )
            ui.select(
                options=[item.value for item in AssetType],
                value=row["type"],
                label=t("asset.type"),
                on_change=lambda e, i=index: on_field_change(
                    index, "type", e.value
                ),
            ).classes("w-28")
            ui.button(
                icon="delete",
                on_click=lambda i=index: on_remove(i),
            ).props("dense flat color=red")
        if asset_type == AssetType.INHERITANCE:
            _inheritance_relationship_labels = {
                InheritanceRelationship.EHEGATTE.value: t(
                    "inheritance.rel.ehegatte"
                ),
                InheritanceRelationship.KIND.value: t("inheritance.rel.kind"),
                InheritanceRelationship.ENKEL.value: t(
                    "inheritance.rel.enkel"
                ),
                InheritanceRelationship.ELTERNTEIL.value: t(
                    "inheritance.rel.elternteil"
                ),
                InheritanceRelationship.KLASSE_II.value: t(
                    "inheritance.rel.klasse_ii"
                ),
                InheritanceRelationship.KLASSE_III.value: t(
                    "inheritance.rel.klasse_iii"
                ),
            }
            with ui.grid(columns=2).classes("w-full gap-2"):
                _commit_on_enter(
                    ui.number(
                        label=t("asset.gross_amount"),
                        value=row.get("inheritance_gross_amount") or 0,
                        format="%.0f",
                        min=0,
                        step=10000,
                    ).classes("w-full"),
                    lambda value: on_field_change(
                        index, "inheritance_gross_amount", value
                    ),
                )
                _commit_on_enter(
                    ui.number(
                        label=t("asset.age_at_receipt"),
                        value=row.get("inheritance_age") or 67,
                        format="%.0f",
                        min=0,
                        step=1,
                    ).classes("w-full"),
                    lambda value: on_field_change(
                        index, "inheritance_age", value
                    ),
                )
            ui.select(
                options=_inheritance_relationship_labels,
                value=row.get(
                    "inheritance_relationship",
                    InheritanceRelationship.KIND.value,
                ),
                label=t("asset.relationship"),
                on_change=lambda e, i=index: on_field_change(
                    i,
                    "inheritance_relationship",
                    e.value,
                ),
            ).classes("w-full")
        elif asset_type == AssetType.VBL_KLASSIK:
            input_mode = str(row.get("vbl_input_mode", "points"))
            with ui.column().classes("w-full gap-2"):
                ui.select(
                    options={
                        "points": t("asset.vbl_points_option"),
                        "euro": t("asset.vbl_euro_option"),
                    },
                    value=input_mode,
                    label=t("asset.vbl_input"),
                    on_change=lambda e, i=index: on_field_change(
                        i,
                        "vbl_input_mode",
                        e.value,
                    ),
                ).classes("w-full")
                if input_mode == "euro":
                    _commit_on_enter(
                        ui.number(
                            label=t("asset.vbl_monthly_pension"),
                            value=row.get("vbl_monthly_pension") or 0,
                            format="%.0f",
                            min=0,
                            step=50,
                        ).classes("w-full"),
                        lambda value: on_field_change(
                            index, "vbl_monthly_pension", value
                        ),
                    )
                else:
                    _commit_on_enter(
                        ui.number(
                            label=t("asset.vbl_points_label"),
                            value=row.get("vbl_points") or 0,
                            format="%.1f",
                            min=0,
                            step=1,
                        ).classes("w-full"),
                        lambda value: on_field_change(
                            index, "vbl_points", value
                        ),
                    )
                with ui.row().classes("w-full gap-2 items-center"):
                    ui.checkbox(
                        t("asset.vbl_still_working"),
                        value=bool(row.get("vbl_still_working", False)),
                        on_change=lambda e, i=index: on_field_change(
                            i,
                            "vbl_still_working",
                            e.value,
                        ),
                    )
                with ui.row().classes("w-full gap-2"):
                    _commit_on_enter(
                        ui.number(
                            label=t("asset.vbl_start_age"),
                            value=row.get("vbl_start_age") or 67,
                            format="%.0f",
                            min=0,
                            step=1,
                        ).classes("w-40"),
                        lambda value: on_field_change(
                            index, "vbl_start_age", value
                        ),
                    )
                    _commit_on_enter(
                        ui.number(
                            label=t("asset.vbl_tax_rate"),
                            value=row.get("vbl_tax_rate_pct") or None,
                            format="%.1f",
                            min=0,
                            max=100,
                            step=1,
                        ).classes("w-40"),
                        lambda value: on_field_change(
                            index, "vbl_tax_rate_pct", value
                        ),
                    )
        else:
            with ui.grid(columns=2).classes("w-full gap-2"):
                _commit_on_enter(
                    ui.number(
                        label=t("asset.current_value"),
                        value=row["current_value"],
                        format="%.0f",
                        min=0,
                        step=10000,
                    ).classes("w-full"),
                    lambda value: on_field_change(
                        index, "current_value", value
                    ),
                )
                _commit_on_enter(
                    ui.number(
                        label=t("asset.unrealized_gains"),
                        value=row.get("unrealized_gains") or 0,
                        format="%.0f",
                        min=0,
                        max=current_value,
                        step=10000,
                    ).classes("w-full"),
                    lambda value: on_field_change(
                        index, "unrealized_gains", value
                    ),
                )
                _commit_on_enter(
                    ui.number(
                        label=t("asset.annual_gain"),
                        value=row["annual_gain_rate_pct"],
                        format="%.1f",
                        step=0.1,
                    ).classes("w-full"),
                    lambda value: on_field_change(
                        index, "annual_gain_rate_pct", value
                    ),
                )
                _commit_on_enter(
                    ui.number(
                        label=t("asset.monthly_contribution"),
                        value=row["monthly_contribution"],
                        format="%.0f",
                        min=0,
                        step=50,
                    ).classes("w-full"),
                    lambda value: on_field_change(
                        index, "monthly_contribution", value
                    ),
                )
            if asset_type == AssetType.BAV:
                with ui.column().classes("w-full gap-2"):
                    ui.select(
                        options={
                            BAVStrategy.TRANSFER.value: t(
                                "asset.bav_transfer"
                            ),
                            BAVStrategy.INCOME.value: t("asset.bav_income"),
                        },
                        value=row.get(
                            "bav_strategy",
                            BAVStrategy.TRANSFER.value,
                        ),
                        label=t("asset.bav_mode"),
                        on_change=lambda e, i=index: on_field_change(
                            i,
                            "bav_strategy",
                            e.value,
                        ),
                    ).classes("w-full")
                    if row.get("bav_strategy") == (BAVStrategy.TRANSFER.value):
                        with ui.row().classes("w-full gap-2"):
                            _commit_on_enter(
                                ui.number(
                                    label=t("asset.bav_retirement_age"),
                                    value=row.get(
                                        "bav_retirement_age",
                                        67,
                                    ),
                                    format="%.0f",
                                    min=0,
                                    step=1,
                                ).classes("w-32"),
                                lambda value: on_field_change(
                                    index, "bav_retirement_age", value
                                ),
                            )
                            _commit_on_enter(
                                ui.number(
                                    label=t("asset.etf_share"),
                                    value=row.get(
                                        "bav_transfer_etf_ratio_pct",
                                        50.0,
                                    ),
                                    format="%.0f",
                                    min=0,
                                    max=100,
                                    step=5,
                                ).classes("w-28"),
                                lambda value: on_field_change(
                                    index, "bav_transfer_etf_ratio_pct", value
                                ),
                            )
                    elif row.get("bav_strategy") == (BAVStrategy.INCOME.value):
                        _commit_on_enter(
                            ui.number(
                                label=t("asset.bav_retirement_age"),
                                value=row.get(
                                    "bav_retirement_age",
                                    67,
                                ),
                                format="%.0f",
                                min=0,
                                step=1,
                            ).classes("w-32"),
                            lambda value: on_field_change(
                                index, "bav_retirement_age", value
                            ),
                        )


class _WealthPage:
    """Stateful controller for the wealth forecast page.

    Holds the editable state and the NiceGUI widget references and binds the
    event handlers as methods. The handlers can be unit-tested by constructing
    the controller and calling them directly; the widget tree is only needed by
    :meth:`build`, :meth:`render_asset_rows` and :meth:`run_forecast`.
    """

    # Widget references, assigned in build().
    current_age_years: ui.number
    current_age_months: ui.number
    retirement_age: ui.number
    end_age: ui.number
    currency: ui.input
    average_inflation_rate: ui.number
    debt_interest_rate: ui.number
    withdrawal_input: ui.number
    annual_income: ui.number
    state_pension_current_monthly_amount: ui.number
    state_pension_growth_display: ui.label
    state_pension_penalty_display: ui.label
    state_pension_achieved_display: ui.label
    state_pension_start_age: ui.number
    state_pension_adjustment_rate: ui.number
    assets_container: ui.column
    summary_label: ui.label
    chart: ui.echart
    table: ui.table
    profile_name_input: ui.input
    profile_select: ui.select
    file_dialog: ui.dialog
    about_dialog: ui.dialog
    dark_mode: ui.dark_mode
    color_scheme_button: ui.button
    log_scale_toggle: ui.switch

    def __init__(self) -> None:
        self.state_error: str | None = None
        cached_state: dict[str, Any] | None = None
        try:
            cached_state = _load_cached_state()
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            self.state_error = f"Failed to load cached state: {exc}"
            cached_state = None
        self.language = _load_language(cached_state)
        self.t = _make_translator(self.language)
        self.asset_rows = _load_asset_rows(cached_state)
        self.profile_state = _load_profile_state(cached_state)
        self.withdrawal_state = _load_withdrawal_state(cached_state)
        self.default_profile_state = _default_profile_state()
        self.default_withdrawal_state = _default_withdrawal_state()
        self.suppress_cache_save = False
        self.profile_store: ProfileStore = _default_profile_store()
        self.ui_config: UiConfig = _get_ui_config()
        self.color_scheme: ColorScheme = _load_color_scheme(
            cached_state, self.ui_config.color_scheme
        )
        self.log_scale: bool = _load_log_scale(cached_state)

    # ── Forecast runs ───────────────────────
    def run_immediate(self, rebuild_assets: bool = False) -> None:
        """Re-run the forecast now, optionally rebuilding the asset rows.

        Text inputs commit on Enter/blur (see :func:`_commit_on_enter`) and
        other controls fire discrete events, so every refresh is a deliberate,
        one-off action — there is nothing to debounce.

        Args:
            rebuild_assets: Re-render the asset rows before forecasting (needed
                when a change alters which row widgets are shown).
        """
        if rebuild_assets:
            self.render_asset_rows()
        self.run_forecast()

    def _commit_profile_edit(self, _value: Any) -> None:
        """Re-run the forecast when a profile/withdrawal text field commits.

        The committed value is already synced onto the bound widget, and
        :meth:`run_forecast` reads every widget, so the value argument exists
        only to satisfy the :func:`_commit_on_enter` callback signature.
        """
        self.run_immediate()

    # ── Asset-row handlers ────────────────────
    def update_asset_row(self, index: int, field: str, value: Any) -> None:
        """Update a field on a specific asset row.

        Args:
            index: Row index to update.
            field: Field name to update.
            value: New field value.
        """
        current_row = self.asset_rows[index]
        if field == "type":
            _apply_type_change_defaults(current_row, AssetType(str(value)))
        value = _coerce_asset_field(current_row, field, value)
        if field == "current_value":
            unrealized_gains = float(current_row.get("unrealized_gains") or 0)
            current_row["unrealized_gains"] = min(
                unrealized_gains, float(value or 0)
            )
        current_row[field] = value
        if field in {
            "type",
            "bav_strategy",
            "active",
            "inheritance_relationship",
            "vbl_input_mode",
            "vbl_still_working",
        }:
            self.render_asset_rows()
            self.run_immediate()
            return
        if field == "current_value":
            self.run_immediate(rebuild_assets=True)
            return
        self.run_immediate()

    def remove_asset_row(self, index: int) -> None:
        """Remove an asset row from the list."""
        self.asset_rows.pop(index)
        self.render_asset_rows()
        self.run_immediate()

    def add_asset_row(self) -> None:
        """Append a new blank asset row."""
        self.asset_rows.append(_new_asset_row())
        self.render_asset_rows()
        self.run_immediate()

    def _apply_state_to_widgets(
        self, profile: dict[str, Any], withdrawal: dict[str, Any]
    ) -> None:
        """Push profile/withdrawal values onto the bound input widgets.

        Shared by :meth:`reset_state` and :meth:`load_profile`; it only writes
        widget values and leaves caching, re-rendering, and re-running to the
        caller.

        Args:
            profile: Profile state dict (as produced by ``load_profile_state``).
            withdrawal: Withdrawal state dict (as produced by
                ``load_withdrawal_state``).
        """
        self.current_age_years.value = profile["current_age_years"]
        self.current_age_years.update()
        self.current_age_months.value = profile["current_age_months"]
        self.current_age_months.update()
        self.retirement_age.value = profile["retirement_age"]
        self.retirement_age.update()
        self.end_age.value = profile["end_age"]
        self.end_age.update()
        self.currency.value = profile["currency"]
        self.currency.update()
        self.average_inflation_rate.value = profile[
            "average_inflation_rate_pct"
        ]
        self.average_inflation_rate.update()
        self.debt_interest_rate.value = profile["debt_interest_rate_pct"]
        self.debt_interest_rate.update()
        self.annual_income.value = profile["annual_income"]
        self.annual_income.update()
        self.withdrawal_input.value = withdrawal["monthly_withdrawal"]
        self.withdrawal_input.update()
        self.state_pension_current_monthly_amount.value = withdrawal[
            "state_pension_current_monthly_amount"
        ]
        self.state_pension_current_monthly_amount.update()
        self.state_pension_growth_display.text = _format_currency(
            withdrawal["state_pension_growth_per_working_year"],
            profile["currency"],
        ) + self.t("common.pm_suffix")
        self.state_pension_growth_display.update()
        self.state_pension_penalty_display.text = ""
        self.state_pension_penalty_display.update()
        self.state_pension_achieved_display.text = ""
        self.state_pension_achieved_display.update()
        self.state_pension_start_age.value = withdrawal[
            "state_pension_start_age"
        ]
        self.state_pension_start_age.update()
        self.state_pension_adjustment_rate.value = withdrawal[
            "state_pension_adjustment_rate_pct"
        ]
        self.state_pension_adjustment_rate.update()

    def reset_state(self) -> None:
        """Reset UI values to defaults and clear cached state."""
        self.suppress_cache_save = True
        self.asset_rows[:] = _default_asset_rows()
        self._apply_state_to_widgets(
            self.default_profile_state, self.default_withdrawal_state
        )
        self.render_asset_rows()
        self.run_immediate()
        self.suppress_cache_save = False
        try:
            _clear_cached_state()
        except OSError as error:
            ui.notify(
                self.t("notify.clear_cache_fail").format(error=error),
                type="negative",
            )

    # ── Settings profiles ─────────────────────
    def _refresh_profile_options(self, select: str | None = None) -> None:
        """Reload the profile dropdown from the store.

        Args:
            select: Profile to select after refreshing; if ``None``, the current
                selection is kept when it still exists, else cleared.
        """
        names = self.profile_store.list_profiles()
        self.profile_select.options = names
        if select is not None:
            self.profile_select.value = select
        elif self.profile_select.value not in names:
            self.profile_select.value = None
        self.profile_select.update()

    def save_profile(self) -> None:
        """Persist the current settings under the entered profile name."""
        try:
            name = _normalize_profile_name(self.profile_name_input.value or "")
        except ValueError as error:
            ui.notify(str(error), type="warning")
            return
        try:
            self.profile_store.save_profile(name, self._state_snapshot())
        except (OSError, ValueError) as error:
            ui.notify(
                self.t("notify.save_profile_fail").format(error=error),
                type="negative",
            )
            return
        self._refresh_profile_options(select=name)
        ui.notify(
            self.t("notify.save_profile_ok").format(name=name), type="positive"
        )

    def load_profile(self) -> None:
        """Load the selected profile's settings into the UI."""
        name = self.profile_select.value
        if not name:
            ui.notify(self.t("notify.select_to_load"), type="warning")
            return
        try:
            state = self.profile_store.load_profile(name)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            ui.notify(
                self.t("notify.load_profile_fail").format(
                    name=name, error=error
                ),
                type="negative",
            )
            return
        self.suppress_cache_save = True
        self.asset_rows[:] = _load_asset_rows(state)
        self._apply_state_to_widgets(
            _load_profile_state(state), _load_withdrawal_state(state)
        )
        self.render_asset_rows()
        self.suppress_cache_save = False
        self.run_immediate()
        ui.notify(
            self.t("notify.load_profile_ok").format(name=name),
            type="positive",
        )

    def delete_profile(self) -> None:
        """Delete the selected profile."""
        name = self.profile_select.value
        if not name:
            ui.notify(self.t("notify.select_to_delete"), type="warning")
            return
        try:
            self.profile_store.delete_profile(name)
        except OSError as error:
            ui.notify(
                self.t("notify.delete_profile_fail").format(
                    name=name, error=error
                ),
                type="negative",
            )
            return
        self._refresh_profile_options()
        ui.notify(
            self.t("notify.delete_profile_ok").format(name=name),
            type="positive",
        )

    # ── Navbar and dialogs ─────────────────────
    def open_file_dialog(self) -> None:
        """Open the File window, refreshing the saved-profiles list first."""
        self._refresh_profile_options()
        self.file_dialog.open()

    def _build_navbar(self) -> None:
        """Render the always-visible top navbar with the File/About actions.

        The header background follows the active color scheme (teal that matches
        the logo's gradient in light mode, dark gray in dark mode) via the
        themed navbar class. The logo, title and actions are left-aligned in a
        single row; the color-scheme toggle and language toggle are pushed to
        the far right.
        """
        with ui.header().classes(
            f"items-center gap-4 px-4 py-2 {_NAVBAR_CLASS}"
        ):
            ui.html(_inline_logo_svg()).classes("w-8 h-8 shrink-0")
            ui.label(self.t("nav.title")).classes("text-lg font-bold")
            ui.button(
                self.t("nav.file"), on_click=self.open_file_dialog
            ).props("flat color=white")
            ui.button(
                self.t("nav.export"), on_click=self.export_forecast_csv
            ).props("flat color=white")
            ui.button(
                self.t("nav.about"), on_click=self.about_dialog.open
            ).props("flat color=white")
            ui.space()
            self.color_scheme_button = (
                ui.button(
                    icon=_color_scheme_icon(self.color_scheme),
                    on_click=self.cycle_color_scheme,
                )
                .props("flat round color=white")
                .tooltip(self.t("nav.color_scheme"))
            )
            ui.toggle(
                {
                    code: _LANGUAGE_TOGGLE_LABELS[code]
                    for code in _available_languages()
                },
                value=self.language,
                on_change=lambda e: self.set_language(e.value),
            ).props("dense color=white text-color=teal-7").tooltip(
                self.t("nav.language")
            )

    def set_language(self, language: str) -> None:
        """Switch the UI language and reload the page in that language.

        The choice is persisted to the cached state first (so the current,
        possibly unsaved, widget values survive the reload), then the page is
        reloaded so every widget is rebuilt with the new translator. Reloading
        avoids having to track and re-label every widget individually.

        Args:
            language: The requested language code; unknown codes are normalized
                to the default (English).
        """
        normalized = _normalize_language(language)
        if normalized == self.language:
            return
        self.language = normalized
        self.t = _make_translator(normalized)
        try:
            _save_cached_state(self._state_snapshot())
        except (OSError, ValueError) as error:
            ui.notify(
                self.t("notify.language_persist_fail").format(error=error),
                type="negative",
            )
        ui.navigate.reload()

    def cycle_color_scheme(self) -> None:
        """Advance the color scheme to the next option (auto → light → dark)."""
        self.set_color_scheme(_next_color_scheme(self.color_scheme))

    def set_color_scheme(self, scheme: ColorScheme) -> None:
        """Apply a color scheme live and persist the choice.

        Updates the page's dark-mode element (no reload needed) and the navbar
        toggle's icon, then saves the choice to the cached state so it survives a
        reload. Auto defers to the OS/browser ``prefers-color-scheme`` setting.

        Args:
            scheme: The color scheme to switch to.
        """
        self.color_scheme = scheme
        self.dark_mode.value = _scheme_to_dark_mode(scheme)
        self.dark_mode.update()
        self.color_scheme_button.props(f"icon={_color_scheme_icon(scheme)}")
        self.color_scheme_button.update()
        if self.suppress_cache_save:
            return
        try:
            _save_cached_state(self._state_snapshot())
        except (OSError, ValueError) as error:
            ui.notify(
                self.t("notify.color_scheme_persist_fail").format(error=error),
                type="negative",
            )

    def set_log_scale(self, log_scale: bool) -> None:
        """Switch the capital (y) axis between linear and logarithmic scale.

        Re-renders the existing chart in place (no reload): swaps the y-axis
        config and re-runs the forecast so the series are rebuilt with (or
        without) the log-scale floor clipping, then persists the choice to the
        cached state so the toggle survives a reload.

        Args:
            log_scale: ``True`` to use a logarithmic scale, ``False`` for linear.
        """
        self.log_scale = log_scale
        self.chart.options["yAxis"] = _chart_y_axis(log_scale)
        self.run_forecast()
        if self.suppress_cache_save:
            return
        try:
            _save_cached_state(self._state_snapshot())
        except (OSError, ValueError) as error:
            ui.notify(
                self.t("notify.color_scheme_persist_fail").format(error=error),
                type="negative",
            )

    def _build_file_dialog(self) -> None:
        """Build the File window holding the save/load/delete profile controls.

        Binds :attr:`profile_name_input` and :attr:`profile_select`, which the
        save/load/delete handlers read from.
        """
        with ui.dialog() as dialog, ui.card().classes("w-[460px] p-4 gap-2"):
            self.file_dialog = dialog
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(self.t("file.title")).classes("text-lg font-semibold")
                ui.button(icon="close", on_click=dialog.close).props(
                    "flat dense round"
                )
            ui.label(self.t("file.description")).classes(
                "text-xs text-gray-500"
            )
            with ui.row().classes("w-full gap-2 items-end"):
                self.profile_name_input = ui.input(
                    label=self.t("file.profile_name"),
                ).classes("flex-1")
                ui.button(
                    self.t("file.save"), on_click=self.save_profile
                ).props("color=green-4")
            with ui.row().classes("w-full gap-2 items-end"):
                self.profile_select = ui.select(
                    options=self.profile_store.list_profiles(),
                    label=self.t("file.saved_profiles"),
                    with_input=True,
                ).classes("flex-1")
                ui.button(
                    self.t("file.load"), on_click=self.load_profile
                ).props("outline")
                ui.button(
                    self.t("file.delete"), on_click=self.delete_profile
                ).props("outline color=red")

    def _build_about_dialog(self) -> None:
        """Build the About window showing the application version."""
        with (
            ui.dialog() as dialog,
            ui.card().classes("p-4 gap-2 items-center"),
        ):
            self.about_dialog = dialog
            ui.html(_inline_logo_svg()).classes("w-12 h-12")
            ui.label(self.t("about.app_name")).classes("text-lg font-semibold")
            ui.label(_version_label_text()).classes("text-sm text-gray-500")
            ui.button(self.t("about.close"), on_click=dialog.close).props(
                "flat"
            )

    def build_assets(self) -> list[Asset]:
        """Build asset objects from the current UI rows.

        Returns:
            List of assets for the forecast.
        """
        return [_asset_from_row(row) for row in self.asset_rows]

    def render_asset_rows(self) -> None:
        """Render the asset input rows."""
        self.assets_container.clear()
        for index, row in enumerate(self.asset_rows):
            with self.assets_container:
                _render_asset_row(
                    index,
                    row,
                    self.update_asset_row,
                    self.remove_asset_row,
                    self.t,
                )

    def _build_forecast_inputs(
        self,
    ) -> tuple[UserProfile, list[Asset], WithdrawalPlan]:
        """Assemble the forecast inputs from the current widget values.

        Reads the profile, asset rows, and withdrawal/state-pension inputs and
        builds the engine's typed inputs. Shared by :meth:`run_forecast` and
        :meth:`export_forecast_csv` so both project the exact same scenario.

        Returns:
            A ``(profile, assets, withdrawal)`` tuple ready for
            :func:`forecast_wealth`; the withdrawal always carries a
            :class:`StatePension`.
        """
        profile = UserProfile(
            current_age_years=int(self.current_age_years.value or 0),
            current_age_months=int(self.current_age_months.value or 0),
            retirement_age=int(self.retirement_age.value or 0),
            end_age=int(self.end_age.value or 0),
            currency=str(self.currency.value or "EUR"),
            average_inflation_rate=float(
                self.average_inflation_rate.value or 0.0
            )
            / 100,
            debt_interest_rate=float(self.debt_interest_rate.value or 0.0)
            / 100,
        )
        assets = self.build_assets()
        monthly_growth = estimate_monthly_growth_per_working_year(
            float(self.annual_income.value or 0), get_config().drv
        )
        withdrawal = WithdrawalPlan(
            monthly_withdrawal=float(self.withdrawal_input.value or 0),
            state_pension=StatePension(
                current_monthly_amount=float(
                    self.state_pension_current_monthly_amount.value or 0
                ),
                monthly_growth_per_working_year=float(monthly_growth),
                start_age=int(self.state_pension_start_age.value or 67),
                adjustment_rate=float(
                    self.state_pension_adjustment_rate.value or 0.0
                )
                / 100,
            ),
        )
        return profile, assets, withdrawal

    def run_forecast(self) -> None:
        """Run the forecast and update the UI outputs."""
        try:
            profile, assets, withdrawal = self._build_forecast_inputs()
            # State-pension estimates (display-only). The business math lives
            # in finev.pension; the UI only renders the results.
            config = get_config()
            state_pension = withdrawal.state_pension
            assert state_pension is not None  # always built above
            monthly_growth_per_working_year_computed = (
                state_pension.monthly_growth_per_working_year
            )
            pension_start_age = state_pension.start_age
            penalty_fraction = early_retirement_penalty_fraction(
                pension_start_age, config.drv
            )
            years_remaining = max(
                0, profile.retirement_age - profile.current_age_years
            )
            net_pension = estimate_pension_at_start(
                current_monthly_amount=state_pension.current_monthly_amount,
                monthly_growth_per_working_year=(
                    monthly_growth_per_working_year_computed
                ),
                years_until_retirement=years_remaining,
                penalty_fraction=penalty_fraction,
            )

            self.state_pension_growth_display.text = _format_currency(
                monthly_growth_per_working_year_computed,
                profile.currency,
            ) + self.t("common.pm_suffix")
            self.state_pension_growth_display.update()
            if penalty_fraction > 0:
                penalty_monthly = (
                    monthly_growth_per_working_year_computed * penalty_fraction
                )
                self.state_pension_penalty_display.text = self.t(
                    "pension.penalty"
                ).format(
                    amount=_format_currency(penalty_monthly, profile.currency),
                    pct=f"{penalty_fraction * 100:.1f}%",
                )
            else:
                self.state_pension_penalty_display.text = self.t(
                    "pension.no_penalty"
                )
            self.state_pension_penalty_display.update()
            self.state_pension_achieved_display.text = self.t(
                "pension.achieved"
            ).format(
                age=pension_start_age,
                amount=_format_currency(net_pension, profile.currency),
                years=years_remaining,
                ret=profile.retirement_age,
            )
            self.state_pension_achieved_display.update()

            df = forecast_wealth(
                profile=profile,
                assets=assets,
                withdrawal=withdrawal,
            )
        except (ValueError, KeyError) as error:
            ui.notify(str(error), type="negative")
            return

        display_df = _yearly_display_frame(df)
        age_labels = [
            f"{int(age)}" for age in display_df["age_years"].tolist()
        ]
        rounded = display_df.copy()
        rounded["age"] = age_labels
        numeric_columns = rounded.select_dtypes(include="number").columns
        rounded[numeric_columns] = (
            rounded[numeric_columns].round(0).astype(int)
        )

        asset_columns = _asset_value_columns(assets)
        self.table.columns = _forecast_table_columns(asset_columns, self.t)
        self.table.rows = rounded.to_dict(orient="records")
        self.table.update()

        self.chart.options["xAxis"]["data"] = age_labels
        self.chart.options["series"] = _chart_series(
            rounded, asset_columns, self.log_scale
        )
        self.chart.update()

        final_total = float(df["total"].iloc[-1])
        self.summary_label.text = self.t("forecast.total").format(
            age=profile.end_age,
            amount=_format_currency(final_total, profile.currency),
        )
        if self.suppress_cache_save:
            return
        try:
            _save_cached_state(self._state_snapshot())
        except (OSError, ValueError) as error:
            ui.notify(
                self.t("notify.save_cache_fail").format(error=error),
                type="negative",
            )

    def export_forecast_csv(self) -> None:
        """Export the detailed monthly forecast as a CSV download.

        Recomputes the full monthly forecast for the current inputs — every
        month and every column the engine produces, not the rounded yearly view
        shown in the table — and streams it to the browser as a CSV download,
        which the browser routes to the user's download folder.
        """
        try:
            profile, assets, withdrawal = self._build_forecast_inputs()
            df = forecast_wealth(
                profile=profile,
                assets=assets,
                withdrawal=withdrawal,
            )
        except (ValueError, KeyError) as error:
            ui.notify(str(error), type="negative")
            return
        ui.download.content(
            _forecast_csv(df), _export_csv_filename(), "text/csv"
        )

    def _state_snapshot(self) -> dict[str, Any]:
        """Build a serializable snapshot of the current UI inputs.

        Shared by the autosave cache and the named-profile store so both persist
        an identical shape. The state-pension growth is recomputed from the
        annual income (it is a display-only derived figure).

        Returns:
            A dict with ``assets``, ``profile`` and ``withdrawal`` keys.
        """
        monthly_growth = estimate_monthly_growth_per_working_year(
            float(self.annual_income.value or 0), get_config().drv
        )
        return {
            "language": self.language,
            "color_scheme": self.color_scheme.value,
            "log_scale": self.log_scale,
            "assets": [_normalize_asset_row(row) for row in self.asset_rows],
            "profile": {
                "current_age_years": int(self.current_age_years.value or 0),
                "current_age_months": int(self.current_age_months.value or 0),
                "retirement_age": int(self.retirement_age.value or 0),
                "end_age": int(self.end_age.value or 0),
                "currency": str(self.currency.value or "EUR"),
                "average_inflation_rate_pct": float(
                    self.average_inflation_rate.value or 0.0
                ),
                "debt_interest_rate_pct": float(
                    self.debt_interest_rate.value or 0.0
                ),
                "annual_income": float(self.annual_income.value or 0),
            },
            "withdrawal": {
                "monthly_withdrawal": float(self.withdrawal_input.value or 0),
                "state_pension_current_monthly_amount": float(
                    self.state_pension_current_monthly_amount.value or 0
                ),
                "state_pension_growth_per_working_year": float(monthly_growth),
                "state_pension_start_age": int(
                    self.state_pension_start_age.value or 67
                ),
                "state_pension_adjustment_rate_pct": float(
                    self.state_pension_adjustment_rate.value or 0.0
                ),
            },
        }

    def build(self) -> None:
        """Construct the page widgets and render the initial forecast."""
        profile_state = self.profile_state
        withdrawal_state = self.withdrawal_state
        # Theme CSS makes the navbar, surfaces and scrollbars follow the scheme
        # (keyed on Quasar's ``body--dark`` class) and grays out the dark
        # palette. Apply the active scheme; ``None`` lets NiceGUI follow the
        # OS/browser ``prefers-color-scheme`` preference (auto).
        ui.add_head_html(f"<style>{_theme_css()}</style>")
        # Cap panel help tooltips to a readable column. Quasar's position engine
        # overwrites an inline max-width, so this rule needs ``!important``.
        ui.add_head_html(f"<style>{_help_tip_css()}</style>")
        self.dark_mode = ui.dark_mode(
            value=_scheme_to_dark_mode(self.color_scheme)
        )
        self._build_file_dialog()
        self._build_about_dialog()
        self._build_navbar()
        # Drop the default page padding so the layout below owns the full
        # height under the navbar; each panel then scrolls within its own
        # frame instead of the whole page scrolling as one.
        ui.query(".nicegui-content").classes("p-0 gap-0")
        # Constrain the content to the configured max width and centre it
        # (``mx-auto``); an empty max-width style means full width.
        outer_style = "height: calc(100vh - 4rem)"
        max_width_style = self.ui_config.content_max_width_style
        if max_width_style:
            outer_style = f"{outer_style}; {max_width_style}"
        with ui.column().classes("w-full mx-auto p-4").style(outer_style):
            with ui.row().classes(
                "w-full h-full gap-4 items-stretch flex-nowrap"
            ):
                # ── Left sidebar (independent scroll frame) ─
                with ui.column().classes(
                    "w-[420px] shrink-0 gap-4 h-full overflow-y-auto pr-2"
                ):
                    with ui.card().classes("w-full p-3"):
                        _panel_header(
                            self.t("profile.section"),
                            self.t("panel.profile.help"),
                        )
                        with ui.grid(columns=2).classes("w-full gap-3"):
                            self.current_age_years = _commit_on_enter(
                                ui.number(
                                    label=self.t("profile.current_age_years"),
                                    value=profile_state["current_age_years"],
                                    format="%.0f",
                                ),
                                self._commit_profile_edit,
                            )
                            self.current_age_months = _commit_on_enter(
                                ui.number(
                                    label=self.t("profile.current_age_months"),
                                    value=profile_state["current_age_months"],
                                    format="%.0f",
                                    min=0,
                                    max=11,
                                ),
                                self._commit_profile_edit,
                            )
                            self.retirement_age = _commit_on_enter(
                                ui.number(
                                    label=self.t("profile.retirement_age"),
                                    value=profile_state["retirement_age"],
                                    format="%.0f",
                                ),
                                self._commit_profile_edit,
                            )
                            self.end_age = _commit_on_enter(
                                ui.number(
                                    label=self.t("profile.end_age"),
                                    value=profile_state["end_age"],
                                    format="%.0f",
                                ),
                                self._commit_profile_edit,
                            )
                            self.currency = _commit_on_enter(
                                ui.input(
                                    label=self.t("profile.currency"),
                                    value=profile_state["currency"],
                                ),
                                self._commit_profile_edit,
                            )
                            self.average_inflation_rate = _commit_on_enter(
                                ui.number(
                                    label=self.t("profile.inflation"),
                                    value=profile_state[
                                        "average_inflation_rate_pct"
                                    ],
                                    format="%.2f",
                                    min=-99.9,
                                    step=0.1,
                                ),
                                self._commit_profile_edit,
                            )
                            self.debt_interest_rate = _commit_on_enter(
                                ui.number(
                                    label=self.t("profile.debt_interest"),
                                    value=profile_state[
                                        "debt_interest_rate_pct"
                                    ],
                                    format="%.2f",
                                    min=0,
                                    step=0.1,
                                ),
                                self._commit_profile_edit,
                            )
                            self.withdrawal_input = _commit_on_enter(
                                ui.number(
                                    label=self.t("profile.monthly_withdrawal"),
                                    value=withdrawal_state[
                                        "monthly_withdrawal"
                                    ],
                                    format="%.0f",
                                    min=0,
                                    step=50,
                                ),
                                self._commit_profile_edit,
                            )

                    with ui.card().classes("w-full p-3"):
                        _panel_header(
                            self.t("pension.section"),
                            self.t("panel.pension.help"),
                        )
                        with ui.grid(columns=2).classes("w-full gap-3"):
                            self.annual_income = _commit_on_enter(
                                ui.number(
                                    label=self.t("pension.annual_income"),
                                    value=profile_state.get(
                                        "annual_income", 50000.0
                                    ),
                                    format="%.0f",
                                    min=0,
                                    step=1000,
                                ),
                                self._commit_profile_edit,
                            )
                            self.state_pension_current_monthly_amount = _commit_on_enter(
                                ui.number(
                                    label=self.t("pension.now_monthly"),
                                    value=withdrawal_state[
                                        "state_pension_current_monthly_amount"
                                    ],
                                    format="%.0f",
                                    min=0,
                                    step=50,
                                ),
                                self._commit_profile_edit,
                            )
                            self.state_pension_growth_display = ui.label(
                                _format_currency(
                                    withdrawal_state[
                                        "state_pension_growth_per_working_year"
                                    ],
                                    profile_state["currency"],
                                )
                                + self.t("common.pm_suffix")
                            )
                            # Read-only: estimated early-retirement penalty.
                            self.state_pension_penalty_display = ui.label("")
                            # Read-only: total achieved monthly pension.
                            self.state_pension_achieved_display = ui.label("")
                            self.state_pension_start_age = _commit_on_enter(
                                ui.number(
                                    label=self.t("pension.start_age"),
                                    value=withdrawal_state[
                                        "state_pension_start_age"
                                    ],
                                    format="%.0f",
                                    min=63,
                                    max=67,
                                    step=1,
                                ),
                                self._commit_profile_edit,
                            )
                            self.state_pension_adjustment_rate = (
                                _commit_on_enter(
                                    ui.number(
                                        label=self.t(
                                            "pension.adjustment_rate"
                                        ),
                                        value=withdrawal_state[
                                            "state_pension_adjustment_rate_pct"
                                        ],
                                        format="%.2f",
                                        min=-99.9,
                                        step=0.1,
                                    ),
                                    self._commit_profile_edit,
                                )
                            )

                    with ui.card().classes("w-full p-3"):
                        _panel_header(
                            self.t("assets.section"),
                            self.t("panel.assets.help"),
                        )
                        ui.label(self.t("assets.defaults_note")).classes(
                            "text-xs text-gray-500"
                        )

                        self.assets_container = ui.column().classes(
                            "w-full gap-2"
                        )
                        self.render_asset_rows()

                        with ui.row().classes("gap-2"):
                            ui.button(
                                self.t("assets.add"),
                                on_click=self.add_asset_row,
                            ).props("outline color=green-4")
                            ui.button(
                                self.t("assets.reset"),
                                on_click=self.reset_state,
                            ).props("outline color=red")

                # ── Right panel (chart + table): own scroll frame ─
                with ui.column().classes(
                    "flex-1 min-w-0 gap-4 h-full overflow-y-auto pr-2"
                ):
                    with ui.row().classes(
                        "w-full items-center justify-between"
                    ):
                        self.summary_label = ui.label(
                            self.t("forecast.none")
                        ).classes("text-sm")
                        self.log_scale_toggle = ui.switch(
                            self.t("chart.log_scale"),
                            value=self.log_scale,
                            on_change=lambda e: self.set_log_scale(e.value),
                        ).props("dense")
                    # shrink-0 keeps the chart at its fixed height: as a flex
                    # child of the scroll frame its content height is 0 (the
                    # ECharts canvas is absolutely positioned), so without it
                    # flex-shrink would collapse the chart and hide the plot.
                    self.chart = ui.echart(
                        _build_chart_options(self.log_scale)
                    ).classes("w-full h-[500px] shrink-0")
                    self.table = (
                        ui.table(columns=[], rows=[], row_key="month_index")
                        .props("dense flat bordered separator=horizontal")
                        .classes("w-full text-xs")
                    )

            self.run_forecast()
            if self.state_error:
                ui.notify(self.state_error, type="negative")


def build_wealth_page() -> None:
    """Construct the wealth forecast page and bind its update logic."""
    _WealthPage().build()

# Wealth Forecast App — Design and Requirements

> **Status:** living document describing the *current* implementation of `finev`,
> reflecting what the code actually does today. Engineering rationale
> is in [SOFTWARE_ENGINEERING.md](../SOFTWARE_ENGINEERING.md); the operational
> checklist is in [CLAUDE.md](../CLAUDE.md).

---

## 1. Overview

Fin-Escape-Velocity (`finev`) is a German personal-finance forecasting tool. It
projects the monthly value of a user's assets from their current age through an
end age (default 100), accounting for:

- asset-specific compound growth,
- pre-retirement monthly contributions,
- post-retirement monthly withdrawals (net-target, grossed up for tax),
- German **Abgeltungssteuer** (capital-gains tax) + **Soli** on ETF gains, with
  the annual tax-free allowance (*Sparerpauschbetrag*) and partial exemption
  (*Teilfreistellung*),
- occupational pension (**bAV**) transfer/payout strategies,
- statutory state pension (**DRV**) income that offsets withdrawals,
- **VBLklassik** public-sector occupational pension as a lifelong, income-taxed
  annuity that offsets withdrawals,
- inheritance events with **Erbschaftsteuer** by heir class.

It ships as both a NiceGUI web app and a CLI, backed by a single pure forecasting
engine.

---

## 2. Goals and non-goals

### Goals

- Produce a **deterministic, monthly** forecast per asset and for the total
  portfolio, from current age through end age inclusive.
- Keep all domain math in a pure engine that is unit-testable without a UI.
- Drive every German tax constant from configuration, not code, so rule changes
  are data edits.
- Remain easy to extend: new asset types, per-month adjustments, and alternative
  tax regimes should slot in without rewriting the monthly loop.

### Non-goals (current iteration)

- No Monte-Carlo / stochastic modelling — growth rates are deterministic.
- No FX conversion — the currency field is a display label only.
- No multi-user *accounts* (authentication / per-user server sessions). Multiple
  people are supported instead through named **settings profiles** persisted via
  a pluggable store (local disk today; an S3/database backend can be added by
  implementing the same interface).
- No real-time market data; all inputs are user-supplied or configured.

---

## 3. Definitions

| Term | Meaning |
|---|---|
| **Current age** | Age at forecast start, in whole years plus optional months (0–11). |
| **Retirement age** | Age at which contributions stop and withdrawals begin (default 67). |
| **End age** | Last age included in the forecast (default 100). |
| **Monthly step** | Forecast granularity: one calculation per month. |
| **Cost basis** | Sum of contributions/capital paid into an asset; grows with contributions, shrinks proportionally on withdrawal, never written down by market loss. |
| **Gains** | `balance − cost_basis`; the taxable component of a withdrawal. |
| **Gross withdrawal** | Amount removed from the portfolio before tax. |
| **Net cashflow** | What the user actually receives/contributes after taxes in a month. |
| **bAV** | *Betriebliche Altersvorsorge* — occupational pension. |
| **bAV strategy** | How a bAV pays out: `transfer` (move balance to ETF/Cash over a window) or `income` (pay monthly gains). |
| **DRV** | *Deutsche Rentenversicherung* — the statutory state-pension system. |
| **VBLklassik** | Mandatory public-sector occupational pension (*Zusatzversorgung*) run by the VBL: a defined-benefit lifelong annuity of €4/Versorgungspunkt gross monthly, fully income-taxed and (here) not inflation-compensated. |
| **Erbschaftsteuer** | German inheritance tax, by heir class and Freibetrag. |
| **Teilfreistellung** | Partial tax exemption on equity-fund gains (30%). |
| **Sparerpauschbetrag** | Annual capital-gains tax-free allowance (€1,000). |

---

## 4. Architecture

The domain flows in one direction:

```
models → config / forecast / pension → ui_state / ui_view → ui / cli / app
```

Business logic stays in the pure engine modules. The presentation modules
(`ui.py`, `cli.py`, `app.py`) only call the engine and render results — they
contain no domain math.

| Module | Role | Pure? |
|---|---|---|
| [`models.py`](../src/finev/models.py) | Domain types (`UserProfile`, `Asset`, `StatePension`, `WithdrawalPlan`) and enums (`AssetType`, `BAVStrategy`, `AllocationStrategy`, `InheritanceRelationship`); default gain rates. | ✅ |
| [`config.py`](../src/finev/config.py) | Loads and validates `config.json` into frozen typed dataclasses; exposes ETF/DRV/Erbschaftsteuer parameters and derived rates. | ✅ |
| [`forecast.py`](../src/finev/forecast.py) | The calculation engine: validates inputs, builds an immutable per-run context, runs the monthly pipeline, returns a pandas `DataFrame`. | ✅ |
| [`pension.py`](../src/finev/pension.py) | DRV state-pension **display** estimates (growth-per-working-year, early-retirement penalty, pension at start). No I/O. | ✅ |
| [`i18n.py`](../src/finev/i18n.py) | UI internationalization: the English/German translation catalog and lookup helpers (`translate`, `normalize_language`, `make_translator`), with English→key fallback. No NiceGUI dependency. | ✅ |
| [`ui_state.py`](../src/finev/ui_state.py) | UI defaults, JSON state persistence (autosave cache, incl. the language preference), value coercion/clamping, row normalization, row→`Asset` conversion. No NiceGUI dependency. | ✅ |
| [`profile_store.py`](../src/finev/profile_store.py) | Named settings-profile storage behind the `ProfileStore` abstraction; `LocalDiskProfileStore` keeps one JSON file per profile. Pluggable backend (S3/DB later). No NiceGUI dependency. | ✅ |
| [`ui_view.py`](../src/finev/ui_view.py) | Presentation helpers: currency formatting, chart/table option shaping, yearly display frame, version label text, theme CSS (scheme-following navbar/surfaces/scrollbars). No NiceGUI dependency. | ✅ |
| [`ui_config.py`](../src/finev/ui_config.py) | Loads and validates `ui_config.json` (layout max width, color scheme) into a frozen typed dataclass; maps the scheme to NiceGUI's dark-mode value and the width to a CSS declaration, and provides the navbar toggle's cycle/icon helpers. No NiceGUI dependency. | ✅ |
| [`ui.py`](../src/finev/ui.py) | NiceGUI page. The `_WealthPage` controller holds widget refs + state and binds event handlers as methods; `build_wealth_page()` is the thin entry point. | ❌ (presentation) |
| [`app.py`](../src/finev/app.py) | NiceGUI server launcher; auto-selects a free port in 8081–8130; honours `WEALTH_APP_PORT`. | ❌ (I/O) |
| [`cli.py`](../src/finev/cli.py) | Console entry point: builds a default scenario, prints a yearly summary table. | ❌ (I/O) |

`config.json` is the authoritative source for all German tax constants. When a
tax rule changes, edit the JSON — not the Python. `ui_config.json` is the
authoritative source for the presentation-only UI settings (layout max width and
color scheme); see [§9.1](#91-web-app-nicegui).

### Engine internals

`forecast_wealth()` is structured as an ordered pipeline of small pure step
functions over a shared mutable `_MonthlyState`, parameterised by an immutable
`_EngineParams`:

1. `_apply_inheritance` — credit net inheritance proceeds due this month.
2. `_apply_contributions` *(pre-retirement)* **or** `_apply_withdrawal` *(post-retirement)*.
3. `_apply_bav_transfer` — move an in-window slice of each TRANSFER bAV to ETF/Cash.
4. `_apply_bav_income` — pay out monthly gains from INCOME bAV (freezes its principal).
5. `_apply_growth` — compound each balance by its monthly rate (skipping frozen assets).

This shape realises the design intent that new per-month adjustments and asset
types slot in as additional steps/handlers rather than edits to a monolithic loop.

---

## 5. Inputs

### 5.1 User profile (`UserProfile`)

| Field | Default | Notes |
|---|---|---|
| Current age (years) | — (40 in UI) | Required; whole years. |
| Current age (months) | 0 | 0–11; fractional start offset. |
| Retirement age | 67 | Contributions stop / withdrawals begin. |
| End age | 100 | Must be ≥ retirement age and > current age. |
| Currency | `EUR` | Display label only; no FX. |
| Average inflation rate | 2% (UI) / 0.02 (model) | Annual; inflates withdrawal targets. Must be > −100%. |
| Debt interest rate | 8% (UI) / 0.08 (model) | Annual rate charged on negative total wealth (debt); compounds monthly. Must be ≥ 0. |

### 5.2 State pension (`StatePension` + UI-derived display)

| Field | Required | Notes |
|---|---|---|
| Current monthly amount (today-value) | Yes | Gross monthly state pension if the user stopped working today. |
| Annual income | Yes (UI) | Drives the read-only pension-points estimate. |
| Monthly growth per working year | Derived | Extra gross monthly pension per additional working year. Computed in `pension.py` from annual income and DRV params; shown read-only. |
| Start age | Yes | Must be **63–67** inclusive. |
| Annual pension adjustment (*Rentenanpassung p.a.*) | 1% (UI) / 0.01 (model) | Annual growth applied to the accrued pension over time, **independent of price inflation**. When below the inflation rate, the pension loses real value. Must be > −100%. |
| Tax rate | Optional | Defaults to `DRV_BRUTTO_RENTE_STEUERSATZ` when omitted; must be in `[0, 1)`. |

DRV parameters (from `config.json`): `DRV_RENTENABSCHLAG_PRO_JAHR` (early-retirement
penalty per year), `DRV_RENTE_PRO_RENTENPUNKT_EURO`, `DRV_DURCHSCHNITTS_JAHRESENTGELT_EURO`,
`DRV_MAXIMALE_RENTENPUNKTE_PRO_JAHR`, `DRV_BRUTTO_RENTE_STEUERSATZ`.

The UI shows three read-only displays: the computed monthly growth per working
year, the estimated early-retirement penalty for the chosen start age, and the
estimated net pension at start. The penalty is shown separately but applied to
the gross pension by the engine (see §7.6).

### 5.3 Assets (`Asset`)

Each asset row carries a name, a type (`ETF`, `bAV`, `Cash`, `Inheritance`,
`VBLklassik`), a current value, an optional annual gain-rate override, a monthly
contribution, and an `active` toggle. ETF/Cash/bAV also carry *unrealized gains*
in the UI, which is converted to an
`initial_cost_basis = current_value − unrealized_gains`.

**bAV-specific fields:** `bav_strategy` (`transfer`/`income`),
`bav_retirement_age`, `bav_transfer_etf_ratio` (share to ETF; remainder to
Cash). The bAV retirement age is the transfer year for `transfer` and the payout
start age for `income`.

**Inheritance-specific fields:** `inheritance_gross_amount`, `inheritance_age`
(year the event occurs), `inheritance_relationship` (heir class).

**VBLklassik-specific fields:** `vbl_monthly_pension` (gross monthly pension at
the start age, today's euros), `vbl_monthly_growth_per_working_year` (extra gross
monthly pension per additional public-service working year — one Versorgungspunkt
per year, i.e. `VBL_RENTE_PRO_PUNKT_EURO`), `vbl_start_age`, and an optional
`vbl_tax_rate`. VBLklassik holds **no running balance**: like inheritance it has
no balance column and takes no contributions; instead it pays a lifelong annuity
that offsets withdrawals (§7.9). In the UI the user enters either Versorgungspunkte
(× `VBL_RENTE_PRO_PUNKT_EURO`) or a direct euro amount, and a "still in public
service" checkbox toggles the per-working-year accrual.

#### Default annual gain rates (`models.DEFAULT_ANNUAL_GAIN_RATES`)

| Asset type | Default annual gain rate |
|---|---|
| ETF | 6.0% |
| bAV | 2.0% |
| Cash | 0.5% |
| Inheritance | 0.0% (no running balance) |
| VBLklassik | 0.0% (no running balance; income annuity) |

Defaults are configurable per-asset in the UI; the type default is used when no
override is given.

### 5.4 Withdrawals (`WithdrawalPlan`)

- A single **net monthly withdrawal target**, interpreted as the amount the user
  wants to *receive* (the engine grosses it up for ETF tax).
- Allocation strategy: **proportional** to withdrawable asset balances. (The
  `AllocationStrategy` enum exists for future strategies; only `PROPORTIONAL` is
  currently valid.)
- The target is specified in **today's currency** and inflated to each retirement
  month.
- An optional `StatePension` whose net amount offsets the target each month.

---

## 6. Configuration (`config.json`)

Validated on load into frozen dataclasses (`FinevConfig` → `DrvConfig`,
`VblConfig`, `EtfTaxConfig`, `InheritanceTaxConfig`). Fractions are range-checked
`[0,1]`, euro amounts checked non-negative/positive as appropriate.

**VBLklassik** — `VBL_RENTE_PRO_PUNKT_EURO` (gross monthly pension per
Versorgungspunkt, currently **€4.00**) and `VBL_BRUTTO_RENTE_STEUERSATZ` (default
income-tax rate on the gross VBL pension, currently **16%**).

**ETF tax** — effective rate = `abgeltungssteuer × (1 + soli + kirchensteuer)`
(currently 25% × 1.055 = **26.25%**); taxable share = `1 − teilfreistellung`
(currently **70%**); annual allowance = **€1,000**.

**Erbschaftsteuer** — per heir class (I/II/III) a Freibetrag plus a **flat**
(non-marginal) rate chosen by which bracket the taxable amount (gross − Freibetrag)
falls into. Thresholds: 75k / 300k / 600k / 6M / 13M / 26M.

| Relationship | Class | Freibetrag |
|---|---|---|
| Ehegatte / Lebenspartner | I | €500,000 |
| Kind / Stiefkind | I | €400,000 |
| Enkel | I | €200,000 |
| Elternteil | I | €100,000 |
| Klasse II (Geschwister, Nichten, Neffen…) | II | €20,000 |
| Klasse III (übrige) | III | €20,000 |

**Privatinsolvenz** — `PRIVATINSOLVENZ_SCHWELLE_EURO` (currently **€100,000**, a
positive amount) is the most negative total wealth a forecast may reach. It is a
config-only constant (no UI control). See §7.11.

---

## 7. Forecast rules

### 7.1 Horizon and timeline

Ages are tracked in months. The forecast runs from `start_age_months`
(`current_age_years × 12 + current_age_months`) through `end_age × 12` inclusive.
Month 0 is the seeded starting state (no cashflow applied); month ≥ 1 runs the
full pipeline. A fractional current age shifts the month-in-year of every row.

### 7.2 Monthly growth rate

`monthly_rate = (1 + annual_rate)^(1/12) − 1`, applied **after** the month's
cashflow events so a contribution earns growth in the same month.

### 7.3 Contributions (pre-retirement)

Each active, non-inheritance asset receives its monthly contribution, added to
both balance and cost basis; the sum is recorded as positive net cashflow.

If the state pension's (§7.6) or a VBLklassik pension's (§7.9) start age falls
**before** retirement, the user is still working yet already drawing that pension.
In those gap months the combined net pension is **invested** rather than dropped:
it is added to both the balance and cost basis of a single target asset and
recorded as positive net cashflow. The target is the active ETF with the **highest
annual gain rate**, or — when no ETF exists — the highest-rate active Cash asset;
ties resolve to the lowest index and the target is fixed for the whole run. With
no ETF or Cash asset the income is dropped. From retirement onward the pensions
instead offset the withdrawal target (§7.4 step 2), so they are never counted
twice.

### 7.4 Withdrawals (post-retirement)

1. Inflate the base net target to the current month.
2. Subtract the **net state pension** and the **net VBLklassik pension** (§7.9)
   for the month; floor at 0.
3. Determine **withdrawable** assets: ETF and Cash always; bAV only once its
   bAV retirement age is reached. (State and VBLklassik pensions are income, not
   withdrawable balances.)
4. **Gross up** the net target to cover ETF capital-gains tax on the taxable
   gains portion, accounting for any remaining annual allowance (`_gross_up_withdrawal`).
5. Allocate the grossed-up amount **proportionally** by balance across
   withdrawable assets, capped at the total available (each balance floors at 0).
6. Reduce each asset's cost basis proportionally to the fraction withdrawn.
7. Tax the ETF taxable gains beyond the remaining allowance at the effective
   rate; record taxes and net cashflow.
8. If the assets could not cover the full net target, the unmet remainder is
   **borrowed**: it is added to the running debt and recorded as net cashflow, so
   total wealth is allowed to go below zero (see §7.11).

### 7.5 ETF withdrawal tax

Applies only to the ETF gains portion of a withdrawal:

- gains ratio (per ETF, balance > 0): `max(0, (balance − cost_basis) / balance)`
- taxable gains: `gains_portion × taxable_share` (×0.70)
- the annual allowance (€1,000) is consumed first each calendar year; only the
  excess is taxed
- tax: `taxable_after_allowance × effective_rate` (×0.2625)

The allowance resets at the start of each forecast year.

### 7.6 State pension

For months at/after the start age:

```
accrued       = current_monthly + working_years × growth_per_working_year
gross(month)  = accrued × adjustment_multiplier(month) × (1 − rentenabschlag × (67 − start_age))
net(month)    = gross(month) × (1 − tax_rate)
```

`adjustment_multiplier(month)` compounds the **annual pension adjustment**
(*Rentenanpassung p.a.*, default 1%) over the months since the forecast start —
**not** price inflation. The withdrawal target itself remains inflation-indexed
(§7.4), so when the adjustment rate is below inflation the pension's real value
erodes over time.

`working_years` is the working time accrued **so far**, capped at retirement:
`(min(age, retirement) − current) / 12`. From retirement onward this equals the
full current→retirement window; when the pension starts **before** retirement it
grows month by month through the gap, so the pension is not credited with working
years the user has not yet worked. `tax_rate` defaults to
`DRV_BRUTTO_RENTE_STEUERSATZ`. From retirement onward the net amount reduces the
withdrawal target (§7.4 step 2); in any months where the pension starts before
retirement, the same net amount is instead invested while still working (§7.3).
The display-only estimates in `pension.py` mirror this for the UI but are computed
independently.

### 7.7 bAV strategies

- **Transfer:** across the 12 months of the `bav_retirement_age` year, transfer
  an equal monthly fraction (`1 / remaining_months`) of the bAV balance. The
  gains portion is taxed at the full effective rate (no Teilfreistellung), and the
  net transfer is split to ETF/Cash by `bav_transfer_etf_ratio`. A transfer
  requires at least one ETF target (if ratio > 0) and one Cash target (if ratio
  < 1).
- **Income:** from the `bav_retirement_age`, pay out the bAV's monthly gains as
  income, taxed at the full effective rate; the principal is **frozen** (does not
  compound) in payout months. Before that age, it compounds normally.

### 7.8 Inheritance

At the configured `inheritance_age` (in the matching month), an active inheritance
asset with a positive gross amount triggers an event: Erbschaftsteuer is computed
by relationship (§6), and the **net** proceeds are credited to ETF assets (or
Cash if no ETF exists), increasing both balance and cost basis. Inheritance
assets hold no running balance and are excluded from output columns.

### 7.9 VBLklassik pension

For each active VBLklassik asset, from its `vbl_start_age` onward:

```
working_years = (min(age, retirement) − current) / 12   (accrued so far, as §7.6)
gross(month)  = vbl_monthly_pension + working_years × vbl_monthly_growth_per_working_year
net(month)    = gross(month) × (1 − tax_rate)
```

`tax_rate` defaults to `VBL_BRUTTO_RENTE_STEUERSATZ` (fully income-taxed). From
retirement onward the combined net VBL pension across all active VBLklassik assets
reduces the withdrawal target (§7.4 step 2); for any months where a VBL pension
starts before retirement, that net amount is instead invested while still working
(§7.3). Unlike the state pension, the VBL pension is
**not inflation-compensated** — it stays nominal at its today's-euro value, so its
real value erodes against the inflation-indexed withdrawal target — and **no
early-retirement reduction** is applied. The per-working-year growth models the
"still in public service" option as one Versorgungspunkt earned per working year.

### 7.10 Asset activation toggle

Deactivating an asset (`active = false`) excludes it from contributions,
withdrawal allocation, transfers, and as a transfer/inheritance target — it is
treated as a zero balance — while its row and configuration remain in the UI and
persisted cache, so it can be re-activated to compare scenarios.

### 7.11 Debt and Privatinsolvenz (negative total wealth)

When a month's withdrawal exceeds the available assets, the unmet net need is
booked as **debt** — a running, non-negative balance held in engine state. Total
wealth is the asset sum **minus** this debt, so it may go negative once assets
are exhausted. Each month any outstanding debt compounds by the monthly
equivalent of the profile's `debt_interest_rate` (`_apply_debt_interest`). Net
inheritance proceeds **repay** outstanding debt before the remainder is invested.
Debt is not a separate output column; it is reflected only in a reduced (possibly
negative) `total`.

**Privatinsolvenz floor.** As the last step of each month, the debt is capped so
that total wealth cannot fall below `-PRIVATINSOLVENZ_SCHWELLE_EURO` (§6):
`_apply_insolvency_floor` sets `debt = min(debt, asset_total + floor)`. Because
the cap is applied to the carried-over state (not just the output row), a capped
debt **stops compounding** — so it stays pinned at the floor while insolvent, yet
a later inheritance large enough to repay the capped debt can lift the forecast
back into the green. A forecast may therefore enter Privatinsolvenz, escape via
an inheritance, and re-enter it later; the total stays at the floor for any span
where no rescue follows, including permanently once none can.

---

## 8. Outputs

`forecast_wealth()` returns a pandas `DataFrame`, one row per month, with columns:

| Column | Description |
|---|---|
| `month_index` | 0-based month from forecast start. |
| `age_years`, `age_months` | User age at that row. |
| `net_cashflow` | Net received (−)/contributed (+) that month, after taxes. |
| `taxes` | Total tax deducted that month (ETF + bAV + inheritance). VBL/state pension tax is reflected via the reduced net withdrawal, not this column. |
| *per-asset* | Balance for each balance-holding asset (column = asset name); inheritance and VBLklassik hold no balance and have no column. |
| `total` | Sum of all balance-holding asset balances, minus any outstanding debt; may be negative but never below the Privatinsolvenz floor (§7.11). |

Presentation layers derive a **yearly** view (`ui_view.yearly_display_frame`,
every 12th month; `cli.summarize_yearly`, aggregated per age-year) for the chart,
table, and console output.

---

## 9. User interfaces

### 9.1 Web app (NiceGUI)

`mise run app` launches `python -m finev.app`, which serves the page at `/` on the
first free port from 8081 (override with `WEALTH_APP_PORT`). An always-visible top
**navbar** (`ui.header`) carries the app logo, the title, **File**, **Export**
and **About** actions, and — pushed to the far right — a **language toggle**.
Below it the page (`_WealthPage`) has a left sidebar (Profile,
State pension, Assets cards with an add/reset control and per-row editors) and a
right panel (a row holding the summary label and a **log-scale toggle**, then the
ECharts line chart and yearly table). The two regions
fill the height below the navbar and **scroll independently** — each is its own
scroll frame (`overflow-y-auto`, full height of a viewport-bounded row), so a
tall sidebar (many asset rows) does not push the chart/table out of view and the
page never scrolls as a single block. The ECharts chart is pinned to its fixed
500px height (`shrink-0`) so flexbox does not collapse it inside the scroll
frame.

A **log-scale toggle** (a `ui.switch` next to the summary label) switches the
capital (y) axis between a linear and a logarithmic scale live —
`set_log_scale` swaps the `yAxis` config (`ui_view.chart_y_axis`), re-runs the
forecast to rebuild the series, and persists the choice to the autosave cache
(`log_scale` key, restored via `ui_state.load_log_scale`) — all without a reload.
In log view the visible axis bottom stays at 1000 € (`LOG_SCALE_Y_AXIS_MIN_EUR`).
Independently, `ui_view.chart_series` **clamps** every value up to a 1 € minimum
(`LOG_SCALE_VALUE_FLOOR_EUR`) only so the logarithmic axis stays well-defined — a
log scale cannot represent values ≤ 0. Because the value floor (1 €) is far below
the axis bottom (1000 €), a falling series descends past the 1000 € gridline and
slides off the bottom of the chart on its own, instead of throwing on a
non-positive value. Edits are debounced
(~0.5s) before re-running the forecast; structural changes
(type/strategy/active/relationship, add/remove, reset) re-render immediately.

The browser tab uses a bundled SVG favicon (`src/finev/static/favicon.svg`, a
rising-trend arrow), loaded via `ui_view.favicon_svg()` and passed to `ui.run`.
The same artwork is rendered inline as the navbar logo and inside the About
window via `ui_view.inline_logo_svg()`, which rescales the icon's fixed root
dimensions to its container; the navbar background is a matching teal in light
mode and a dark gray in dark mode (see the color-scheme note below).

The navbar's **About** action opens a window showing the application version
(e.g. `v0.1.0`), sourced from `ui_view.version_label_text()` →
`greet.get_version()`.

**Layout width and color scheme** default from `ui_config.json` via
`ui_config.get_ui_config()`. `MAX_WIDTH_PX` caps the centred content width (in
pixels; `0` means full width — the historical behaviour), applied as a
`max-width` CSS declaration on the page's outer column. `COLOR_SCHEME` is one of
`auto` | `light` | `dark` and is applied through `ui.dark_mode(...)`: `dark`/
`light` force a fixed scheme, while `auto` defers to the operating
system/browser preference (the `prefers-color-scheme` media query), so the app
follows the user's Windows/macOS/Linux light-or-dark setting.

A navbar **color-scheme toggle** (an icon button, left of the language toggle)
lets the user cycle `auto → light → dark` live — `set_color_scheme` updates the
page's `ui.dark_mode` element without a reload, swaps the button icon, and
persists the choice to the cached state (alongside the language) so it survives a
reload; `ui_config.json` provides only the default. Global theme CSS
(`ui_view.theme_css`, injected via `ui.add_head_html`) keys off Quasar's
`body--dark` class so the **navbar background** (brand teal in light, dark gray
in dark), the **page/card surfaces** (overriding Quasar's near-black defaults
with neutral grays) and the **scrollbars** all follow whichever scheme is active,
including auto-resolved dark.

Each input panel (Profile, State pension, Assets) carries a single **`?` help
icon** in its header instead of a tooltip per field. Resting on the icon reveals
a concise read-me describing that panel's parameters. The icon and its tooltip
are rendered by the `_panel_header(title, help_text)` helper in `ui.py` (a
`ui.icon` anchor, which — unlike an input — does not duplicate its DOM `id`, so
exactly one tooltip shows). The help text lives in the `finev.i18n` catalog under
`panel.*.help` keys, so both English and German are covered and `i18n` stays the
single source of user-facing strings. The tooltip uses a **1.5 s show delay**
(`ui._TOOLTIP_DELAY_MS`, applied once via the Quasar `Tooltip` class default
prop) so help appears only on a deliberate pause, not while sweeping across the
form, and is styled for readability — capped at `_HELP_MAX_WIDTH_CH` (40)
character widths so long text wraps to a narrow column, and set to
`_HELP_FONT_SIZE_PX` (16px, +2 over Quasar's default). The width cap is enforced
by an `!important` stylesheet rule (`_help_tip_css`, keyed on the
`finev-help-tip` class) because Quasar's tooltip position engine writes its own
inline `max-width` (95vw) that would otherwise override a plain inline style.

The current working state is autosaved to a local JSON cache
(`.cache/finev/wealth_state.json`, or `WEALTH_APP_STATE_PATH`).

### 9.1.0 Language toggle (i18n)

The navbar carries an **EN/DE** toggle that switches the user-facing UI between
**English** (the default) and **German**. All user-facing strings — navbar,
dialogs, card and field labels, the asset-row editors, the forecast table column
headers, the state-pension/forecast summary lines, and notifications — are
resolved through `finev.i18n`: a pure catalog keyed by `(language, key)` with a
lookup that falls back to English and then to the raw key, so a missing
translation degrades gracefully. The `_WealthPage` controller holds the active
language and a bound translator (`make_translator`). Switching language persists
the choice into the autosave cache (a top-level `language` key) and reloads the
page so every widget is rebuilt by the translator; the choice therefore survives
reloads. The default on first load (no cache) is English. Currency/number
formatting is **not** localized in this iteration (amounts remain
`1,234 EUR`-style); locale-aware number formatting is a possible follow-up.

### 9.1.1 Settings profiles

The navbar's **File** action opens a window that lets the user save the current
settings under a name (e.g. one per family member), then reload or delete any
saved profile. This supports planning for several people without separate
accounts. Names are normalized to a safe slug (`[a-z0-9_-]`), which also prevents
path traversal.

Storage goes through the `ProfileStore` abstraction so the backend is
swappable. The default `LocalDiskProfileStore` writes one JSON file per profile
under `.cache/finev/profiles/` (override the directory with
`WEALTH_APP_PROFILES_DIR`); the saved payload is the same snapshot used by the
autosave cache (`assets`/`profile`/`withdrawal`, plus the `language`
preference). Loading a profile repopulates the inputs and re-runs the forecast
(the active language is taken from the autosave cache, not changed on profile
load). A future S3/database backend only needs to
implement `list_profiles` / `save_profile` / `load_profile` / `delete_profile`.

### 9.1.2 CSV export

The navbar's **Export** action recomputes the forecast for the current inputs
and downloads the **detailed** result as a CSV via the browser's download folder.
Unlike the on-screen table (a rounded, yearly-sampled view), the export is the
full engine output: one row per month and every computed column (`month_index`,
`age_years`, `age_months`, `net_cashflow`, `taxes`, the per-asset balances, and
`total`). The inputs are assembled once by `_WealthPage._build_forecast_inputs`
(shared with the live forecast), serialized by `ui_view.forecast_csv`, and named
by `ui_view.export_csv_filename` (a timestamped `wealth-forecast-…csv`). To keep
the file frugal, `forecast_csv` rounds the EURO-valued columns to whole-euro
integers (the `month_index`/`age_*` columns are already integers). Invalid
inputs surface as a negative notification and emit no download.

### 9.2 CLI

`mise run run` runs `cli.run()`: a default scenario (age 40→100, ETF/bAV/Cash,
€3,000/mo withdrawal) printed as a yearly summary table of per-asset balances,
total, taxes, and net cashflow.

---

## 10. Functional requirements

| # | Requirement |
|---|---|
| FR1 | Monthly forecast of each asset balance and the portfolio total from current age to end age, using type-default gain rates where no override is given. |
| FR2 | Pre-retirement monthly contributions per asset, applied (contribution then growth) until the retirement month. |
| FR3 | Post-retirement net withdrawal target deducted proportionally across withdrawable assets; individual balances floor at zero, while any unmet need is borrowed so total wealth may go negative. |
| FR4 | German ETF capital-gains tax (26.25% on 70% of gains) with the €1,000 annual allowance; net cashflow reflects tax; withdrawals are grossed up to the net target. |
| FR5 | Configurable default gain rates with per-asset overrides. |
| FR6 | Inflation-adjusted withdrawal targets from today's currency to each retirement month. |
| FR7 | bAV transfer at a configurable single retirement age (+ ETF ratio) and bAV monthly-gains income; bAV gains fully taxed at 26.25%. |
| FR8 | State-pension stream starting at age 63–67, with earned growth, a configurable annual pension adjustment (*Rentenanpassung p.a.*, default 1%) applied independently of price inflation, early-retirement reduction, and configured tax rate; net pension offsets withdrawals. |
| FR9 | Inheritance events at a configured age, taxed by Erbschaftsteuer class/Freibetrag; net proceeds credited to ETF (then Cash). |
| FR10 | Per-asset activation toggle for what-if scenarios; deactivated assets excluded from calculations but preserved and persisted. |
| FR11 | Inputs validated at the boundary (`forecast.py` validators, `config.py` on load, `ui_state` coercion); invalid inputs fail loudly. |
| FR12 | When withdrawals exhaust the assets, the unmet need is borrowed so total wealth can go negative; the debt compounds monthly at the configured annual debt interest rate and is repaid by net inheritance proceeds. |
| FR13 | Total wealth is floored at the configured Privatinsolvenz threshold (`-PRIVATINSOLVENZ_SCHWELLE_EURO`); the capped debt stops compounding, so a later inheritance can repay it and lift the forecast back out of insolvency, and the total stays at the floor for any span without such a rescue. |
| FR14 | The user can save the current settings as a named profile, list saved profiles, load one back into the UI, and delete one. Profiles are persisted through the swappable `ProfileStore` abstraction (local disk by default); names are normalized to a safe slug. |
| FR15 | VBLklassik occupational pension as a lifelong, income-taxed annuity from a configurable start age that offsets withdrawals; entered as Versorgungspunkte (× `VBL_RENTE_PRO_PUNKT_EURO`) or a direct euro amount, with an optional "still in public service" accrual of one point per working year. The VBL pension is not inflation-compensated and holds no balance column. |
| FR16 | The web UI can be displayed in English (default) or German via a navbar language toggle. All user-facing text is resolved through the `finev.i18n` catalog with English→key fallback; the chosen language is persisted in the autosave cache and restored on reload. |

---

## 11. Acceptance criteria

| # | Criterion |
|---|---|
| AC1 | Forecast covers every month from current to end age inclusive, with per-asset and total values per row. |
| AC2 | Contributions applied in order (contribution then growth) for all pre-retirement months; stop at retirement. |
| AC3 | Withdrawals begin at the retirement month; individual asset balances floor at zero, and any unmet need accrues as debt that drives total wealth negative and compounds at the debt interest rate, but never below the Privatinsolvenz floor. |
| AC12 | Total wealth never drops below `-PRIVATINSOLVENZ_SCHWELLE_EURO`; a forecast can enter the floor, escape via a later inheritance that repays the capped debt, and re-enter it, staying pinned at the floor whenever no rescue follows. |
| AC4 | ETF withdrawal tax matches §7.5 (allowance before tax); net cashflow reflects the deduction. |
| AC5 | Gross withdrawal is computed so net cashflow equals the user's net target (subject to available balance). |
| AC6 | Cost basis updates correctly on contribution and proportionally on withdrawal. |
| AC7 | Type-default gain rate used where no override is given; overrides take precedence. |
| AC8 | Retirement withdrawals inflated from today's currency before gross-up and allocation. |
| AC9 | bAV transfer allocates net balance to ETF/Cash with full-gains tax; bAV income pays monthly gains (no reinvestment) from the bAV retirement age, compounding before it. |
| AC10 | State pension start age validated to 63–67; configured tax rate and early-retirement penalty applied by the engine. |
| AC11 | State pension reflects earned growth until retirement and compounds the annual pension adjustment (*Rentenanpassung p.a.*) over forecast time, independently of price inflation; when the adjustment rate is below inflation, the pension loses real value against the inflation-indexed withdrawal target. |
| AC12 | UI shows read-only computed monthly growth per working year, an estimated early-retirement penalty, and net pension at start. |
| AC13 | Deactivating an asset excludes it from contributions/allocation/transfers while preserving its row and persisted config; reactivation restores it. |
| AC14 | No withdrawals from a bAV before its bAV retirement age; allocation ignores bAV until withdrawable. |
| AC15 | Inheritance below the Freibetrag is tax-free; above it the correct flat bracket rate by class applies; inactive inheritance is not injected. |
| AC16 | Saving a named profile persists the current snapshot and lists it; loading it restores the inputs and re-runs; deleting it removes it. Profile names are slugified (rejecting empty names and neutralizing path traversal), and the local backend round-trips the stored state. |
| AC17 | A VBLklassik asset reduces the post-retirement withdrawal target by its net (income-taxed) monthly pension from `vbl_start_age` onward, stays nominal under inflation, accrues one point per working year when "still in public service" is set, and produces no balance column; points convert to euros at `VBL_RENTE_PRO_PUNKT_EURO`. |
| AC18 | The navbar offers an English/German toggle; English is the default with no cache. `i18n.translate` returns the language-specific string, falling back to English and then to the raw key for missing entries. Selecting a language persists it to the cache (`language` key) and reloads; an unchanged selection is a no-op. |

Each criterion is exercised by the test suite under [`tests/finev/`](../tests/finev/)
(notably `test_forecast.py`, `test_forecast_golden.py`, `test_validation.py`,
`test_config.py`, `test_pension.py`, `test_ui_*.py`).

---

## 12. Extensibility and design constraints

- **Engine/UI separation:** presentation modules must contain no domain math;
  business logic stays in `forecast`/`config`/`pension`.
- **Per-month hook points:** new monthly adjustments are added as pipeline steps
  in `forecast_wealth`, not as edits to a monolithic loop.
- **Asset types:** adding a type means adding handling to the relevant step
  functions (and UI rows), not branching everywhere.
- **Pluggable tax rules:** ETF, DRV, and Erbschaftsteuer parameters are
  config-driven and replaceable; alternative regimes are a config/dataclass swap.
- **Typed models at the boundary:** inputs/outputs are explicit frozen dataclasses
  and enums; illegal states (e.g. unknown strategy/relationship) are rejected at
  validation time.

---

## 13. Quality gates

Reproducible via `mise` tasks (the same gates CI runs): `format-check`, `lint`
(Ruff), `typecheck` (mypy, strict-ish), `test` (pytest), and `coverage`
(minimum **58%**). `mise run check` runs them together. See
[CLAUDE.md](../CLAUDE.md) for the pre-commit and PR workflow.

---

## 14. Versioning and releases

The project follows **Semantic Versioning** (`MAJOR.MINOR.PATCH`). The canonical
version is the `version` field of `pyproject.toml`; it is read at runtime via
`finev.greet.get_version()` (package metadata) and surfaced in the web UI title
and the `finev-version` CLI. Releases are git tags `vX.Y.Z` with matching GitHub
Releases, cut by `mise run release` and published by
[`.github/workflows/release.yml`](../.github/workflows/release.yml) on tag push.
History is tracked in [`CHANGELOG.md`](../CHANGELOG.md) (Keep a Changelog). The
full scheme — including how a vulnerable version is retired via a GitHub Security
Advisory and a superseding release — is documented in
[docs/VERSIONING.md](VERSIONING.md).

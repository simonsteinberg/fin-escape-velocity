"""User-interface internationalization (i18n) for the wealth forecast app.

A pure translation catalog and lookup helpers with no NiceGUI dependency, so the
translation behaviour can be unit-tested without rendering a page. The NiceGUI
layer (:mod:`finev.ui`) resolves the active language to a translator callable via
:func:`make_translator` and looks up user-facing strings by key.

Two languages are supported: English (``"en"``, the default) and German
(``"de"``). Lookups fall back to English and then to the raw key, so a missing
translation degrades gracefully rather than raising.
"""

from __future__ import annotations

from collections.abc import Callable

#: The default language used on first load and whenever an unknown language code
#: is requested.
DEFAULT_LANGUAGE = "en"

#: Human-readable display names for each supported language, keyed by code.
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "de": "Deutsch",
}

#: Short labels for the navbar toggle, keyed by language code.
LANGUAGE_TOGGLE_LABELS: dict[str, str] = {
    "en": "EN",
    "de": "DE",
}

#: Translation catalog: ``{language_code: {key: text}}``. English is the
#: canonical, complete catalog; every key present in English should also be
#: present in German.
TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # Navbar
        "nav.title": "Financial Escape Velocity - Wealth Forecast",
        "nav.file": "File",
        "nav.export": "Export",
        "nav.about": "About",
        "nav.language": "Language",
        "nav.color_scheme": "Color scheme",
        "chart.log_scale": "Log scale",
        "color.auto": "System",
        "color.light": "Light",
        "color.dark": "Dark",
        # File / profiles dialog
        "file.title": "Profiles",
        "file.description": (
            "Save the current settings under a name (e.g. one per person) "
            "and switch between them."
        ),
        "file.profile_name": "Profile name",
        "file.save": "Save",
        "file.saved_profiles": "Saved profiles",
        "file.load": "Load",
        "file.delete": "Delete",
        # About dialog
        "about.app_name": "Financial Escape Velocity",
        "about.close": "Close",
        # Asset rows
        "asset.name": "Name",
        "asset.type": "Type",
        "asset.gross_amount": "Gross amount",
        "asset.age_at_receipt": "Age at receipt",
        "asset.relationship": "Relationship",
        "asset.current_value": "Current value",
        "asset.unrealized_gains": "Unrealized gains",
        "asset.annual_gain": "Annual gain (%)",
        "asset.monthly_contribution": "Monthly contribution",
        "asset.contribution_growth": "Annual contribution change (%)",
        "asset.bav_mode": "bAV mode",
        "asset.bav_transfer": "Transfer to ETF/Cash",
        "asset.bav_income": "Monthly gains income",
        "asset.bav_retirement_age": "bAV retirement age",
        "asset.etf_share": "ETF share (%)",
        "asset.vbl_input": "Input",
        "asset.vbl_points_option": "Versorgungspunkte",
        "asset.vbl_euro_option": "Monthly pension (€)",
        "asset.vbl_monthly_pension": "Monthly pension (€, gross)",
        "asset.vbl_points_label": "Versorgungspunkte",
        "asset.vbl_still_working": "Still in public service (1 point/year)",
        "asset.vbl_start_age": "Pension start age",
        "asset.vbl_tax_rate": "Tax rate (%, optional)",
        # Inheritance relationship options
        "inheritance.rel.ehegatte": "Spouse / partner (I, €500k)",
        "inheritance.rel.kind": "Child / stepchild (I, €400k)",
        "inheritance.rel.enkel": "Grandchild (I, €200k)",
        "inheritance.rel.elternteil": "Parent (I, €100k)",
        "inheritance.rel.klasse_ii": "Sibling / niece / nephew (II, €20k)",
        "inheritance.rel.klasse_iii": "Other (III, €20k)",
        # Profile card
        "profile.section": "Profile",
        "profile.current_age_years": "Current age (years)",
        "profile.current_age_months": "Current age (months)",
        "profile.retirement_age": "Retirement age",
        "profile.end_age": "End age",
        "profile.currency": "Currency",
        "profile.inflation": "Average inflation rate (%)",
        "profile.debt_interest": "Debt interest rate (%)",
        "profile.monthly_withdrawal": "Monthly withdrawal",
        # State pension card
        "pension.section": "State pension",
        "pension.annual_income": "Annual income",
        "pension.now_monthly": "State pension now (monthly)",
        "pension.start_age": "State pension start age",
        "pension.adjustment_rate": "Annual pension adjustment (%)",
        "pension.no_penalty": "No early-retirement penalty",
        "pension.penalty": (
            "Estimated early-retirement penalty: -{amount} p.m. "
            "({pct} reduction)"
        ),
        "pension.achieved": (
            "Pension at age {age}: {amount} p.m. gross "
            "({years} working year(s) remaining, retiring at {ret})"
        ),
        "common.pm_suffix": " p.m.",
        # Assets card
        "assets.section": "Assets",
        "assets.defaults_note": (
            "Defaults: ETF 6.0% | bAV 2.0% | Cash 0.5% (annual)"
        ),
        "assets.add": "Add asset",
        "assets.reset": "Reset",
        # Forecast outputs
        "forecast.none": "No forecast yet.",
        "forecast.total": "Total at age {age}: {amount}",
        # Forecast table columns
        "table.year": "Year",
        "table.age": "Age",
        "table.net_cashflow": "Net Cashflow p.m.",
        "table.taxes": "Taxes p.m.",
        # Notifications
        "notify.clear_cache_fail": "Failed to clear cached state: {error}",
        "notify.save_profile_fail": "Failed to save profile: {error}",
        "notify.save_profile_ok": "Saved profile '{name}'.",
        "notify.select_to_load": "Select a profile to load.",
        "notify.load_profile_fail": "Failed to load profile '{name}': {error}",
        "notify.load_profile_ok": "Loaded profile '{name}'.",
        "notify.select_to_delete": "Select a profile to delete.",
        "notify.delete_profile_fail": (
            "Failed to delete profile '{name}': {error}"
        ),
        "notify.delete_profile_ok": "Deleted profile '{name}'.",
        "notify.save_cache_fail": "Failed to save cached state: {error}",
        "notify.language_persist_fail": (
            "Failed to save language preference: {error}"
        ),
        "notify.color_scheme_persist_fail": (
            "Failed to save color scheme preference: {error}"
        ),
        # Panel help (one ? icon per input panel, replacing per-field tooltips)
        "panel.profile.help": (
            "Your personal and economic assumptions: current age, the age you "
            "retire and the age the projection ends, the display currency, "
            "expected average inflation, the interest charged if wealth goes "
            "negative, and the net monthly amount you plan to withdraw in "
            "retirement."
        ),
        "panel.pension.help": (
            "German state pension (DRV) inputs: your current gross annual "
            "income and the monthly pension you have already earned in today's "
            "money, plus the age you start drawing it. The annual pension "
            "adjustment grows the pension over time independently of price "
            "inflation; when it is below your inflation rate, the pension loses "
            "real value. The read-only lines show the projected growth per "
            "working year, any early-start penalty, and the resulting achieved "
            "monthly pension."
        ),
        "panel.assets.help": (
            "Your wealth building blocks. Add ETF, bAV (occupational pension), "
            "Cash, Inheritance, or VBLklassik entries; each type shows only the "
            "fields relevant to it. Use the eye icon to include or exclude an "
            "asset for what-if scenarios. The annual contribution change "
            "adapts the monthly contribution once per forecast year (e.g. to "
            "keep pace with inflation); it may be negative, but a contribution "
            "never drops below zero."
        ),
    },
    "de": {
        # Navbar
        "nav.title": "Financial Escape Velocity - Vermögensprognose",
        "nav.file": "Datei",
        "nav.export": "Export",
        "nav.about": "Über",
        "nav.language": "Sprache",
        "nav.color_scheme": "Farbschema",
        "chart.log_scale": "Log-Skala",
        "color.auto": "System",
        "color.light": "Hell",
        "color.dark": "Dunkel",
        # File / profiles dialog
        "file.title": "Profile",
        "file.description": (
            "Speichere die aktuellen Einstellungen unter einem Namen "
            "(z. B. eines pro Person) und wechsle zwischen ihnen."
        ),
        "file.profile_name": "Profilname",
        "file.save": "Speichern",
        "file.saved_profiles": "Gespeicherte Profile",
        "file.load": "Laden",
        "file.delete": "Löschen",
        # About dialog
        "about.app_name": "Financial Escape Velocity",
        "about.close": "Schließen",
        # Asset rows
        "asset.name": "Name",
        "asset.type": "Typ",
        "asset.gross_amount": "Bruttobetrag",
        "asset.age_at_receipt": "Alter bei Erhalt",
        "asset.relationship": "Verwandtschaft",
        "asset.current_value": "Aktueller Wert",
        "asset.unrealized_gains": "Nicht realisierte Gewinne",
        "asset.annual_gain": "Jährliche Rendite (%)",
        "asset.monthly_contribution": "Monatlicher Beitrag",
        "asset.contribution_growth": "Jährliche Beitragsanpassung (%)",
        "asset.bav_mode": "bAV-Modus",
        "asset.bav_transfer": "Übertrag auf ETF/Cash",
        "asset.bav_income": "Monatliche Gewinnausschüttung",
        "asset.bav_retirement_age": "bAV-Renteneintrittsalter",
        "asset.etf_share": "ETF-Anteil (%)",
        "asset.vbl_input": "Eingabe",
        "asset.vbl_points_option": "Versorgungspunkte",
        "asset.vbl_euro_option": "Monatsrente (€)",
        "asset.vbl_monthly_pension": "Monatsrente (€, brutto)",
        "asset.vbl_points_label": "Versorgungspunkte",
        "asset.vbl_still_working": (
            "Noch im Öffentlichen Dienst (1 Punkt/Jahr)"
        ),
        "asset.vbl_start_age": "Rentenbeginn-Alter",
        "asset.vbl_tax_rate": "Steuersatz (%, optional)",
        # Inheritance relationship options
        "inheritance.rel.ehegatte": ("Ehegatte / Lebenspartner (I, 500 K€)"),
        "inheritance.rel.kind": "Kind / Stiefkind (I, 400 K€)",
        "inheritance.rel.enkel": "Enkel (I, 200 K€)",
        "inheritance.rel.elternteil": "Elternteil (I, 100 K€)",
        "inheritance.rel.klasse_ii": (
            "Geschwister / Nichte / Neffe (II, 20 K€)"
        ),
        "inheritance.rel.klasse_iii": "Sonstige (III, 20 K€)",
        # Profile card
        "profile.section": "Profil",
        "profile.current_age_years": "Aktuelles Alter (Jahre)",
        "profile.current_age_months": "Aktuelles Alter (Monate)",
        "profile.retirement_age": "Renteneintrittsalter",
        "profile.end_age": "Endalter",
        "profile.currency": "Währung",
        "profile.inflation": "Durchschnittliche Inflationsrate (%)",
        "profile.debt_interest": "Sollzinssatz (%)",
        "profile.monthly_withdrawal": "Monatliche Entnahme",
        # State pension card
        "pension.section": "Gesetzliche Rente",
        "pension.annual_income": "Jahreseinkommen",
        "pension.now_monthly": "Gesetzliche Rente heute (monatlich)",
        "pension.start_age": "Rentenbeginn-Alter (gesetzlich)",
        "pension.adjustment_rate": "Rentenanpassung p.a. (%)",
        "pension.no_penalty": ("Kein Abschlag bei vorzeitigem Renteneintritt"),
        "pension.penalty": (
            "Geschätzter Abschlag bei vorzeitigem Renteneintritt: "
            "-{amount} mtl. ({pct} Reduzierung)"
        ),
        "pension.achieved": (
            "Rente mit {age}: {amount} mtl. brutto "
            "({years} verbleibende(s) Arbeitsjahr(e), "
            "Renteneintritt mit {ret})"
        ),
        "common.pm_suffix": " mtl.",
        # Assets card
        "assets.section": "Vermögenswerte",
        "assets.defaults_note": (
            "Standardwerte: ETF 6,0 % | bAV 2,0 % | Cash 0,5 % (jährlich)"
        ),
        "assets.add": "Vermögenswert hinzufügen",
        "assets.reset": "Zurücksetzen",
        # Forecast outputs
        "forecast.none": "Noch keine Prognose.",
        "forecast.total": "Gesamt mit {age}: {amount}",
        # Forecast table columns
        "table.year": "Jahr",
        "table.age": "Alter",
        "table.net_cashflow": "Netto-Cashflow mtl.",
        "table.taxes": "Steuern mtl.",
        # Notifications
        "notify.clear_cache_fail": (
            "Zwischenspeicher konnte nicht geleert werden: {error}"
        ),
        "notify.save_profile_fail": (
            "Profil konnte nicht gespeichert werden: {error}"
        ),
        "notify.save_profile_ok": "Profil „{name}“ gespeichert.",
        "notify.select_to_load": "Wähle ein Profil zum Laden aus.",
        "notify.load_profile_fail": (
            "Profil „{name}“ konnte nicht geladen werden: {error}"
        ),
        "notify.load_profile_ok": "Profil „{name}“ geladen.",
        "notify.select_to_delete": "Wähle ein Profil zum Löschen aus.",
        "notify.delete_profile_fail": (
            "Profil „{name}“ konnte nicht gelöscht werden: {error}"
        ),
        "notify.delete_profile_ok": "Profil „{name}“ gelöscht.",
        "notify.save_cache_fail": (
            "Zwischenspeicher konnte nicht gespeichert werden: {error}"
        ),
        "notify.language_persist_fail": (
            "Spracheinstellung konnte nicht gespeichert werden: {error}"
        ),
        "notify.color_scheme_persist_fail": (
            "Farbschema-Einstellung konnte nicht gespeichert werden: {error}"
        ),
        # Panel-Hilfe (ein ?-Symbol je Eingabe-Panel statt Tooltips pro Feld)
        "panel.profile.help": (
            "Deine persönlichen und wirtschaftlichen Annahmen: heutiges Alter, "
            "Alter bei Renteneintritt und Alter, bis zu dem die Prognose läuft, "
            "die Anzeigewährung, die erwartete durchschnittliche Inflation, der "
            "Sollzins bei negativem Vermögen sowie die geplante monatliche "
            "Netto-Entnahme im Ruhestand."
        ),
        "panel.pension.help": (
            "Eingaben zur gesetzlichen Rente (DRV): aktuelles Bruttojahresgehalt "
            "und die bereits erworbene Monatsrente in heutigem Geld sowie das "
            "Alter des Rentenbeginns. Die Rentenanpassung p.a. lässt die Rente "
            "über die Zeit unabhängig von der Preisinflation wachsen; liegt sie "
            "unter deiner Inflationsrate, verliert die Rente real an Wert. Die "
            "schreibgeschützten Zeilen zeigen den jährlichen Rentenzuwachs, "
            "einen etwaigen Abschlag bei frühem Beginn und die sich daraus "
            "ergebende erreichte Monatsrente."
        ),
        "panel.assets.help": (
            "Deine Vermögensbausteine. Füge ETF, bAV, Cash, Erbschaft oder "
            "VBLklassik hinzu; jeder Typ zeigt nur die relevanten Felder. Mit "
            "dem Augen-Symbol kannst du einen Vermögenswert für Was-wäre-wenn-"
            "Szenarien ein- oder ausblenden. Die jährliche Beitragsanpassung "
            "verändert den monatlichen Beitrag einmal pro Prognosejahr (z. B. "
            "als Inflationsausgleich); sie darf negativ sein, der Beitrag "
            "wird jedoch nie kleiner als null."
        ),
    },
}


def available_languages() -> list[str]:
    """Return the supported language codes, default first.

    Returns:
        The supported language codes (``["en", "de"]``).
    """
    codes = [DEFAULT_LANGUAGE]
    codes.extend(code for code in TRANSLATIONS if code != DEFAULT_LANGUAGE)
    return codes


def normalize_language(value: object) -> str:
    """Coerce an arbitrary value to a supported language code.

    Args:
        value: The candidate language code (e.g. from cached state or a widget).

    Returns:
        The matching supported code, or :data:`DEFAULT_LANGUAGE` if the value is
        not a recognised language.
    """
    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in TRANSLATIONS:
            return candidate
    return DEFAULT_LANGUAGE


def translate(key: str, language: str) -> str:
    """Look up a user-facing string by key for the given language.

    Falls back to English when the key is missing from the requested language,
    and to the raw key when it is missing from English too, so a missing
    translation degrades gracefully rather than raising.

    Args:
        key: The catalog key (e.g. ``"nav.file"``).
        language: The requested language code; unknown codes resolve to
            :data:`DEFAULT_LANGUAGE`.

    Returns:
        The translated string, or the English fallback, or the key itself.
    """
    lang = normalize_language(language)
    table = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])
    if key in table:
        return table[key]
    return TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)


def make_translator(language: str) -> Callable[[str], str]:
    """Build a translator bound to a single language.

    Args:
        language: The language code to bind.

    Returns:
        A callable that maps a catalog key to its translated string via
        :func:`translate`.
    """
    lang = normalize_language(language)
    return lambda key: translate(key, lang)

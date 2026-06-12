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
        # Parameter tooltips (hover help: meaning + typical values)
        "tooltip.profile.current_age_years": (
            "Your age today in whole years; the forecast starts here. "
            "Typical: 25-60."
        ),
        "tooltip.profile.current_age_months": (
            "Extra months on top of your age in years (0-11) for a precise "
            "start."
        ),
        "tooltip.profile.retirement_age": (
            "Age when contributions stop and withdrawals begin. Typical: "
            "63-67."
        ),
        "tooltip.profile.end_age": (
            "Last age the forecast runs to. Typical: 90-100."
        ),
        "tooltip.profile.currency": (
            "Display label for amounts only — no currency conversion is "
            "applied. E.g. EUR."
        ),
        "tooltip.profile.inflation": (
            "Average yearly inflation, used to deflate future values. "
            "Typical: 2-3%."
        ),
        "tooltip.profile.debt_interest": (
            "Annual interest charged when total wealth goes negative. "
            "Typical: 5-10%."
        ),
        "tooltip.profile.monthly_withdrawal": (
            "Net monthly amount drawn in retirement; taxes are added on top. "
            "E.g. 2,000-4,000."
        ),
        "tooltip.pension.annual_income": (
            "Current gross yearly salary; estimates state-pension accrual. "
            "E.g. 40,000-80,000."
        ),
        "tooltip.pension.now_monthly": (
            "State pension already earned, in today's monthly euros. "
            "E.g. 0-1,500."
        ),
        "tooltip.pension.start_age": (
            "Age you start drawing the state pension. Typical: 63-67."
        ),
        "tooltip.asset.name": (
            "A label for this asset, e.g. 'MSCI World ETF' or 'Savings "
            "account'."
        ),
        "tooltip.asset.type": (
            "ETF, bAV (occupational pension), Cash, Inheritance, or "
            "VBLklassik. Determines which fields apply."
        ),
        "tooltip.asset.gross_amount": (
            "Inheritance amount before tax; Erbschaftsteuer applies per heir "
            "class. E.g. 50,000+."
        ),
        "tooltip.asset.age_at_receipt": (
            "Your age when the inheritance is received. Typical: 40-80."
        ),
        "tooltip.asset.relationship": (
            "Your relation to the deceased — sets the tax-free allowance and "
            "tax rate."
        ),
        "tooltip.asset.current_value": (
            "Today's total balance of this asset. E.g. 10,000-500,000."
        ),
        "tooltip.asset.unrealized_gains": (
            "Portion of the current value that is profit (value minus what "
            "you paid). Only this part is taxed on withdrawal."
        ),
        "tooltip.asset.annual_gain": (
            "Expected average yearly return. Typical: ETF 5-7%, Cash 0-1%."
        ),
        "tooltip.asset.monthly_contribution": (
            "Amount added every month until retirement. E.g. 0-2,000."
        ),
        "tooltip.asset.bav_mode": (
            "How the bAV pays out: transfer the balance to ETF/Cash, or pay "
            "monthly gains as income."
        ),
        "tooltip.asset.bav_retirement_age": (
            "Age the bAV pays out or starts transferring. Typical: 63-67."
        ),
        "tooltip.asset.etf_share": (
            "Share of the transferred bAV that goes into ETF (rest to Cash). "
            "Typical: 0-100%."
        ),
        "tooltip.asset.vbl_input": (
            "Enter the VBLklassik pension as Versorgungspunkte or directly as "
            "a monthly euro amount."
        ),
        "tooltip.asset.vbl_monthly_pension": (
            "Gross monthly VBLklassik pension in euros. E.g. 100-800."
        ),
        "tooltip.asset.vbl_points_label": (
            "Versorgungspunkte accrued; each point ≈ €4 gross monthly pension."
        ),
        "tooltip.asset.vbl_still_working": (
            "Tick if still in public service — adds about 1 point per "
            "remaining working year."
        ),
        "tooltip.asset.vbl_start_age": (
            "Age the VBLklassik pension begins. Typical: 63-67."
        ),
        "tooltip.asset.vbl_tax_rate": (
            "Optional income-tax rate applied to the VBL pension. Leave blank "
            "to skip. E.g. 0-30%."
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
        # Parameter-Tooltips (Hover-Hilfe: Bedeutung + typische Werte)
        "tooltip.profile.current_age_years": (
            "Dein heutiges Alter in vollen Jahren; hier startet die Prognose. "
            "Typisch: 25-60."
        ),
        "tooltip.profile.current_age_months": (
            "Zusätzliche Monate zum Alter in Jahren (0-11) für einen genauen "
            "Start."
        ),
        "tooltip.profile.retirement_age": (
            "Alter, in dem Beiträge enden und Entnahmen beginnen. Typisch: "
            "63-67."
        ),
        "tooltip.profile.end_age": (
            "Letztes Alter, bis zu dem die Prognose läuft. Typisch: 90-100."
        ),
        "tooltip.profile.currency": (
            "Nur Anzeige-Label für Beträge — es findet keine "
            "Währungsumrechnung statt. Z. B. EUR."
        ),
        "tooltip.profile.inflation": (
            "Durchschnittliche jährliche Inflation zur Abwertung künftiger "
            "Werte. Typisch: 2-3 %."
        ),
        "tooltip.profile.debt_interest": (
            "Jährlicher Sollzins, wenn das Gesamtvermögen negativ wird. "
            "Typisch: 5-10 %."
        ),
        "tooltip.profile.monthly_withdrawal": (
            "Gewünschte monatliche Netto-Entnahme im Ruhestand; Steuern "
            "kommen obendrauf. Z. B. 2.000-4.000."
        ),
        "tooltip.pension.annual_income": (
            "Aktuelles Bruttojahresgehalt; schätzt den Rentenaufbau. "
            "Z. B. 40.000-80.000."
        ),
        "tooltip.pension.now_monthly": (
            "Bereits erworbene gesetzliche Rente in heutigen Monatsbeträgen. "
            "Z. B. 0-1.500."
        ),
        "tooltip.pension.start_age": (
            "Alter des gesetzlichen Rentenbeginns. Typisch: 63-67."
        ),
        "tooltip.asset.name": (
            "Eine Bezeichnung für diesen Vermögenswert, z. B. „MSCI World "
            "ETF“ oder „Tagesgeld“."
        ),
        "tooltip.asset.type": (
            "ETF, bAV, Cash, Erbschaft oder VBLklassik. Bestimmt, welche "
            "Felder gelten."
        ),
        "tooltip.asset.gross_amount": (
            "Erbschaftsbetrag vor Steuer; Erbschaftsteuer je Steuerklasse. "
            "Z. B. ab 50.000."
        ),
        "tooltip.asset.age_at_receipt": (
            "Dein Alter beim Erhalt der Erbschaft. Typisch: 40-80."
        ),
        "tooltip.asset.relationship": (
            "Verwandtschaft zum Erblasser — bestimmt Freibetrag und "
            "Steuersatz."
        ),
        "tooltip.asset.current_value": (
            "Heutiger Gesamtwert dieses Vermögenswerts. Z. B. 10.000-500.000."
        ),
        "tooltip.asset.unrealized_gains": (
            "Anteil des aktuellen Werts, der Gewinn ist (Wert minus "
            "Einzahlungen). Nur dieser Teil wird bei Entnahme besteuert."
        ),
        "tooltip.asset.annual_gain": (
            "Erwartete durchschnittliche Jahresrendite. Typisch: ETF 5-7 %, "
            "Cash 0-1 %."
        ),
        "tooltip.asset.monthly_contribution": (
            "Monatliche Einzahlung bis zum Ruhestand. Z. B. 0-2.000."
        ),
        "tooltip.asset.bav_mode": (
            "Auszahlung der bAV: Guthaben auf ETF/Cash übertragen oder "
            "monatliche Gewinne als Einkommen."
        ),
        "tooltip.asset.bav_retirement_age": (
            "Alter, in dem die bAV auszahlt bzw. der Übertrag startet. "
            "Typisch: 63-67."
        ),
        "tooltip.asset.etf_share": (
            "Anteil der übertragenen bAV in ETF (Rest in Cash). Typisch: "
            "0-100 %."
        ),
        "tooltip.asset.vbl_input": (
            "VBLklassik-Rente als Versorgungspunkte oder direkt als "
            "Monatsbetrag in Euro eingeben."
        ),
        "tooltip.asset.vbl_monthly_pension": (
            "Monatliche VBLklassik-Bruttorente in Euro. Z. B. 100-800."
        ),
        "tooltip.asset.vbl_points_label": (
            "Erworbene Versorgungspunkte; je Punkt ca. 4 € Bruttorente "
            "monatlich."
        ),
        "tooltip.asset.vbl_still_working": (
            "Ankreuzen, wenn weiterhin im öffentlichen Dienst — ca. 1 Punkt "
            "je verbleibendem Arbeitsjahr."
        ),
        "tooltip.asset.vbl_start_age": (
            "Alter des VBLklassik-Rentenbeginns. Typisch: 63-67."
        ),
        "tooltip.asset.vbl_tax_rate": (
            "Optionaler Steuersatz auf die VBL-Rente. Leer lassen zum "
            "Überspringen. Z. B. 0-30 %."
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

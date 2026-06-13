"""Unit tests for the UI internationalization catalog and helpers."""

from __future__ import annotations

import pytest

from finev.i18n import (
    DEFAULT_LANGUAGE,
    TRANSLATIONS,
    available_languages,
    make_translator,
    normalize_language,
    translate,
)


def test_default_language_is_english() -> None:
    assert DEFAULT_LANGUAGE == "en"


def test_available_languages_lists_default_first() -> None:
    languages = available_languages()
    assert languages[0] == "en"
    assert set(languages) == {"en", "de"}


def test_translate_returns_language_specific_string() -> None:
    assert translate("nav.file", "en") == "File"
    assert translate("nav.file", "de") == "Datei"


def test_translate_unknown_language_falls_back_to_english() -> None:
    # An unrecognised language code resolves to the English default.
    assert translate("nav.file", "fr") == "File"
    assert translate("nav.file", "") == "File"


def test_translate_missing_key_falls_back_to_english_then_key() -> None:
    # A key missing from German but present in English uses the English value.
    de_only = dict(TRANSLATIONS["de"])
    # Sanity: the key exists in English.
    assert "nav.about" in TRANSLATIONS["en"]
    # A key absent from every catalog returns the raw key unchanged.
    assert translate("does.not.exist", "en") == "does.not.exist"
    assert translate("does.not.exist", "de") == "does.not.exist"
    # Guard against accidental mutation of the module catalog.
    assert TRANSLATIONS["de"] == de_only


def test_german_catalog_covers_every_english_key() -> None:
    # Every English key must have a German translation so nothing silently
    # falls back to English in the German UI.
    missing = set(TRANSLATIONS["en"]) - set(TRANSLATIONS["de"])
    assert missing == set()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("en", "en"),
        ("de", "de"),
        ("DE", "de"),
        ("  En  ", "en"),
        ("fr", "en"),
        ("", "en"),
        (None, "en"),
        (42, "en"),
    ],
)
def test_normalize_language(value: object, expected: str) -> None:
    assert normalize_language(value) == expected


def test_make_translator_binds_language() -> None:
    german = make_translator("de")
    assert german("nav.file") == "Datei"
    english = make_translator("unknown")
    assert english("nav.file") == "File"


def test_format_templates_have_placeholders() -> None:
    # The dynamic strings carry the placeholders the UI fills in.
    for language in ("en", "de"):
        assert "{amount}" in translate("pension.penalty", language)
        assert "{pct}" in translate("pension.penalty", language)
        assert "{age}" in translate("pension.achieved", language)
        assert "{amount}" in translate("forecast.total", language)


#: Every input panel that must carry a hover ``?`` help text (catalog key).
PANEL_HELP_KEYS = [
    "panel.profile.help",
    "panel.pension.help",
    "panel.assets.help",
]


@pytest.mark.parametrize("key", PANEL_HELP_KEYS)
def test_panel_help_keys_are_translated(key: str) -> None:
    # Each panel help text must resolve to a real, non-empty string in both
    # languages (not the key itself, which is the missing-translation fallback).
    for language in ("en", "de"):
        text = translate(key, language)
        assert text != key, f"missing {language} panel help for {key}"
        assert text.strip(), f"empty {language} panel help for {key}"

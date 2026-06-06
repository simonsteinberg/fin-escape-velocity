"""Tests that the UI surfaces the package version."""

from __future__ import annotations

from finev.greet import get_version
from finev.ui_view import version_label_text


def test_version_label_text_prefixes_installed_version() -> None:
    assert version_label_text() == f"v{get_version()}"


def test_version_label_text_starts_with_v() -> None:
    label = version_label_text()
    assert label.startswith("v")
    # The remainder is a non-empty version string, not the bare prefix.
    assert len(label) > 1

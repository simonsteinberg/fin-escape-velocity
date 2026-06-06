"""Unit tests for the named settings-profile store."""

from __future__ import annotations

from pathlib import Path

import pytest

from finev.profile_store import (
    LocalDiskProfileStore,
    default_profiles_dir,
    normalize_profile_name,
)


def test_normalize_profile_name_slugifies() -> None:
    assert normalize_profile_name("My Wife") == "my-wife"
    assert normalize_profile_name("  Brother_2  ") == "brother_2"
    assert normalize_profile_name("Kind #1!") == "kind-1"


def test_normalize_profile_name_rejects_empty() -> None:
    with pytest.raises(ValueError, match="at least one letter or digit"):
        normalize_profile_name("   ")
    with pytest.raises(ValueError, match="at least one letter or digit"):
        normalize_profile_name("!!!")


def test_normalize_profile_name_neutralizes_path_traversal() -> None:
    # Path separators and ".." are stripped, so a name can never escape the dir.
    assert normalize_profile_name("../../etc/passwd") == "etc-passwd"
    assert "/" not in normalize_profile_name("a/b/c")


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    store = LocalDiskProfileStore(tmp_path)
    state = {"profile": {"current_age_years": 41}, "assets": []}

    store.save_profile("wife", state)

    assert store.load_profile("wife") == state


def test_save_overwrites_existing(tmp_path: Path) -> None:
    store = LocalDiskProfileStore(tmp_path)
    store.save_profile("me", {"v": 1})
    store.save_profile("me", {"v": 2})

    assert store.load_profile("me") == {"v": 2}
    assert store.list_profiles() == ["me"]


def test_list_profiles_sorted(tmp_path: Path) -> None:
    store = LocalDiskProfileStore(tmp_path)
    store.save_profile("wife", {})
    store.save_profile("brother", {})
    store.save_profile("child", {})

    assert store.list_profiles() == ["brother", "child", "wife"]


def test_list_profiles_empty_when_dir_missing(tmp_path: Path) -> None:
    store = LocalDiskProfileStore(tmp_path / "does-not-exist")

    assert store.list_profiles() == []


def test_load_missing_raises(tmp_path: Path) -> None:
    store = LocalDiskProfileStore(tmp_path)

    with pytest.raises(FileNotFoundError, match="No profile named 'ghost'"):
        store.load_profile("ghost")


def test_load_rejects_non_object_payload(tmp_path: Path) -> None:
    store = LocalDiskProfileStore(tmp_path)
    (tmp_path / "broken.json").write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a JSON object"):
        store.load_profile("broken")


def test_delete_removes_profile(tmp_path: Path) -> None:
    store = LocalDiskProfileStore(tmp_path)
    store.save_profile("temp", {})

    store.delete_profile("temp")

    assert store.list_profiles() == []


def test_delete_missing_raises(tmp_path: Path) -> None:
    store = LocalDiskProfileStore(tmp_path)

    with pytest.raises(FileNotFoundError, match="No profile named 'ghost'"):
        store.delete_profile("ghost")


def test_name_is_normalized_on_save_and_load(tmp_path: Path) -> None:
    store = LocalDiskProfileStore(tmp_path)
    store.save_profile("My Wife", {"x": 1})

    # The slug is what gets listed, and the original (normalizable) name loads.
    assert store.list_profiles() == ["my-wife"]
    assert store.load_profile("My Wife") == {"x": 1}


def test_default_profiles_dir_honours_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WEALTH_APP_PROFILES_DIR", str(tmp_path / "p"))

    assert default_profiles_dir() == tmp_path / "p"

"""Named settings-profile storage with a pluggable backend.

The wealth app autosaves a single working state to a JSON cache (see
:mod:`finev.ui_state`). This module adds *named* profiles on top of that so a
user can keep separate scenarios — for example one per family member — and
switch between them.

The :class:`ProfileStore` abstraction decouples the UI from where profiles
live. :class:`LocalDiskProfileStore` persists each profile as a JSON file in a
directory; a future backend (S3, a database, ...) only has to implement the
same four methods.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

_NAME_RE = re.compile(r"[^a-z0-9_-]+")


def normalize_profile_name(raw: str) -> str:
    """Normalize a user-supplied profile name into a safe identifier.

    Lower-cases the name and collapses any run of unsupported characters into a
    single hyphen, yielding a slug usable as a filename or object key across
    backends. Because everything outside ``[a-z0-9_-]`` is stripped, the result
    can never contain path separators or ``..``, so it is safe to use directly
    in a filesystem path.

    Args:
        raw: The raw name typed by the user.

    Returns:
        A non-empty slug containing only ``[a-z0-9_-]``.

    Raises:
        ValueError: If the name has no usable characters.
    """
    slug = _NAME_RE.sub("-", raw.strip().lower()).strip("-")
    if not slug:
        raise ValueError(
            "Profile name must contain at least one letter or digit"
        )
    return slug


class ProfileStore(ABC):
    """Storage backend for named settings profiles."""

    @abstractmethod
    def list_profiles(self) -> list[str]:
        """Return the saved profile names, sorted."""

    @abstractmethod
    def save_profile(self, name: str, state: dict[str, Any]) -> None:
        """Persist ``state`` under ``name``, overwriting any existing profile.

        Args:
            name: Profile identifier.
            state: The serializable UI state snapshot to store.
        """

    @abstractmethod
    def load_profile(self, name: str) -> dict[str, Any]:
        """Return the state stored under ``name``.

        Args:
            name: Profile identifier.

        Returns:
            The stored state dictionary.

        Raises:
            FileNotFoundError: If no profile with that name exists.
            ValueError: If the stored payload is not a JSON object.
        """

    @abstractmethod
    def delete_profile(self, name: str) -> None:
        """Remove the profile ``name``.

        Args:
            name: Profile identifier.

        Raises:
            FileNotFoundError: If no profile with that name exists.
        """


class LocalDiskProfileStore(ProfileStore):
    """A :class:`ProfileStore` that keeps one JSON file per profile."""

    def __init__(self, directory: Path) -> None:
        """Initialize the store.

        Args:
            directory: Directory holding the ``<name>.json`` profile files. It
                is created lazily on the first save.
        """
        self._directory = directory

    def _path(self, name: str) -> Path:
        """Return the file path for ``name``, normalizing it to a safe slug."""
        return self._directory / f"{normalize_profile_name(name)}.json"

    def list_profiles(self) -> list[str]:
        if not self._directory.exists():
            return []
        return sorted(path.stem for path in self._directory.glob("*.json"))

    def save_profile(self, name: str, state: dict[str, Any]) -> None:
        path = self._path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)

    def load_profile(self, name: str) -> dict[str, Any]:
        path = self._path(name)
        if not path.exists():
            raise FileNotFoundError(f"No profile named '{name}'")
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("Profile payload must be a JSON object")
        return data

    def delete_profile(self, name: str) -> None:
        path = self._path(name)
        if not path.exists():
            raise FileNotFoundError(f"No profile named '{name}'")
        path.unlink()


def default_profiles_dir() -> Path:
    """Return the directory used for local profile storage.

    Honours ``WEALTH_APP_PROFILES_DIR``; otherwise defaults to
    ``.cache/finev/profiles`` under the repository root.
    """
    env_path = os.getenv("WEALTH_APP_PROFILES_DIR")
    if env_path:
        return Path(env_path).expanduser()
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / ".cache" / "finev" / "profiles"


def default_profile_store() -> ProfileStore:
    """Return the default local-disk profile store."""
    return LocalDiskProfileStore(default_profiles_dir())

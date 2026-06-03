"""Tiny version/greeting entry point (``finev-version`` console script)."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

_FALLBACK_VERSION = "0.0.0"


def get_version() -> str:
    """Return the installed package version.

    Uses installed package metadata so it works from a wheel as well as an
    editable install, instead of reading ``pyproject.toml`` from a fixed
    relative path.

    Returns:
        The ``finev`` version string, or ``"0.0.0"`` if the package metadata is
        not available (e.g. running from a source tree that was never installed).
    """
    try:
        return version("finev")
    except PackageNotFoundError:
        return _FALLBACK_VERSION


def main() -> None:
    """Print a greeting with the current package version."""
    print(f"Hello finev (version {get_version()})")


if __name__ == "__main__":
    main()

"""End-to-end tests for the runnable entry points.

These exercise the exact code paths invoked by ``mise run run`` and
``mise run app`` — running ``python -m finev.cli`` and ``python -m finev.app``
as real subprocesses through their ``__main__`` guards — rather than calling the
functions in-process. They are the closest automated equivalent of a developer
typing the two ``mise`` commands.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

#: Generous ceilings: the forecast itself is fast, but a cold subprocess start
#: (interpreter + imports, and the NiceGUI server boot) needs headroom on a
#: loaded CI machine.
_CLI_TIMEOUT_S = 60
_APP_BOOT_TIMEOUT_S = 40
_APP_SHUTDOWN_TIMEOUT_S = 10


def _free_port() -> int:
    """Reserve a currently-free localhost TCP port and return its number.

    The socket is closed before returning, so there is a small race window; the
    app entry point tolerates it by retrying the next port on ``EADDRINUSE``.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _isolated_env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    """Copy the environment and point persisted state at a temp directory.

    Keeps the subprocess from touching the repo's real autosave cache or
    profiles directory.
    """
    env = os.environ.copy()
    # NiceGUI's ui.run switches to screen-test mode when PYTEST_CURRENT_TEST is
    # set; drop it so the subprocess behaves like a real ``mise run`` launch.
    env.pop("PYTEST_CURRENT_TEST", None)
    env["WEALTH_APP_STATE_PATH"] = str(tmp_path / "state.json")
    env["WEALTH_APP_PROFILES_DIR"] = str(tmp_path / "profiles")
    env.update(overrides)
    return env


@pytest.mark.e2e
def test_cli_entrypoint_prints_forecast(tmp_path: Path) -> None:
    """``python -m finev.cli`` (i.e. ``mise run run``) prints the forecast."""
    result = subprocess.run(
        [sys.executable, "-m", "finev.cli"],
        capture_output=True,
        text=True,
        timeout=_CLI_TIMEOUT_S,
        env=_isolated_env(tmp_path),
        cwd=Path(__file__).resolve().parents[2],
    )

    assert result.returncode == 0, result.stderr
    # The default scenario's assets and the summary columns are all printed.
    for token in ("ETF MSCI World", "Notgroschen", "total", "EUR"):
        assert token in result.stdout
    # The header plus one row per age-year (30→100 inclusive) is a lot of rows.
    assert len(result.stdout.strip().splitlines()) > 60


@pytest.mark.e2e
def test_app_entrypoint_serves_the_page(tmp_path: Path) -> None:
    """``python -m finev.app`` (i.e. ``mise run app``) boots and serves ``/``."""
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "finev.app"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=_isolated_env(tmp_path, WEALTH_APP_PORT=str(port)),
        cwd=Path(__file__).resolve().parents[2],
    )
    try:
        url = f"http://127.0.0.1:{port}/"
        body: str | None = None
        deadline = time.monotonic() + _APP_BOOT_TIMEOUT_S
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                output = proc.stdout.read() if proc.stdout else ""
                pytest.fail(
                    f"app exited early (code {proc.returncode}):\n{output}"
                )
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    assert response.status == 200
                    body = response.read().decode("utf-8", "replace")
                break
            except (urllib.error.URLError, ConnectionError, OSError):
                time.sleep(0.3)

        assert body is not None, "app server never answered on its port"
        # A successful 200 means the page builder (build_wealth_page) ran without
        # raising; the NiceGUI bootstrap and the app title confirm it is our app.
        assert "nicegui" in body.lower()
        assert "Financial Escape Velocity" in body
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=_APP_SHUTDOWN_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

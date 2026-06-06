"""Wealth forecast NiceGUI application entrypoint."""

from __future__ import annotations

import errno
import os

from nicegui import ui

from finev.ui import build_wealth_page


def register_routes() -> None:
    """Register wealth forecast page routes."""

    @ui.page("/")
    def index_page() -> None:
        """Render the main wealth forecast page."""
        build_wealth_page()


def _candidate_ports(start_port: int, max_attempts: int) -> list[int]:
    """Build a list of candidate ports starting from the given port.

    Args:
        start_port: Port number to start searching from.
        max_attempts: Maximum number of ports to try.

    Returns:
        List of candidate ports to try.
    """
    return [start_port + offset for offset in range(max_attempts)]


def main() -> None:
    """Launch the wealth forecast server."""
    register_routes()
    port_value = os.getenv("WEALTH_APP_PORT", "8081")
    try:
        base_port = int(port_value)
    except ValueError as exc:
        raise ValueError("WEALTH_APP_PORT must be an integer") from exc
    if base_port <= 0:
        raise ValueError("WEALTH_APP_PORT must be a positive integer")
    candidate_ports = _candidate_ports(base_port, max_attempts=50)
    last_error: OSError | None = None
    for port in candidate_ports:
        try:
            ui.run(
                host="0.0.0.0",
                port=port,
                title="Financial Escape Velocity - Wealth Forecast",
                reload=False,
                show=False,
            )
            return
        except OSError as exc:
            last_error = exc
            if exc.errno == errno.EADDRINUSE:
                continue
            raise

    if last_error is not None:
        raise RuntimeError(
            "No available port found starting at "
            f"{base_port} after {len(candidate_ports)} attempts."
        ) from last_error


if __name__ == "__main__":
    main()

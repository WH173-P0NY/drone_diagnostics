"""Helpers for establishing MAVLink connections."""

from pymavlink import mavutil


DEFAULT_BAUD = 115200
DEFAULT_HEARTBEAT_TIMEOUT = 30.0


class ConnectionError(Exception):
    """Base error raised while establishing a MAVLink connection."""


class ConnectionOpenError(ConnectionError):
    """The serial device could not be opened."""


class HeartbeatTimeoutError(ConnectionError):
    """No MAVLink heartbeat arrived before the configured timeout."""


def connect(
    device: str,
    baud: int = DEFAULT_BAUD,
    heartbeat_timeout: float = DEFAULT_HEARTBEAT_TIMEOUT,
):
    """Open a MAVLink serial connection and wait for its first heartbeat.

    Args:
        device: Serial device path, such as ``/dev/ttyACM0``.
        baud: Serial baud rate. Defaults to 115200.
        heartbeat_timeout: Maximum seconds to wait for a heartbeat. Defaults
            to 30 seconds.

    Returns:
        The pymavlink connection, with ``target_system`` and
        ``target_component`` populated from the heartbeat.

    Raises:
        ValueError: If the heartbeat timeout is not positive.
        ConnectionOpenError: If pymavlink cannot open the device.
        HeartbeatTimeoutError: If no heartbeat arrives before the timeout.
    """
    if heartbeat_timeout <= 0:
        raise ValueError("heartbeat_timeout must be greater than zero")

    try:
        connection = mavutil.mavlink_connection(device, baud=baud)
    except Exception as exc:
        raise ConnectionOpenError(
            f"Could not open MAVLink device {device!r}: {exc}"
        ) from exc

    try:
        heartbeat = connection.wait_heartbeat(timeout=heartbeat_timeout)
    except Exception as exc:
        _close_quietly(connection)
        raise HeartbeatTimeoutError(
            f"Failed waiting for a heartbeat from {device!r} "
            f"within {heartbeat_timeout:g} seconds: {exc}"
        ) from exc

    if heartbeat is None:
        _close_quietly(connection)
        raise HeartbeatTimeoutError(
            f"No heartbeat received from {device!r} "
            f"within {heartbeat_timeout:g} seconds"
        )

    return connection


def _close_quietly(connection) -> None:
    close = getattr(connection, "close", None)
    if close is not None:
        try:
            close()
        except Exception:
            pass

from unittest.mock import Mock, patch

import pytest

from drone_diagnostics.mavlink.connection import (
    DEFAULT_BAUD,
    DEFAULT_HEARTBEAT_TIMEOUT,
    ConnectionOpenError,
    HeartbeatTimeoutError,
    connect,
)


@patch("drone_diagnostics.mavlink.connection.mavutil.mavlink_connection")
def test_connect_returns_connection_and_target_ids_without_printing(
    mavlink_connection, capsys
):
    connection = Mock()
    connection.wait_heartbeat.return_value = Mock()
    connection.target_system = 42
    connection.target_component = 7
    mavlink_connection.return_value = connection

    result = connect("/dev/ttyACM0")

    assert result is connection
    assert (result.target_system, result.target_component) == (42, 7)
    mavlink_connection.assert_called_once_with(
        "/dev/ttyACM0", baud=DEFAULT_BAUD
    )
    connection.wait_heartbeat.assert_called_once_with(
        timeout=DEFAULT_HEARTBEAT_TIMEOUT
    )
    assert capsys.readouterr().out == ""


@patch("drone_diagnostics.mavlink.connection.mavutil.mavlink_connection")
def test_connect_passes_configured_baud_and_heartbeat_timeout(mavlink_connection):
    connection = Mock()
    connection.wait_heartbeat.return_value = Mock()
    mavlink_connection.return_value = connection

    connect("/dev/ttyUSB1", baud=57600, heartbeat_timeout=8.5)

    mavlink_connection.assert_called_once_with("/dev/ttyUSB1", baud=57600)
    connection.wait_heartbeat.assert_called_once_with(timeout=8.5)


@patch("drone_diagnostics.mavlink.connection.mavutil.mavlink_connection")
def test_connect_raises_actionable_error_when_heartbeat_times_out(
    mavlink_connection,
):
    connection = Mock()
    connection.wait_heartbeat.return_value = None
    mavlink_connection.return_value = connection

    with pytest.raises(HeartbeatTimeoutError, match="/dev/ttyACM0") as error:
        connect("/dev/ttyACM0", heartbeat_timeout=2)

    assert "2 seconds" in str(error.value)
    connection.close.assert_called_once_with()


@patch("drone_diagnostics.mavlink.connection.mavutil.mavlink_connection")
def test_connect_wraps_serial_open_failure(mavlink_connection):
    mavlink_connection.side_effect = OSError("permission denied")

    with pytest.raises(ConnectionOpenError) as error:
        connect("/dev/ttyACM0")

    assert "/dev/ttyACM0" in str(error.value)
    assert "permission denied" in str(error.value)
    mavlink_connection.assert_called_once_with("/dev/ttyACM0", baud=DEFAULT_BAUD)


@patch("drone_diagnostics.mavlink.connection.mavutil.mavlink_connection")
def test_connect_closes_connection_if_wait_for_heartbeat_raises(mavlink_connection):
    connection = Mock()
    connection.wait_heartbeat.side_effect = OSError("read failed")
    mavlink_connection.return_value = connection

    with pytest.raises(HeartbeatTimeoutError, match="read failed"):
        connect("/dev/ttyACM0", heartbeat_timeout=1)

    connection.close.assert_called_once_with()

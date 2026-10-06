from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from drone_diagnostics.mavlink.parameters import (
    ParameterDownloadError,
    get_all_params,
    get_param,
)


def parameter(name, value, index=0, count=1):
    return SimpleNamespace(
        param_id=name,
        param_value=value,
        param_index=index,
        param_count=count,
    )


def connection_with_messages(*messages):
    connection = Mock()
    connection.target_system = 3
    connection.target_component = 1
    connection.recv_match.side_effect = [*messages]
    return connection


def test_get_param_requests_named_parameter_and_normalizes_bytes_id():
    connection = connection_with_messages(
        parameter(b"OTHER\x00", 1),
        parameter(b"ALT_HOLD_RTL\x00", 2.5),
    )

    assert get_param(connection, "ALT_HOLD_RTL") == 2.5
    connection.mav.param_request_read_send.assert_called_once_with(
        3, 1, b"ALT_HOLD_RTL", -1
    )
    assert [item.kwargs["type"] for item in connection.recv_match.call_args_list] == [
        "PARAM_VALUE",
        "PARAM_VALUE",
    ]


def test_get_param_timeout_is_total_across_unrelated_values(monkeypatch):
    connection = connection_with_messages(
        parameter("OTHER", 1),
        None,
    )
    times = iter([10.0, 10.0, 12.0])
    monkeypatch.setattr("drone_diagnostics.mavlink.parameters.time.monotonic", lambda: next(times))

    assert get_param(connection, "WANTED", timeout=3) is None
    assert connection.recv_match.call_args_list == [
        call(type="PARAM_VALUE", blocking=True, timeout=3.0),
        call(type="PARAM_VALUE", blocking=True, timeout=1.0),
    ]


def test_get_param_returns_none_when_response_times_out():
    connection = connection_with_messages(None)

    assert get_param(connection, "MISSING", timeout=0.1) is None


def test_get_all_params_handles_out_of_order_and_duplicate_responses():
    connection = connection_with_messages(
        parameter(b"THIRD\x00", 3, index=2, count=3),
        parameter("FIRST", 1, index=0, count=3),
        parameter("FIRST", 1.5, index=0, count=3),
        parameter("SECOND", 2, index=1, count=3),
    )

    assert get_all_params(connection, timeout=5) == {
        "FIRST": 1.5,
        "SECOND": 2,
        "THIRD": 3,
    }
    connection.mav.param_request_list_send.assert_called_once_with(3, 1)
    assert all(call.kwargs["timeout"] <= 5 for call in connection.recv_match.call_args_list)


def test_get_all_params_raises_with_missing_indices_on_incomplete_list():
    connection = connection_with_messages(
        parameter("FIRST", 1, index=0, count=3),
        None,
    )

    with pytest.raises(ParameterDownloadError, match="missing parameter indices") as error:
        get_all_params(connection, timeout=0.1)

    assert error.value.missing_indices == {1, 2}


def test_get_all_params_timeout_without_any_response_is_actionable():
    connection = connection_with_messages(None)

    with pytest.raises(ParameterDownloadError, match="no complete parameter list"):
        get_all_params(connection, timeout=0.1)

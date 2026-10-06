"""Bounded MAVLink parameter read helpers."""

import time


class ParameterDownloadError(TimeoutError):
    """A parameter list was not complete before its overall deadline."""

    def __init__(self, timeout: float, missing_indices: set[int] | None = None):
        self.timeout = timeout
        self.missing_indices = missing_indices
        if missing_indices is None:
            detail = "no complete parameter list was received"
        else:
            detail = f"missing parameter indices: {sorted(missing_indices)}"
        super().__init__(f"Parameter download timed out after {timeout:g}s; {detail}")


def _normalize_param_id(param_id: str | bytes) -> str:
    if isinstance(param_id, bytes):
        param_id = param_id.decode("utf-8", errors="replace")
    return param_id.rstrip("\x00")


def _validate_timeout(timeout: float) -> None:
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")


def get_param(connection, name: str, timeout: float = 3.0):
    """Request one parameter and return its value, or ``None`` on timeout.

    ``timeout`` is the total time allowed for the response, including time
    spent discarding unrelated parameter values.
    """
    _validate_timeout(timeout)
    connection.mav.param_request_read_send(
        connection.target_system,
        connection.target_component,
        name.encode("utf-8"),
        -1,
    )

    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        msg = connection.recv_match(
            type="PARAM_VALUE",
            blocking=True,
            timeout=remaining,
        )
        if msg is None:
            return None
        if _normalize_param_id(msg.param_id) == name:
            return msg.param_value


def get_all_params(connection, timeout: float = 30.0) -> dict[str, float]:
    """Download a complete parameter list within one overall timeout.

    Responses may arrive out of order or more than once. Completion is based
    on receiving every ``param_index`` in the advertised ``param_count``.
    Raises :class:`ParameterDownloadError` on timeout rather than returning a
    partial dictionary. The default overall timeout is 30 seconds.
    """
    _validate_timeout(timeout)
    connection.mav.param_request_list_send(
        connection.target_system,
        connection.target_component,
    )

    deadline = time.monotonic() + timeout
    indexed_params: dict[int, tuple[str, float]] = {}
    expected_count = None

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            missing = None
            if expected_count is not None:
                missing = set(range(expected_count)) - indexed_params.keys()
            raise ParameterDownloadError(timeout, missing)

        msg = connection.recv_match(
            type="PARAM_VALUE",
            blocking=True,
            timeout=remaining,
        )
        if msg is None:
            missing = None
            if expected_count is not None:
                missing = set(range(expected_count)) - indexed_params.keys()
            raise ParameterDownloadError(timeout, missing)

        count = int(msg.param_count)
        index = int(msg.param_index)
        if count < 0 or index < 0 or index >= count:
            continue

        if expected_count is None:
            expected_count = count
        elif count != expected_count:
            # Ignore inconsistent/stale packets; the first valid response
            # defines the list advertised for this request.
            continue

        indexed_params[index] = (
            _normalize_param_id(msg.param_id),
            msg.param_value,
        )
        if len(indexed_params) == expected_count:
            return {name: value for name, value in indexed_params.values()}

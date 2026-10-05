def get_param(connection, name: str, timeout: float = 3.0):
    connection.mav.param_request_read_send(
        connection.target_system,
        connection.target_component,
        name.encode("utf-8"),
        -1
    )

    while True:
        msg = connection.recv_match(
            type="PARAM_VALUE",
            blocking=True,
            timeout=timeout
        )

        if msg is None:
            return None

        param_name = msg.param_id

        if isinstance(param_name, bytes):
            param_name = param_name.decode("utf-8")

        param_name = param_name.rstrip("\x00")

        if param_name == name:
            return msg.param_value

def get_all_params(connection, timeout: float = 5.0) -> dict[str, float]:
    connection.mav.param_request_list_send(
        connection.target_system,
        connection.target_component
    )

    params = {}

    while True:
        msg = connection.recv_match(
            type="PARAM_VALUE",
            blocking=True,
            timeout=timeout
        )

        if msg is None:
            break

        param_name = msg.param_id

        if isinstance(param_name, bytes):
            param_name = param_name.decode("utf-8")

        param_name = param_name.rstrip("\x00")

        params[param_name] = msg.param_value

    return params

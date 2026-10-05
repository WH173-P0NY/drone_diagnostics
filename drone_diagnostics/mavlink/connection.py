from pymavlink import mavutil


def connect(device: str, baud: int = 115200):
    connection = mavutil.mavlink_connection(
        device,
        baud=baud
    )

    print(f"Connecting to {device}...")
    connection.wait_heartbeat()

    print(
        f"Connected: system={connection.target_system}, "
        f"component={connection.target_component}"
    )

    return connection

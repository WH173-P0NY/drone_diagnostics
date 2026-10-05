import json

from drone_diagnostics.mavlink.connection import connect
from drone_diagnostics.mavlink.parameters import get_all_params


def main():
    connection = connect("/dev/ttyACM0")

    params = get_all_params(connection)

    print(f"Downloaded {len(params)} parameters")

    with open("params_snapshot.json", "w") as file:
        json.dump(
            params,
            file,
            indent=4,
            sort_keys=True
        )

    print("Saved to params_snapshot.json")


if __name__ == "__main__":
    main()

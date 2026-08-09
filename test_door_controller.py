import time

import RPi.GPIO as GPIO

from config import MOCK_DOOR_CYCLE_SECONDS
from database.database import Database
from hardware.relay_controller import RelayController
from hardware.buzzer_controller import BuzzerController
from hardware.mock_door import MockDoorSensor
from core.door_controller import DoorController, DoorState


database = Database()
relay = RelayController()
buzzer = BuzzerController()
door = MockDoorSensor(MOCK_DOOR_CYCLE_SECONDS)
controller = DoorController(relay, buzzer, door, database)

try:
    print("Initial state:", controller.state.value)

    door.simulate_unlock_cycle()

    accepted = controller.request_unlock(
        reason="test_access",
        uid="9E-24-41-06",
    )

    print("Unlock requested:", accepted)

    deadline = time.monotonic() + 10

    while controller.state != DoorState.LOCKED:
        controller.update()

        print(
            "State:",
            controller.state.value,
            "| Door closed:",
            door.is_closed(),
        )

        if time.monotonic() > deadline:
            raise TimeoutError(
                "Door controller did not return to locked state"
            )

        time.sleep(0.1)

    print("Final state:", controller.state.value)

finally:
    controller.cleanup()
    buzzer.cleanup()
    database.close()
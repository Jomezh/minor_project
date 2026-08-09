import time

import RPi.GPIO as GPIO

from config import MOCK_DOOR_CYCLE_SECONDS
from database.database import Database
from core.access_policy import AccessPolicy
from core.app_controller import AppController
from core.door_controller import DoorState
from hardware.relay_controller import RelayController
from hardware.buzzer_controller import BuzzerController
from hardware.mock_door import MockDoorSensor


def finish_door_cycle(app, door):
    deadline = time.monotonic() + 10

    while app.door_controller.state != DoorState.LOCKED:
        app.update()

        if time.monotonic() >= deadline:
            raise TimeoutError("Door did not return to locked state")

        time.sleep(0.1)


database = Database()
policy = AccessPolicy(database)
relay = RelayController()
buzzer = BuzzerController()
door = MockDoorSensor(MOCK_DOOR_CYCLE_SECONDS)

door_controller = __import__(
    "core.door_controller",
    fromlist=["DoorController"],
).DoorController(relay, buzzer, door, database)

app = AppController(
    database=database,
    access_policy=policy,
    door_controller=door_controller,
    buzzer=buzzer,
)

try:
    print("Testing valid admin card")

    door.simulate_unlock_cycle()

    result = app.handle_rfid_uid("9E-24-41-06")
    print(result)

    finish_door_cycle(app, door)
    print("Admin access cycle complete")

    print("\nTesting valid guest card")

    door.simulate_unlock_cycle()

    result = app.handle_rfid_uid("AA-BB-CC-EE")
    print(result)

    finish_door_cycle(app, door)
    print("Guest access cycle complete")

    print("\nTesting unknown card")

    result = app.handle_rfid_uid("00-11-22-33")
    print(result)

    print("\nTesting manual exit")

    door.simulate_unlock_cycle()

    result = app.handle_exit_button()
    print(result)

    finish_door_cycle(app, door)
    print("Exit cycle complete")

finally:
    app.cleanup()
    buzzer.cleanup()
    database.close()
    GPIO.cleanup()
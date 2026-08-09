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
            raise TimeoutError("Door did not
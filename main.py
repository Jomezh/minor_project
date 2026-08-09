import time

import RPi.GPIO as GPIO

from config import MOCK_DOOR_CYCLE_SECONDS
from database.database import Database
from core.access_policy import AccessPolicy
from core.app_controller import AppController
from hardware.rfid_bitbanged import RFIDBitBang
from hardware.relay_controller import RelayController
from hardware.buzzer_controller import BuzzerController
from hardware.mock_door import MockDoorSensor
from core.door_controller import DoorController


database = Database()
policy = AccessPolicy(database)

reader = RFIDBitBang()
relay = RelayController()
buzzer = BuzzerController()
door = MockDoorSensor(MOCK_DOOR_CYCLE_SECONDS)

door_controller = DoorController(
    relay=relay,
    buzzer=buzzer,
    door_sensor=door,
    database=database,
)

app = AppController(
    database=database,
    access_policy=policy,
    door_controller=door_controller,
    buzzer=buzzer,
)

last_uid = None
last_scan_time = 0.0
SCAN_COOLDOWN_SECONDS = 2.0


try:
    reader.initialize()

    print("Access-control system started")
    print("Relay locked")
    print("Waiting for RFID card...")

    while True:
        app.update()

        uid = reader.read_uid()

        if uid is not None:
            normalized_uid = database.normalize_uid(uid)
            now = time.monotonic()

            repeated_scan = (
                normalized_uid == last_uid
                and now - last_scan_time < SCAN_COOLDOWN_SECONDS
            )

            if not repeated_scan:
                print(f"Card detected: {normalized_uid}")

                # Only needed while MockDoorSensor is enabled.
                door.simulate_unlock_cycle()

                result = app.handle_rfid_uid(normalized_uid)
                print(result)

                last_uid = normalized_uid
                last_scan_time = now

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping access-control system")

finally:
    app.cleanup()
    reader.cleanup()
    buzzer.cleanup()
    database.close()
    GPIO.cleanup()
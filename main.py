import time

from config import MOCK_DOOR_CYCLE_SECONDS
from database.database import Database
from core.access_policy import AccessPolicy
from core.app_controller import AppController
from core.door_controller import DoorController
from hardware.rfid_bitbanged import RFIDBitBang
from hardware.relay_controller import RelayController
from hardware.buzzer_controller import BuzzerController
from hardware.mock_door import MockDoorSensor


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

card_ready = True


try:
    reader.initialize()

    print("Access-control system started")
    print("Relay locked")
    print("Waiting for RFID card...")

    while True:
        app.update()

        uid = reader.read_uid()

        if uid is None:
            # The card has been removed.
            # Re-arm the reader for the next scan.
            card_ready = True

        elif card_ready:
            card_ready = False

            normalized_uid = database.normalize_uid(uid)

            print(f"Card detected: {normalized_uid}")

            result = app.handle_rfid_uid(normalized_uid)

            print(result)

            # Only simulate the door opening after access is granted.
            if result.get("allowed"):
                door.simulate_unlock_cycle()

        time.sleep(0.05)


except KeyboardInterrupt:
    print("\nStopping access-control system")


finally:
    # Ensure the relay is locked before releasing GPIO.
    app.cleanup()

    # Buzzer must be cleaned before reader.cleanup()
    # because reader.cleanup() releases all GPIO resources.
    buzzer.cleanup()
    reader.cleanup()
    database.close()

    print("System safely stopped")
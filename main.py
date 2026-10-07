import time

from core.access_policy import AccessPolicy
from core.app_controller import AppController
from core.door_controller import DoorController
from database.database import Database
from hardware.buzzer_controller import BuzzerController
from hardware.reed_door_sensor import ReedDoorSensor
from hardware.relay_controller import RelayController
from hardware.rfid_bitbanged import RFIDBitBang


MISS_THRESHOLD = 6
LOOP_DELAY_SECONDS = 0.05


database = Database()
policy = AccessPolicy(database)

reader = RFIDBitBang()
relay = RelayController()
buzzer = BuzzerController()
door_sensor = ReedDoorSensor()

door_controller = DoorController(
    relay=relay,
    buzzer=buzzer,
    door_sensor=door_sensor,
    database=database,
)

app = AppController(
    database=database,
    access_policy=policy,
    door_controller=door_controller,
    buzzer=buzzer,
)

card_ready = True
consecutive_misses = 0
previous_door_closed = None


def print_result(result):
    print()
    print(result)
    print()


def handle_console_enrollment(result):
    if result.get("result") != "enrollment_started":
        return

    uid = result["uid"]

    print()
    print("=" * 45)
    print("CARD ENROLLMENT")
    print("=" * 45)
    print(f"Card UID: {uid}")
    print("Press Enter with no name to cancel.")
    print()

    label = input("Cardholder name: ").strip()

    if not label:
        app.cancel_enrollment()
        print("Enrollment cancelled.")
        print()
        return

    tier = input(
        "Tier [guest / employee / admin]: "
    ).strip().lower()

    if tier not in ("guest", "employee", "admin"):
        print("Invalid tier; using guest.")
        tier = "guest"

    enrollment_result = app.submit_enrollment(
        uid=uid,
        label=label,
        tier_value=tier,
    )

    print_result(enrollment_result)


def print_door_state_if_changed():
    global previous_door_closed

    closed = door_sensor.is_closed()

    if closed == previous_door_closed:
        return

    previous_door_closed = closed

    if closed:
        print("Door sensor: CLOSED")
    else:
        print("Door sensor: OPEN")


try:
    reader.initialize()
    relay.lock()

    print("Access-control system started")
    print("Relay locked")
    print(
        "Door sensor:",
        "CLOSED" if door_sensor.is_closed() else "OPEN",
    )
    print("Waiting for RFID card...")
    print("Press Ctrl+C to stop.")

    while True:
        app.update()
        print_door_state_if_changed()

        # Important:
        # While a valid access event has the door unlocked, do not process
        # new cards. DoorController will relock after the reed switch sees
        # open -> closed, or after the configured timeout.
        if door_controller.unlock_active:
            time.sleep(LOOP_DELAY_SECONDS)
            continue

        uid = reader.read_uid()

        if uid is None:
            consecutive_misses += 1

            if consecutive_misses >= MISS_THRESHOLD:
                card_ready = True

            time.sleep(LOOP_DELAY_SECONDS)
            continue

        consecutive_misses = 0

        if not card_ready:
            time.sleep(LOOP_DELAY_SECONDS)
            continue

        card_ready = False

        normalized_uid = database.normalize_uid(uid)

        print()
        print(f"Card detected: {normalized_uid}")

        result = app.handle_rfid_uid(normalized_uid)

        print_result(result)

        # Enrollment is intentionally console-based for the no-UI version.
        # This will be replaced by the Kivy enrollment form later.
        handle_console_enrollment(result)

        time.sleep(LOOP_DELAY_SECONDS)


except KeyboardInterrupt:
    print("\nStopping access-control system")


finally:
    # Lock first, then release hardware resources.
    app.cleanup()

    buzzer.cleanup()
    door_sensor.cleanup()
    reader.cleanup()
    database.close()

    print("System safely stopped")
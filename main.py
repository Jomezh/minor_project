import threading
import time

from core.access_policy import AccessPolicy
from core.app_controller import AppController
from core.door_controller import DoorController
from database.database import Database
from hardware.button_input import ButtonInput
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

# RFID state.
card_ready = True
consecutive_misses = 0

# Door/reed state used only for console messages.
previous_door_closed = None

# GPIO callbacks run outside the main program loop. The callback only sets
# this flag; the actual relay/database work remains safely in the main loop.
exit_requested = threading.Event()


def on_exit_button_pressed():
    exit_requested.set()


button = ButtonInput(on_exit_button_pressed)


def print_result(result):
    print()
    print(result)
    print()


def print_door_state_if_changed():
    global previous_door_closed

    door_closed = door_sensor.is_closed()

    if door_closed == previous_door_closed:
        return

    previous_door_closed = door_closed

    if door_closed:
        print("Door sensor: CLOSED")
    else:
        print("Door sensor: OPEN")


def handle_exit_button_request():
    if not exit_requested.is_set():
        return

    exit_requested.clear()

    if door_controller.unlock_active:
        print("Exit button pressed, but door unlock is already active.")
        return

    print()
    print("Exit button pressed")
    print("Unlocking door for exit")

    door_controller.unlock(
        reason="inside_exit_button",
        actor_uid=None,
    )


def handle_console_enrollment(result):
    if result.get("result") != "enrollment_started":
        return

    uid = result["uid"]

    print()
    print("=" * 45)
    print("CARD ENROLLMENT")
    print("=" * 45)
    print(f"Card UID: {uid}")
    print("Press Enter without entering a name to cancel.")
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
    print("Inside exit button is active.")
    print("Press Ctrl+C to stop.")

    while True:
        # Handles reed-switch transitions:
        # closed -> opened -> closed = automatic relay re-lock.
        app.update()

        # Prints OPEN/CLOSED only when the reed-switch state changes.
        print_door_state_if_changed()

        # Handles the physical inside exit button.
        handle_exit_button_request()

        # Do not process RFID while the relay is unlocked.
        # This prevents repeated scans and admin-card toggling while
        # somebody is passing through the door.
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

        # Console-only enrollment bridge.
        # A later touchscreen UI can replace this with a Kivy form.
        handle_console_enrollment(result)

        time.sleep(LOOP_DELAY_SECONDS)


except KeyboardInterrupt:
    print("\nStopping access-control system")


finally:
    # Always force the relay to the locked state before releasing GPIO.
    app.cleanup()

    button.cleanup()
    buzzer.cleanup()
    door_sensor.cleanup()
    reader.cleanup()
    database.close()

    print("System safely stopped")
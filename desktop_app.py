import threading
import time

from config import SIMULATION_MODE
from core.access_policy import AccessPolicy
from core.app_controller import AppController
from core.door_controller import DoorController
from database.database import Database
from hardware.simulated_hardware import (
    SimulatedButtonInput,
    SimulatedBuzzerController,
    SimulatedDoorCycle,
    SimulatedDoorSensor,
    SimulatedRFIDReader,
    SimulatedRelayController,
)


LOOP_DELAY_SECONDS = 0.05


if not SIMULATION_MODE:
    raise RuntimeError(
        "desktop_app.py requires SIMULATION_MODE = True "
        "in config.py"
    )


database = Database()
policy = AccessPolicy(database)

reader = SimulatedRFIDReader()
relay = SimulatedRelayController()
buzzer = SimulatedBuzzerController()
door_sensor = SimulatedDoorSensor()

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

exit_requested = threading.Event()


def on_exit_button_pressed():
    exit_requested.set()


button = SimulatedButtonInput(on_exit_button_pressed)

door_cycle = SimulatedDoorCycle(
    door_sensor=door_sensor,
    open_delay=0.5,
    open_seconds=2.0,
)


def print_help():
    print()
    print("Available simulation commands:")
    print()
    print("  scan <UID>       Simulate an RFID card scan")
    print("  open             Simulate physical door opening")
    print("  close            Simulate physical door closing")
    print("  cycle            Simulate door open -> close cycle")
    print("  exit             Simulate the inside exit button")
    print("  status           Show system state")
    print("  cards            List enrolled cards")
    print("  logs             Show recent access logs")
    print("  help             Show this command list")
    print("  quit             Stop the simulator")
    print()


def print_status():
    print()
    print("SYSTEM STATUS")
    print("-" * 45)
    print(
        "Relay:",
        "UNLOCKED" if relay.is_energized() else "LOCKED",
    )
    print(
        "Door:",
        "CLOSED" if door_sensor.is_closed() else "OPEN",
    )
    print(
        "Door access cycle:",
        "ACTIVE" if door_controller.unlock_active else "IDLE",
    )
    print("App mode:", app.mode)
    print("Admin UID:", app.admin_uid or "-")
    print(
        "Pending enrollment:",
        app.pending_enrollment_uid or "-",
    )
    print()


def print_cards():
    rows = database.list_cards()

    print()
    print("ENROLLED CARDS")
    print("-" * 70)

    if not rows:
        print("No cards are enrolled.")
        print()
        return

    for card in rows:
        state = "active" if card["active"] else "disabled"

        print(
            f"{card['uid']} | "
            f"{card['label']} | "
            f"{card['tier']} | "
            f"{state}"
        )

    print()


def print_logs():
    rows = database.connection.execute(
        """
        SELECT
            uid,
            event_type,
            result,
            reason,
            actor_uid,
            door_state,
            created_at
        FROM access_logs
        ORDER BY id DESC
        LIMIT 20
        """
    ).fetchall()

    print()
    print("RECENT ACCESS LOGS")
    print("-" * 100)

    if not rows:
        print("No log entries.")
        print()
        return

    for row in rows:
        print(
            f"{row['created_at']} | "
            f"UID={row['uid'] or '-'} | "
            f"{row['event_type']} | "
            f"{row['result']} | "
            f"{row['reason'] or '-'}"
        )

    print()


def handle_console_enrollment(result):
    if result.get("result") != "enrollment_started":
        return

    uid = result["uid"]

    print()
    print("=" * 45)
    print("SIMULATED CARD ENROLLMENT")
    print("=" * 45)
    print(f"Card UID: {uid}")

    label = input("Cardholder name: ").strip()

    if not label:
        app.cancel_enrollment()
        print("Enrollment cancelled.")
        return

    tier = input(
        "Tier [guest / employee / admin]: "
    ).strip().lower()

    if tier not in ("guest", "employee", "admin"):
        tier = "guest"
        print("Invalid tier; using guest.")

    enrollment_result = app.submit_enrollment(
        uid=uid,
        label=label,
        tier_value=tier,
    )

    print(enrollment_result)


def handle_scan(uid):
    if door_controller.unlock_active:
        print(
            "Scan ignored: door is currently unlocked. "
            "Close the door first."
        )
        return

    reader.queue_uid(uid)

    scanned_uid = reader.read_uid()

    if scanned_uid is None:
        return

    normalized_uid = database.normalize_uid(scanned_uid)

    print()
    print(f"Simulated card detected: {normalized_uid}")

    result = app.handle_rfid_uid(normalized_uid)

    print(result)

    if result.get("allowed"):
        print(
            "Use 'cycle' to simulate a person opening "
            "and closing the door."
        )

    handle_console_enrollment(result)


def handle_exit_button():
    if door_controller.unlock_active:
        print("Exit request ignored: door unlock is already active.")
        return

    button.press()


def process_exit_button():
    if not exit_requested.is_set():
        return

    exit_requested.clear()

    if door_controller.unlock_active:
        return

    door_controller.unlock(
        reason="inside_exit_button",
        actor_uid=None,
    )


def process_command(command):
    parts = command.strip().split(maxsplit=1)

    if not parts:
        return True

    action = parts[0].lower()
    value = parts[1].strip() if len(parts) > 1 else ""

    if action == "scan":
        if not value:
            print("Usage: scan <UID>")
            return True

        handle_scan(value)
        return True

    if action == "open":
        door_sensor.open()
        return True

    if action == "close":
        door_sensor.close()
        return True

    if action == "cycle":
        if not door_controller.unlock_active:
            print(
                "Door is locked. Scan an allowed card or "
                "use the exit command first."
            )
            return True

        door_cycle.run()
        return True

    if action == "exit":
        handle_exit_button()
        return True

    if action == "status":
        print_status()
        return True

    if action == "cards":
        print_cards()
        return True

    if action == "logs":
        print_logs()
        return True

    if action == "help":
        print_help()
        return True

    if action in ("quit", "q", "exitapp"):
        return False

    print("Unknown command. Type 'help'.")
    return True


def main():
    reader.initialize()
    relay.lock()

    print("Desktop access-control simulator started")
    print("No Raspberry Pi hardware is required.")
    print_help()

    running = True

    while running:
        app.update()
        process_exit_button()

        try:
            command = input("sim> ")
        except EOFError:
            break

        running = process_command(command)

        # Give any simulated door-cycle thread a chance to advance.
        time.sleep(LOOP_DELAY_SECONDS)


try:
    main()

except KeyboardInterrupt:
    print("\nStopping simulator")

finally:
    app.cleanup()
    button.cleanup()
    buzzer.cleanup()
    reader.cleanup()
    database.close()

    print("Simulator safely stopped")
from config import (
    RELAY_ACTIVE_LEVEL,
    RELAY_INACTIVE_LEVEL,
)


class SimulatedRFIDReader:
    def __init__(self):
        self.pending_uid = None

    def initialize(self):
        self.pending_uid = None

    def queue_uid(self, uid):
        self.pending_uid = uid

    def read_uid(self):
        if self.pending_uid is None:
            return None

        uid = self.pending_uid
        self.pending_uid = None

        parts = str(uid).replace(":", "-").replace(" ", "-").split("-")
        return [int(part, 16) for part in parts if part]

    def cleanup(self):
        self.pending_uid = None


class SimulatedRelay:
    def __init__(self):
        self.state = RELAY_INACTIVE_LEVEL

    def lock(self):
        self.state = RELAY_INACTIVE_LEVEL

    def unlock(self):
        self.state = RELAY_ACTIVE_LEVEL

    def is_unlocked(self):
        return self.state == RELAY_ACTIVE_LEVEL

    def is_energized(self):
        return self.state == RELAY_ACTIVE_LEVEL

    def cleanup(self):
        self.lock()


class SimulatedBuzzerController:
    def __init__(self):
        self.last_event = None

    def unlock_beep(self):
        self.last_event = "unlock_beep"

    def lock_beep(self):
        self.last_event = "lock_beep"

    def denied_beep(self):
        self.last_event = "denied_beep"

    def alarm_beep(self):
        self.last_event = "alarm_beep"

    def cleanup(self):
        self.last_event = None


class SimulatedDoorSensor:
    def __init__(self):
        self.open_state = False

    def open(self):
        self.open_state = True

    def close(self):
        self.open_state = False

    def is_open(self):
        return self.open_state

    def is_closed(self):
        return not self.open_state

    def cleanup(self):
        self.open_state = False


class SimulatedButtonInput:
    def __init__(self, on_press=None):
        self.on_press = on_press

    def press(self):
        if self.on_press:
            self.on_press()

    def cleanup(self):
        pass


# Compatibility aliases for alternate import names.
SimulatedBuzzer = SimulatedBuzzerController
SimulatedButton = SimulatedButtonInput
SimulatedRFIDReaderController = SimulatedRFIDReader
SimulatedRelayController = SimulatedRelay
SimulatedDoorSensorController = SimulatedDoorSensor
SimulatedButtonController = SimulatedButtonInput


def create_hardware(on_exit_button=None):
    return {
        "reader": SimulatedRFIDReader(),
        "relay": SimulatedRelay(),
        "buzzer": SimulatedBuzzerController(),
        "door_sensor": SimulatedDoorSensor(),
        "button": SimulatedButtonInput(on_press=on_exit_button),
    }

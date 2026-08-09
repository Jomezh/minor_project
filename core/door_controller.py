import time
from enum import Enum

from config import (
    DOOR_OPEN_TIMEOUT_SECONDS,
    DOOR_CLOSE_TIMEOUT_SECONDS,
    ALARM_REPEAT_SECONDS,
)


class DoorState(str, Enum):
    LOCKED = "locked"
    WAITING_FOR_OPEN = "waiting_for_open"
    OPEN = "open"
    ALARM = "alarm"


class DoorController:
    def __init__(self, relay, buzzer, door_sensor, database=None):
        self.relay = relay
        self.buzzer = buzzer
        self.door_sensor = door_sensor
        self.database = database

        self.state = DoorState.LOCKED
        self.reason = None
        self.uid = None

        self.state_started = time.monotonic()
        self.last_alarm = 0.0

        self.relay.lock()

    def _log(self, event_type, result, reason):
        if self.database is None:
            return

        self.database.add_log(
            uid=self.uid,
            event_type=event_type,
            result=result,
            reason=reason,
            door_state=self.state.value,
        )

    def request_unlock(self, reason="normal_access", uid=None):
        if self.state != DoorState.LOCKED:
            return False

        self.reason = reason
        self.uid = uid

        self.relay.unlock()
        self.buzzer.unlock_beep()

        self.state = DoorState.WAITING_FOR_OPEN
        self.state_started = time.monotonic()

        self._log(
            event_type="unlock_requested",
            result="granted",
            reason=reason,
        )

        return True

    def update(self):
        now = time.monotonic()
        elapsed = now - self.state_started
        door_closed = self.door_sensor.is_closed()

        if self.state == DoorState.WAITING_FOR_OPEN:
            if not door_closed:
                self.state = DoorState.OPEN
                self.state_started = now

                self._log(
                    event_type="door_open",
                    result="open",
                    reason=self.reason,
                )

            elif elapsed >= DOOR_OPEN_TIMEOUT_SECONDS:
                self._relock("Door did not open before timeout")

        elif self.state == DoorState.OPEN:
            if door_closed:
                self._relock("Door closed")

            elif elapsed >= DOOR_CLOSE_TIMEOUT_SECONDS:
                self.state = DoorState.ALARM
                self.state_started = now
                self.last_alarm = 0.0

                self._log(
                    event_type="door_alarm",
                    result="alarm",
                    reason="Door remained open too long",
                )

        elif self.state == DoorState.ALARM:
            if door_closed:
                self._relock("Door closed after alarm")

            elif now - self.last_alarm >= ALARM_REPEAT_SECONDS:
                self.buzzer.alarm_beep()
                self.last_alarm = now

    def _relock(self, reason):
        self.relay.lock()
        self.buzzer.lock_beep()

        self.state = DoorState.LOCKED
        self.state_started = time.monotonic()

        self._log(
            event_type="door_relocked",
            result="locked",
            reason=reason,
        )

        self.reason = None
        self.uid = None

    def force_lock(self):
        if not self.door_sensor.is_closed():
            return False

        self._relock("Manual lock")
        return True

    def cleanup(self):
        self.relay.lock()
        self.state = DoorState.LOCKED

import time

from config import (
    ALARM_REPEAT_SECONDS,
    DOOR_CLOSE_TIMEOUT_SECONDS,
    DOOR_OPEN_TIMEOUT_SECONDS,
)


class DoorController:
    def __init__(self, relay, buzzer, door_sensor, database):
        self.relay = relay
        self.buzzer = buzzer
        self.door_sensor = door_sensor
        self.database = database

        self.unlock_active = False
        self.door_has_opened = False
        self.unlock_started_at = None
        self.last_alarm_at = None

    def unlock(self, reason="access_granted", actor_uid=None):
        if self.unlock_active:
            return False

        self.relay.unlock()
        self.buzzer.unlockbeep()

        self.unlock_active = True
        self.door_has_opened = False
        self.unlock_started_at = time.monotonic()
        self.last_alarm_at = None

        self.database.add_log(
            uid=actor_uid,
            event_type="door",
            result="unlocked",
            reason=reason,
            actor_uid=actor_uid,
            door_state="unlocked",
        )

        return True

    def lock(self, reason="auto_relock", actor_uid=None):
        if not self.unlock_active and not self.relay.is_energized():
            return False

        self.relay.lock()
        self.buzzer.lockbeep()

        self.unlock_active = False
        self.door_has_opened = False
        self.unlock_started_at = None
        self.last_alarm_at = None

        self.database.add_log(
            uid=actor_uid,
            event_type="door",
            result="locked",
            reason=reason,
            actor_uid=actor_uid,
            door_state="locked",
        )

        return True

    def update(self):
        if not self.unlock_active:
            return

        now = time.monotonic()
        elapsed = now - self.unlock_started_at
        door_closed = self.door_sensor.is_closed()

        # Door was physically opened after the unlock command.
        if not door_closed and not self.door_has_opened:
            self.door_has_opened = True

            self.database.add_log(
                uid=None,
                event_type="door",
                result="opened",
                reason="Reed switch detected door open",
                door_state="open",
            )

        # Door was opened and is now physically closed again.
        if self.door_has_opened and door_closed:
            self.lock(reason="door_closed")
            return

        # Access was granted, but the user never opened the door.
        if not self.door_has_opened:
            if elapsed >= DOOR_OPEN_TIMEOUT_SECONDS:
                self.lock(reason="door_not_opened_timeout")
            return

        # Door has remained physically open too long.
        if elapsed >= DOOR_CLOSE_TIMEOUT_SECONDS:
            if (
                self.last_alarm_at is None
                or now - self.last_alarm_at >= ALARM_REPEAT_SECONDS
            ):
                self.buzzer.alarmbeep()
                self.last_alarm_at = now

                self.database.add_log(
                    uid=None,
                    event_type="alarm",
                    result="door_held_open",
                    reason="Door remained open past close timeout",
                    door_state="open",
                )

    def cleanup(self):
        self.relay.lock()
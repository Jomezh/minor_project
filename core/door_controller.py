import time

from config import (
    DOOR_OPEN_TIMEOUT_SECONDS,
    DOOR_CLOSE_TIMEOUT_SECONDS,
    ALARM_REPEAT_SECONDS,
)


class DoorController:
    def __init__(self, relay, buzzer, door_sensor, database):
        self.relay = relay
        self.buzzer = buzzer
        self.door_sensor = door_sensor
        self.database = database

        self.unlock_active = False
        self.door_has_opened = False
        self.admin_override = False
        self.unlock_started_at = None
        self.last_alarm_at = None

    def unlock(self, reason="access_granted", actor_uid=None):
        if self.unlock_active:
            return

        self.relay.unlock()
        self.buzzer.unlockbeep()

        self.unlock_active = True
        self.door_has_opened = False
        self.unlock_started_at = time.time()

        self.door_sensor.simulate_unlock_cycle()

        self.database.add_log(
            uid=actor_uid,
            event_type="door",
            result="unlocked",
            reason=reason,
            actor_uid=actor_uid,
            door_state="unlocked",
        )

    def lock(self, reason="auto_relock", actor_uid=None):
        if not self.unlock_active and not self.relay.is_energized():
            return

        self.relay.lock()
        self.buzzer.lockbeep()

        self.unlock_active = False
        self.door_has_opened = False
        self.unlock_started_at = None

        self.database.add_log(
            uid=actor_uid,
            event_type="door",
            result="locked",
            reason=reason,
            actor_uid=actor_uid,
            door_state="locked",
        )

    def enter_admin_override(self):
        # Admin mode suspends the auto-unlock/auto-relock timers so
        # the door can be controlled manually from the admin menu.
        self.admin_override = True

    def exit_admin_override(self):
        self.admin_override = False

        if not self.unlock_active:
            self.relay.lock()

    def admin_set_state(self, unlocked, actor_uid=None):
        if unlocked:
            self.relay.unlock()
            self.buzzer.unlockbeep()
            result = "unlocked"
        else:
            self.relay.lock()
            self.buzzer.lockbeep()
            result = "locked"

        self.database.add_log(
            uid=actor_uid,
            event_type="admin_override",
            result=result,
            reason="Manual admin control",
            actor_uid=actor_uid,
            door_state=result,
        )

    def update(self):
        if self.admin_override:
            return

        if not self.unlock_active:
            return

        closed = self.door_sensor.is_closed()
        elapsed = time.time() - self.unlock_started_at

        if not closed and not self.door_has_opened:
            self.door_has_opened = True

        if self.door_has_opened and closed:
            self.lock(reason="door_closed")
            return

        if not self.door_has_opened and elapsed > DOOR_OPEN_TIMEOUT_SECONDS:
            self.lock(reason="open_timeout")
            return

        if self.door_has_opened and not closed and elapsed > DOOR_CLOSE_TIMEOUT_SECONDS:
            now = time.time()

            if self.last_alarm_at is None or now - self.last_alarm_at > ALARM_REPEAT_SECONDS:
                self.buzzer.alarmbeep()
                self.last_alarm_at = now

                self.database.add_log(
                    uid=None,
                    event_type="alarm",
                    result="door_held_open",
                    reason="Door held open past timeout",
                    door_state="open",
                )

    def cleanup(self):
        self.relay.lock()
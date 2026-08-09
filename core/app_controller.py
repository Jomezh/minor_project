from config import AccessResult
from core.door_controller import DoorState


class AppController:
    def __init__(self, database, access_policy, door_controller, buzzer):
        self.database = database
        self.access_policy = access_policy
        self.door_controller = door_controller
        self.buzzer = buzzer

    def handle_rfid_uid(self, uid, room_name="Main Entrance"):
        if self.door_controller.state != DoorState.LOCKED:
            return {
                "allowed": False,
                "reason": "Door workflow already active",
            }

        normalized_uid = self.database.normalize_uid(uid)

        decision = self.access_policy.evaluate_normal_access(
            normalized_uid,
            room_name,
        )

        if not decision.allowed:
            self.buzzer.denied_beep()

            self.database.add_log(
                uid=normalized_uid,
                card_id=decision.card["id"] if decision.card else None,
                event_type="rfid_access_attempt",
                result=decision.result.value,
                reason=decision.reason,
                door_state=self.door_controller.state.value,
            )

            return {
                "allowed": False,
                "result": decision.result.value,
                "reason": decision.reason,
            }

        self.database.increment_use_count(decision.card["id"])

        started = self.door_controller.request_unlock(
            reason="normal_access",
            uid=normalized_uid,
        )

        return {
            "allowed": started,
            "result": AccessResult.GRANTED.value,
            "reason": decision.reason,
            "uid": normalized_uid,
        }

    def handle_exit_button(self):
        started = self.door_controller.request_unlock(
            reason="manual_exit",
            uid=None,
        )

        if not started:
            return {
                "allowed": False,
                "reason": "Door workflow already active",
            }

        return {
            "allowed": True,
            "reason": "manual_exit",
        }

    def update(self):
        self.door_controller.update()

    def cleanup(self):
        self.door_controller.cleanup()
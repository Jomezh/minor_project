from config import Tier


class AppController:
    def __init__(self, database, access_policy, door_controller, buzzer):
        self.database = database
        self.access_policy = access_policy
        self.door_controller = door_controller
        self.buzzer = buzzer

        self.mode = "normal"
        self.admin_uid = None
        self.pending_enrollment_uid = None

    def update(self):
        self.door_controller.update()

    def handle_rfid_uid(self, uid):
        uid = self.database.normalize_uid(uid)

        if self.mode == "admin_menu":
            return self._handle_admin_scan(uid)

        if self.access_policy.is_admin(uid):
            return self._enter_admin_mode(uid)

        return self._handle_normal_access(uid)

    def _enter_admin_mode(self, uid):
        self.mode = "admin_menu"
        self.admin_uid = uid
        self.pending_enrollment_uid = None

        self.database.add_log(
            uid=uid,
            event_type="admin_session",
            result="opened",
            reason="Admin card scanned",
            actor_uid=uid,
            door_state="unlocked",
        )

        self.door_controller.unlock(
            reason="admin_access_granted",
            actor_uid=uid,
        )

        return {
            "allowed": True,
            "result": "admin_mode",
            "reason": "Admin access granted; door unlocked",
            "uid": uid,
        }

    def _handle_normal_access(self, uid):
        decision = self.access_policy.evaluate_normal_access(uid)

        result_value = getattr(
            decision.result,
            "value",
            decision.result,
        )

        card_id = None
        if decision.card:
            card_id = decision.card["id"]

        self.database.add_log(
            uid=uid,
            event_type="scan",
            result=result_value,
            reason=decision.reason,
            card_id=card_id,
            door_state="unlocked" if decision.allowed else "locked",
        )

        if decision.allowed:
            self.door_controller.unlock(
                reason="access_granted",
                actor_uid=uid,
            )

            self.database.increment_use_count(card_id)

        else:
            self.buzzer.denied_beep()

        return {
            "allowed": decision.allowed,
            "result": result_value,
            "reason": decision.reason,
            "uid": uid,
        }

    def _handle_admin_scan(self, uid):
        if uid == self.admin_uid:
            self.mode = "normal"
            self.pending_enrollment_uid = None

            self.database.add_log(
                uid=uid,
                event_type="admin_session",
                result="closed",
                reason="Admin re-scanned own card",
                actor_uid=uid,
                door_state=(
                    "unlocked"
                    if self.door_controller.unlock_active
                    else "locked"
                ),
            )

            self.admin_uid = None
            self.buzzer.lock_beep()

            return {
                "allowed": False,
                "result": "admin_mode_exited",
                "reason": "Admin mode exited",
                "uid": uid,
            }

        if self.pending_enrollment_uid == uid:
            return {
                "allowed": False,
                "result": "enrollment_pending",
                "reason": "Waiting for enrollment details",
                "uid": uid,
            }

        existing_card = self.database.get_card(uid)

        if existing_card:
            self.buzzer.denied_beep()

            return {
                "allowed": False,
                "result": "admin_card_lookup",
                "reason": (
                    f"Already enrolled: "
                    f"{existing_card['label']} "
                    f"({existing_card['tier']})"
                ),
                "uid": uid,
            }

        return self.start_enrollment(uid)

    def start_enrollment(self, uid):
        self.pending_enrollment_uid = uid

        return {
            "allowed": False,
            "result": "enrollment_started",
            "reason": "Unknown card is ready for enrollment",
            "uid": uid,
        }

    def submit_enrollment(self, uid, label, tier_value):
        uid = self.database.normalize_uid(uid)

        if uid != self.pending_enrollment_uid:
            return {
                "allowed": False,
                "result": "enrollment_error",
                "reason": "No matching pending enrollment",
                "uid": uid,
            }

        label = label.strip()

        if not label:
            return {
                "allowed": False,
                "result": "enrollment_error",
                "reason": "Cardholder name cannot be empty",
                "uid": uid,
            }

        tier_map = {
            tier.value: tier
            for tier in Tier
        }

        tier = tier_map.get(
            tier_value.strip().lower(),
            Tier.GUEST,
        )

        card_id = self.database.create_card(
            uid=uid,
            label=label,
            tier=tier,
            created_by=self.admin_uid,
        )

        self.database.add_log(
            uid=uid,
            event_type="enrollment",
            result="enrolled",
            reason=(
                f"Enrolled as {tier.value} "
                f"by admin {self.admin_uid}"
            ),
            actor_uid=self.admin_uid,
            card_id=card_id,
            door_state="locked",
        )

        self.pending_enrollment_uid = None
        self.buzzer.unlock_beep()

        return {
            "allowed": False,
            "result": "enrolled",
            "reason": f"{label} enrolled as {tier.value}",
            "uid": uid,
        }

    def cancel_enrollment(self):
        self.pending_enrollment_uid = None

    def cleanup(self):
        self.door_controller.cleanup()
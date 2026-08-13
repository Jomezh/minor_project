from config import Tier


class AppController:
    def __init__(self, database, access_policy, door_controller, buzzer):
        self.database = database
        self.access_policy = access_policy
        self.door_controller = door_controller
        self.buzzer = buzzer

        self.mode = "normal"
        self.admin_uid = None

    def update(self):
        self.door_controller.update()

    def handle_rfid_uid(self, uid):
        uid = self.database.normalize_uid(uid)

        if self.mode == "admin_menu":
            return self._handle_admin_scan(uid)

        if self.access_policy.is_admin(uid):
            self.mode = "admin_menu"
            self.admin_uid = uid
            self.door_controller.enter_admin_override()

            self.database.add_log(
                uid=uid,
                event_type="admin_session",
                result="opened",
                reason="Admin card scanned",
                actor_uid=uid,
                door_state="locked",
            )

            return {
                "allowed": False,
                "result": "admin_mode",
                "reason": "Admin mode entered. Door will not auto-unlock.",
                "uid": uid,
            }

        decision = self.access_policy.evaluate_normal_access(uid)
        result_value = getattr(decision.result, "value", decision.result)

        self.database.add_log(
            uid=uid,
            event_type="scan",
            result=result_value,
            reason=decision.reason,
            card_id=decision.card["id"] if decision.card else None,
            door_state="unlocked" if decision.allowed else "locked",
        )

        if decision.allowed:
            self.door_controller.unlock(reason="access_granted", actor_uid=uid)
            self.database.increment_use_count(decision.card["id"])
        else:
            self.buzzer.deniedbeep()

        return {
            "allowed": decision.allowed,
            "result": result_value,
            "reason": decision.reason,
            "uid": uid,
        }

    def _handle_admin_scan(self, uid):
        if uid == self.admin_uid:
            self.mode = "normal"
            self.door_controller.exit_admin_override()

            self.database.add_log(
                uid=uid,
                event_type="admin_session",
                result="closed",
                reason="Admin re-scanned own card",
                actor_uid=self.admin_uid,
                door_state="locked",
            )

            self.admin_uid = None

            return {
                "allowed": False,
                "result": "admin_mode_exited",
                "reason": "Exited admin mode",
                "uid": uid,
            }

        existing = self.database.get_card(uid)

        if existing:
            return {
                "allowed": False,
                "result": "admin_card_lookup",
                "reason": f"Already enrolled as {existing['label']} ({existing['tier']})",
                "uid": uid,
            }

        return self._enroll_card(uid)

    def _enroll_card(self, uid):
        # Console prompts are a placeholder until the Kivy enrollment
        # screen replaces this with on-screen text entry.
        print(f"\nUnknown card {uid} scanned while in admin mode.")

        label = input("Enter cardholder name: ").strip() or "Unnamed"
        tier_input = input("Enter tier (guest/employee/admin): ").strip().lower()

        tier_map = {tier.value: tier for tier in Tier}
        tier = tier_map.get(tier_input, Tier.GUEST)

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
            reason=f"Enrolled by admin {self.admin_uid} as {tier.value}",
            actor_uid=self.admin_uid,
            card_id=card_id,
            door_state="locked",
        )

        return {
            "allowed": False,
            "result": "enrolled",
            "reason": f"{label} enrolled as {tier.value}",
            "uid": uid,
        }

    def admin_manual_unlock(self):
        if self.mode == "admin_menu":
            self.door_controller.admin_set_state(True, actor_uid=self.admin_uid)

    def admin_manual_lock(self):
        if self.mode == "admin_menu":
            self.door_controller.admin_set_state(False, actor_uid=self.admin_uid)

    def cleanup(self):
        self.door_controller.cleanup()
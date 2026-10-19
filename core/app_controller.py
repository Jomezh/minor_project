import json
from datetime import datetime, timezone

from config import AccessResult, INITIAL_ADMIN_UID, Tier


class AppController:
    def __init__(
        self,
        database,
        access_policy,
        door_controller,
        buzzer=None,
    ):
        self.database = database
        self.policy = access_policy
        self.door_controller = door_controller
        self.buzzer = buzzer

        self.mode = "normal"
        self.admin_uid = None
        self.pending_enrollment_uid = None

    # ---------------- RFID flow ----------------

    def handle_rfid_uid(self, uid):
        uid = self.database.normalize_uid(uid)
        card = self.database.get_card(uid)

        if self.mode == "admin_menu":
            if card and card["tier"] == Tier.ADMIN.value:
                return self.exit_admin_mode(uid)

            if card is None:
                return self.start_enrollment(uid)

            return {
                "result": "admin_card_lookup",
                "uid": uid,
                "reason": (
                    f"{card['label']} | {card['tier']} | "
                    f"{'active' if card['active'] else 'disabled'}"
                ),
            }

        if self.mode == "enrollment":
            if card and card["tier"] == Tier.ADMIN.value and card["active"]:
                self.cancel_enrollment()
                return self.exit_admin_mode(uid)

            return {
                "result": "enrollment_pending",
                "uid": uid,
                "reason": "Complete or cancel current enrollment",
            }

        if card and card["tier"] == Tier.ADMIN.value and card["active"]:
            return self.enter_admin_mode(uid)

        decision = self.policy.evaluate_normal_access(uid)

        if decision.allowed:
            self.database.increment_use_count(decision.card["id"])
            self.database.add_log(
                uid=uid,
                card_id=decision.card["id"],
                event_type="card_scan",
                result=AccessResult.GRANTED.value,
                reason=decision.reason,
                door_state="unlocked",
            )
            self.door_controller.unlock(
                reason=decision.reason,
                actor_uid=uid,
            )
            return {
                "result": AccessResult.GRANTED.value,
                "uid": uid,
                "reason": decision.reason,
            }

        if self.buzzer:
            self.buzzer.denied_beep()

        self.database.add_log(
            uid=uid,
            card_id=decision.card["id"] if decision.card else None,
            event_type="card_scan",
            result=decision.result.value,
            reason=decision.reason,
            door_state="locked",
        )

        return {
            "result": decision.result.value,
            "uid": uid,
            "reason": decision.reason,
        }

    def enter_admin_mode(self, uid):
        self.mode = "admin_menu"
        self.admin_uid = uid

        self.database.add_log(
            uid=uid,
            event_type="admin_action",
            result="admin_mode",
            reason="Admin authenticated",
            actor_uid=uid,
            door_state="unlocked",
        )

        self.door_controller.unlock(
            reason="admin_authenticated",
            actor_uid=uid,
        )

        return {
            "result": "admin_mode",
            "uid": uid,
            "reason": "Admin authenticated",
        }

    def exit_admin_mode(self, uid):
        self.mode = "normal"
        self.admin_uid = None
        self.pending_enrollment_uid = None

        self.database.add_log(
            uid=uid,
            event_type="admin_action",
            result="admin_mode_exited",
            reason="Admin mode exited",
            actor_uid=uid,
            door_state="locked",
        )

        self.door_controller.lock(
            reason="admin_mode_exited",
            actor_uid=uid,
        )

        return {
            "result": "admin_mode_exited",
            "uid": uid,
            "reason": "Admin mode exited",
        }

    # ---------------- Enrollment ----------------

    def start_enrollment(self, uid):
        self.pending_enrollment_uid = uid
        self.mode = "enrollment"

        self.database.add_log(
            uid=uid,
            event_type="enrollment",
            result="enrollment_started",
            reason="Unknown card scanned in admin mode",
            actor_uid=self.admin_uid,
        )

        return {
            "result": "enrollment_started",
            "uid": uid,
            "reason": "New card ready for enrollment",
        }

    def cancel_enrollment(self):
        uid = self.pending_enrollment_uid
        self.pending_enrollment_uid = None
        self.mode = "admin_menu"

        if uid:
            self.database.add_log(
                uid=uid,
                event_type="enrollment",
                result="cancelled",
                reason="Enrollment cancelled",
                actor_uid=self.admin_uid,
            )

    def submit_enrollment(
        self,
        uid,
        label,
        tier_value,
        schedule_id=None,
        valid_from=None,
        valid_until=None,
        max_uses=None,
    ):
        uid = self.database.normalize_uid(uid)

        if self.mode != "enrollment" or self.pending_enrollment_uid != uid:
            return {
                "result": "enrollment_failed",
                "uid": uid,
                "reason": "No enrollment session is active",
            }

        if not label.strip():
            return {
                "result": "enrollment_failed",
                "uid": uid,
                "reason": "Cardholder name is required",
            }

        try:
            tier = Tier(tier_value)
        except ValueError:
            return {
                "result": "enrollment_failed",
                "uid": uid,
                "reason": "Invalid access tier",
            }

        if self.database.get_card(uid):
            return {
                "result": "enrollment_failed",
                "uid": uid,
                "reason": "This card is already enrolled",
            }

        card_id = self.database.create_card(
            uid=uid,
            label=label.strip(),
            tier=tier,
            created_by=self.admin_uid,
            valid_from=valid_from,
            valid_until=valid_until,
            max_uses=max_uses,
        )

        if schedule_id:
            self.database.set_card_schedules(card_id, [schedule_id])

        self.pending_enrollment_uid = None
        self.mode = "admin_menu"

        self.database.add_log(
            uid=uid,
            card_id=card_id,
            event_type="enrollment",
            result="enrolled",
            reason=f"{label.strip()} enrolled as {tier.value}",
            actor_uid=self.admin_uid,
        )

        return {
            "result": "enrolled",
            "uid": uid,
            "reason": f"{label.strip()} enrolled successfully",
        }

    # ---------------- User management ----------------

    def _require_admin(self, actor_uid):
        actor = self.database.get_card(actor_uid) if actor_uid else None

        if not actor or actor["tier"] != Tier.ADMIN.value or not actor["active"]:
            return None, "Admin authorization required"

        return actor, None

    def update_user(
        self,
        card_id,
        actor_uid,
        label=None,
        tier_value=None,
        active=None,
        valid_from=None,
        valid_until=None,
        max_uses=None,
        schedule_ids=None,
    ):
        actor, error = self._require_admin(actor_uid)
        if error:
            return {"ok": False, "message": error}

        card = self.database.get_card_by_id(card_id)
        if not card:
            return {"ok": False, "message": "User not found"}

        fields = {}

        if label is not None:
            if not label.strip():
                return {"ok": False, "message": "Name cannot be empty"}
            fields["label"] = label.strip()

        if tier_value is not None:
            try:
                tier = Tier(tier_value)
            except ValueError:
                return {"ok": False, "message": "Invalid access tier"}

            if (
                card["tier"] == Tier.ADMIN.value
                and card["uid"] != actor["uid"]
                and tier != Tier.ADMIN
            ):
                return {
                    "ok": False,
                    "message": "You cannot change another admin's tier",
                }

            fields["tier"] = tier.value

        if active is not None:
            if (
                card["tier"] == Tier.ADMIN.value
                and card["uid"] != actor["uid"]
                and not active
            ):
                return {
                    "ok": False,
                    "message": "You cannot disable another admin",
                }

            fields["active"] = int(bool(active))

        if valid_from is not None:
            fields["valid_from"] = valid_from

        if valid_until is not None:
            fields["valid_until"] = valid_until

        if max_uses is not None:
            fields["max_uses"] = max_uses

        if fields:
            self.database.update_card(card_id, **fields)

        if schedule_ids is not None:
            self.database.set_card_schedules(card_id, schedule_ids)

        self.database.add_log(
            uid=card["uid"],
            card_id=card_id,
            event_type="admin_action",
            result="user_updated",
            reason=f"User updated: {card['label']}",
            actor_uid=actor_uid,
        )

        return {"ok": True, "message": "User saved"}

    def delete_user(self, card_id, actor_uid):
        actor, error = self._require_admin(actor_uid)
        if error:
            return {"ok": False, "message": error}

        card = self.database.get_card_by_id(card_id)
        if not card:
            return {"ok": False, "message": "User not found"}

        bootstrap_uid = self.database.normalize_uid(INITIAL_ADMIN_UID)

        if card["uid"] == bootstrap_uid:
            return {
                "ok": False,
                "message": "The initial admin card cannot be deleted",
            }

        if card["tier"] == Tier.ADMIN.value and card["uid"] != actor["uid"]:
            return {"ok": False, "message": "You cannot delete another admin"}

        self.database.delete_card(card_id)

        self.database.add_log(
            uid=card["uid"],
            event_type="admin_action",
            result="user_deleted",
            reason=f"User deleted: {card['label']}",
            actor_uid=actor_uid,
        )

        return {"ok": True, "message": "User deleted"}

    # ---------------- Schedule management ----------------

    def create_schedule(
        self,
        actor_uid,
        name,
        days,
        start_time,
        end_time,
        enabled=True,
    ):
        actor, error = self._require_admin(actor_uid)
        if error:
            return {"ok": False, "message": error}

        if not name.strip():
            return {"ok": False, "message": "Schedule name is required"}

        if self.database.get_schedule_by_name(name.strip()):
            return {"ok": False, "message": "A schedule with this name exists"}

        if not days:
            return {"ok": False, "message": "Select at least one weekday"}

        schedule_id = self.database.create_schedule(
            name=name.strip(),
            days=days,
            start_time=start_time,
            end_time=end_time,
            enabled=enabled,
        )

        self.database.add_log(
            uid=actor_uid,
            event_type="admin_action",
            result="schedule_created",
            reason=f"Schedule created: {name.strip()}",
            actor_uid=actor_uid,
        )

        return {"ok": True, "message": "Schedule created", "id": schedule_id}

    def update_schedule(
        self,
        schedule_id,
        actor_uid,
        name,
        days,
        start_time,
        end_time,
        enabled=True,
    ):
        actor, error = self._require_admin(actor_uid)
        if error:
            return {"ok": False, "message": error}

        schedule = self.database.get_schedule(schedule_id)
        if not schedule:
            return {"ok": False, "message": "Schedule not found"}

        if not name.strip():
            return {"ok": False, "message": "Schedule name is required"}

        existing = self.database.get_schedule_by_name(name.strip())

        if existing and existing["id"] != schedule_id:
            return {"ok": False, "message": "A schedule with this name exists"}

        if not days:
            return {"ok": False, "message": "Select at least one weekday"}

        self.database.update_schedule(
            schedule_id,
            name=name.strip(),
            days_json=json.dumps(days),
            start_time=start_time,
            end_time=end_time,
            enabled=int(bool(enabled)),
        )

        self.database.add_log(
            uid=actor_uid,
            event_type="admin_action",
            result="schedule_updated",
            reason=f"Schedule updated: {name.strip()}",
            actor_uid=actor_uid,
        )

        return {"ok": True, "message": "Schedule saved"}

    def delete_schedule(self, schedule_id, actor_uid):
        actor, error = self._require_admin(actor_uid)
        if error:
            return {"ok": False, "message": error}

        schedule = self.database.get_schedule(schedule_id)
        if not schedule:
            return {"ok": False, "message": "Schedule not found"}

        self.database.delete_schedule(schedule_id)

        self.database.add_log(
            uid=actor_uid,
            event_type="admin_action",
            result="schedule_deleted",
            reason=f"Schedule deleted: {schedule['name']}",
            actor_uid=actor_uid,
        )

        return {"ok": True, "message": "Schedule deleted"}

    # ---------------- Lifecycle ----------------

    def update(self):
        self.door_controller.update()

    def cleanup(self):
        pass

import json
from datetime import datetime, timezone

from config import AccessResult, Tier


class AccessDecision:
    def __init__(
        self,
        allowed,
        result,
        reason,
        card=None,
    ):
        self.allowed = allowed
        self.result = result
        self.reason = reason
        self.card = card


class AccessPolicy:
    def __init__(self, database):
        self.database = database

    def evaluate_normal_access(self, uid, room_name="Main Entrance"):
        card = self.database.get_card(uid)

        if card is None:
            return AccessDecision(
                False,
                AccessResult.UNKNOWN_CARD,
                "Card is not enrolled",
            )

        if not card["active"]:
            return AccessDecision(
                False,
                AccessResult.DISABLED_CARD,
                f"{card['label']}'s card is disabled",
                card,
            )

        now = datetime.now(timezone.utc)

        if card["valid_from"]:
            valid_from = datetime.fromisoformat(card["valid_from"])
            if now < valid_from:
                return AccessDecision(
                    False,
                    AccessResult.EXPIRED_CARD,
                    f"{card['label']}'s card is not valid yet",
                    card,
                )

        if card["valid_until"]:
            valid_until = datetime.fromisoformat(card["valid_until"])
            if now > valid_until:
                return AccessDecision(
                    False,
                    AccessResult.EXPIRED_CARD,
                    f"{card['label']}'s card has expired",
                    card,
                )

        if card["max_uses"] is not None:
            if card["uses_count"] >= card["max_uses"]:
                return AccessDecision(
                    False,
                    AccessResult.EXPIRED_CARD,
                    f"{card['label']}'s card use limit reached",
                    card,
                )

        if not self._schedule_allows(card["id"], now):
            return AccessDecision(
                False,
                AccessResult.OUTSIDE_SCHEDULE,
                f"{card['label']} is outside permitted access time",
                card,
            )

        if not self._room_allows(card["id"], room_name):
            return AccessDecision(
                False,
                AccessResult.DENIED,
                f"{card['label']} is not authorized for this room",
                card,
            )

        return AccessDecision(
            True,
            AccessResult.GRANTED,
            f"Access granted to {card['label']} ({card['tier']})",
            card,
        )

    def is_admin(self, uid):
        card = self.database.get_card(uid)

        return bool(
            card
            and card["active"]
            and card["tier"] == Tier.ADMIN.value
        )

    def _schedule_allows(self, card_id, current_time):
        rows = self.database.connection.execute(
            """
            SELECT schedules.*
            FROM schedules
            JOIN card_schedules
                ON card_schedules.schedule_id = schedules.id
            WHERE card_schedules.card_id = ?
            AND schedules.enabled = 1
            """,
            (card_id,),
        ).fetchall()

        # No schedule means unrestricted access.
        if not rows:
            return True

        weekday = current_time.weekday()
        current = current_time.strftime("%H:%M")

        for schedule in rows:
            days = json.loads(schedule["days_json"])

            if weekday not in days:
                continue

            start = schedule["start_time"]
            end = schedule["end_time"]

            if start <= current <= end:
                return True

        return False

    def _room_allows(self, card_id, room_name):
        row = self.database.connection.execute(
            """
            SELECT 1
            FROM card_rooms
            JOIN rooms
                ON rooms.id = card_rooms.room_id
            WHERE card_rooms.card_id = ?
            AND rooms.name = ?
            AND rooms.enabled = 1
            """,
            (card_id, room_name),
        ).fetchone()

        # Until room assignments are explicitly added, Main Entrance
        # remains the default physical access point.
        if row:
            return True

        assigned_rooms = self.database.connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM card_rooms
            WHERE card_id = ?
            """,
            (card_id,),
        ).fetchone()["count"]

        return assigned_rooms == 0 and room_name == "Main Entrance"
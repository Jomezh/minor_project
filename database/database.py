import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import DATABASE_PATH, INITIAL_ADMIN_UID, Tier, DEFAULT_SCHEDULES


class Database:
    def __init__(self, path=DATABASE_PATH):
        self.path = Path(path)
        self.connection = sqlite3.connect(
            self.path,
            check_same_thread=False,
        )
        self.connection.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self):
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                enabled INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                tier TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                valid_from TEXT,
                valid_until TEXT,
                max_uses INTEGER,
                uses_count INTEGER NOT NULL DEFAULT 0,
                created_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                days_json TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS card_schedules (
                card_id INTEGER NOT NULL,
                schedule_id INTEGER NOT NULL,
                PRIMARY KEY (card_id, schedule_id),
                FOREIGN KEY (card_id) REFERENCES cards(id),
                FOREIGN KEY (schedule_id) REFERENCES schedules(id)
            );

            CREATE TABLE IF NOT EXISTS card_rooms (
                card_id INTEGER NOT NULL,
                room_id INTEGER NOT NULL,
                PRIMARY KEY (card_id, room_id),
                FOREIGN KEY (card_id) REFERENCES cards(id),
                FOREIGN KEY (room_id) REFERENCES rooms(id)
            );

            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT,
                card_id INTEGER,
                event_type TEXT NOT NULL,
                result TEXT NOT NULL,
                reason TEXT,
                actor_uid TEXT,
                door_state TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

        self.seed_defaults()
        self.connection.commit()

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def normalize_uid(uid):
        if isinstance(uid, (list, tuple)):
            uid = "-".join(f"{int(value):02X}" for value in uid)

        uid = str(uid).replace(":", "-").replace(" ", "-")
        parts = [part for part in uid.split("-") if part]

        return "-".join(part.upper().zfill(2) for part in parts)

    def seed_defaults(self):
        self.connection.execute(
            """
            INSERT OR IGNORE INTO rooms(name, enabled)
            VALUES (?, 1)
            """,
            ("Main Entrance",),
        )

        for key, schedule in DEFAULT_SCHEDULES.items():
            self.connection.execute(
                """
                INSERT OR IGNORE INTO schedules
                (name, days_json, start_time, end_time)
                VALUES (?, ?, ?, ?)
                """,
                (
                    key,
                    json.dumps(schedule["days"]),
                    schedule["start"],
                    schedule["end"],
                ),
            )

        uid = self.normalize_uid(INITIAL_ADMIN_UID)
        now = self.now()

        self.connection.execute(
            """
            INSERT OR IGNORE INTO cards
            (uid, label, tier, active, created_by, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?, ?)
            """,
            (
                uid,
                "Initial Admin",
                Tier.ADMIN.value,
                uid,
                now,
                now,
            ),
        )

    def get_card(self, uid):
        uid = self.normalize_uid(uid)

        return self.connection.execute(
            """
            SELECT *
            FROM cards
            WHERE uid = ?
            """,
            (uid,),
        ).fetchone()

    def get_card_by_id(self, card_id):
        return self.connection.execute(
            """
            SELECT *
            FROM cards
            WHERE id = ?
            """,
            (card_id,),
        ).fetchone()

    def list_cards(self):
        return self.connection.execute(
            """
            SELECT *
            FROM cards
            ORDER BY tier, label
            """
        ).fetchall()

    def create_card(
        self,
        uid,
        label,
        tier,
        created_by,
        valid_from=None,
        valid_until=None,
        max_uses=None,
    ):
        uid = self.normalize_uid(uid)
        now = self.now()

        cursor = self.connection.execute(
            """
            INSERT INTO cards
            (
                uid,
                label,
                tier,
                active,
                valid_from,
                valid_until,
                max_uses,
                created_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
            """,
            (
                uid,
                label,
                tier.value if isinstance(tier, Tier) else str(tier),
                valid_from,
                valid_until,
                max_uses,
                created_by,
                now,
                now,
            ),
        )

        self.connection.commit()
        return cursor.lastrowid

    def update_card(self, card_id, **fields):
        allowed = {
            "label",
            "tier",
            "active",
            "valid_from",
            "valid_until",
            "max_uses",
            "uses_count",
        }

        changes = {
            key: value
            for key, value in fields.items()
            if key in allowed
        }

        if not changes:
            return

        if "tier" in changes and isinstance(changes["tier"], Tier):
            changes["tier"] = changes["tier"].value

        changes["updated_at"] = self.now()

        assignments = ", ".join(
            f"{key} = ?" for key in changes
        )

        values = list(changes.values())
        values.append(card_id)

        self.connection.execute(
            f"""
            UPDATE cards
            SET {assignments}
            WHERE id = ?
            """,
            values,
        )
        self.connection.commit()

    def increment_use_count(self, card_id):
        self.connection.execute(
            """
            UPDATE cards
            SET uses_count = uses_count + 1,
                updated_at = ?
            WHERE id = ?
            """,
            (self.now(), card_id),
        )
        self.connection.commit()

    def add_log(
        self,
        uid,
        event_type,
        result,
        reason=None,
        actor_uid=None,
        card_id=None,
        door_state=None,
    ):
        self.connection.execute(
            """
            INSERT INTO access_logs
            (
                uid,
                card_id,
                event_type,
                result,
                reason,
                actor_uid,
                door_state,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.normalize_uid(uid) if uid else None,
                card_id,
                event_type,
                result,
                reason,
                self.normalize_uid(actor_uid) if actor_uid else None,
                door_state,
                self.now(),
            ),
        )
        self.connection.commit()

    def close(self):
        self.connection.close()

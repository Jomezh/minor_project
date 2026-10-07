from enum import Enum


class Tier(str, Enum):
    GUEST = "guest"
    EMPLOYEE = "employee"
    ADMIN = "admin"


class AccessResult(str, Enum):
    GRANTED = "granted"
    UNKNOWN_CARD = "unknown_card"
    DISABLED_CARD = "disabled_card"
    EXPIRED_CARD = "expired_card"
    OUTSIDE_SCHEDULE = "outside_schedule"
    ADMIN_REQUIRED = "admin_required"
    DENIED = "denied"


# GPIO numbering is BCM numbering, not physical pin numbering.

# RFID MFRC522 bit-banged SPI wiring.
RFID_CS_PIN = 18
RFID_MISO_PIN = 19
RFID_MOSI_PIN = 20
RFID_SCK_PIN = 21
RFID_RST_PIN = 12

# Door hardware.
RELAY_PIN = 5
BUZZER_PIN = 6
BUTTON_PIN = 26
REED_SWITCH_PIN = 16

# Relay states.
# Keep these values aligned with your already-tested relay controller.
RELAY_ACTIVE_LEVEL = 1
RELAY_INACTIVE_LEVEL = 0

# Initial bootstrap administrator.
INITIAL_ADMIN_UID = "9E-24-41-06"

# Door timing.
DOOR_OPEN_TIMEOUT_SECONDS = 5
DOOR_CLOSE_TIMEOUT_SECONDS = 30
ALARM_REPEAT_SECONDS = 2

# Database.
DATABASE_PATH = "access_control.db"

# Schedules are retained for the existing access-policy system.
DEFAULT_SCHEDULES = {
    "guest_daytime": {
        "name": "Guest daytime",
        "days": [0, 1, 2, 3, 4, 5, 6],
        "start": "08:00",
        "end": "18:00",
    },
    "employee_weekday": {
        "name": "Employee weekdays",
        "days": [0, 1, 2, 3, 4],
        "start": "08:00",
        "end": "18:00",
    },
    "always": {
        "name": "Always allowed",
        "days": [0, 1, 2, 3, 4, 5, 6],
        "start": "00:00",
        "end": "23:59",
    },
}
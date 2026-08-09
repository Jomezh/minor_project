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


# Hardware GPIO assignments, BCM numbering.
RFID_CS_PIN = 18
RFID_MISO_PIN = 19
RFID_MOSI_PIN = 20
RFID_SCK_PIN = 21
RFID_RST_PIN = 12

RELAY_PIN = 5
BUTTON_PIN = 26
BUZZER_PIN = 6

# GPIO5 HIGH energizes the relay.
RELAY_ACTIVE_LEVEL = 1
RELAY_INACTIVE_LEVEL = 0

# Initial administrator.
INITIAL_ADMIN_UID = "9E-24-41-06"

# Door timing.
DOOR_OPEN_TIMEOUT_SECONDS = 5
DOOR_CLOSE_TIMEOUT_SECONDS = 30
ADMIN_UNLOCK_TIMEOUT_SECONDS = 30
MOCK_DOOR_CYCLE_SECONDS = 5
ALARM_REPEAT_SECONDS = 2

# Set to True until the physical reed switch is installed.
MOCK_REED_ENABLED = True

DATABASE_PATH = "access_control.db"

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

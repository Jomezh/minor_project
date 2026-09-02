import os
import sys

# Allow imports from the project root when launched as:
# cd ~/minor_project/ui && python3 main_app.py
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Kivy must receive these settings before any other Kivy imports.
os.environ["KIVY_WINDOW"] = "sdl2"

from kivy.config import Config

# Your physical LCD is used in landscape mode by the display driver.
Config.set("graphics", "width", "320")
Config.set("graphics", "height", "240")
Config.set("graphics", "resizable", "0")
Config.set("graphics", "fullscreen", "1")
Config.set("graphics", "borderless", "1")
Config.set("kivy", "exit_on_escape", "0")

# The log confirms the ADS7846/XPT2046 controller is /dev/input/event2.
#
# Start with this configuration. If the buttons render correctly but touches
# land in the wrong location, see the alternatives below this file.
Config.set(
    "input",
    "xpt2046",
    "hidinput,/dev/input/event2,invert_y=0",
)

Config.set("input", "mouse", "mouse")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.label import Label
from kivy.uix.screenmanager import NoTransition, Screen

from config import MOCK_DOOR_CYCLE_SECONDS
from database.database import Database
from core.access_policy import AccessPolicy
from core.app_controller import AppController
from core.door_controller import DoorController
from hardware.rfid_bitbanged import RFIDBitBang
from hardware.relay_controller import RelayController
from hardware.buzzer_controller import BuzzerController
from hardware.mock_door import MockDoorSensor


KV = """
#:import dp kivy.metrics.dp

ScreenManager:
    HomeScreen:
    AdminScreen:
    EnrollScreen:
    LogsScreen:

<HomeScreen>:
    name: "home"

    BoxLayout:
        orientation: "vertical"
        padding: dp(8)
        spacing: dp(6)

        canvas.before:
            Color:
                rgba: 0.04, 0.06, 0.10, 1
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: "ACCESS CONTROL"
            font_size: "20sp"
            bold: True
            color: 0.25, 0.75, 1, 1
            size_hint_y: None
            height: dp(32)

        Label:
            text: root.door_state_text
            font_size: "22sp"
            bold: True
            color: root.door_colour
            size_hint_y: None
            height: dp(36)

        Label:
            text: root.status_text
            font_size: "15sp"
            color: 0.95, 0.95, 0.95, 1
            halign: "center"
            valign: "middle"
            text_size: self.size
            size_hint_y: 1

        Label:
            text: "Present RFID card"
            font_size: "12sp"
            color: 0.60, 0.65, 0.70, 1
            size_hint_y: None
            height: dp(22)

<AdminScreen>:
    name: "admin"

    BoxLayout:
        orientation: "vertical"
        padding: dp(8)
        spacing: dp(5)

        canvas.before:
            Color:
                rgba: 0.06, 0.05, 0.10, 1
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: "ADMIN MODE"
            font_size: "20sp"
            bold: True
            color: 1, 0.78, 0.25, 1
            size_hint_y: None
            height: dp(30)

        Label:
            text: root.status_text
            font_size: "13sp"
            color: 0.96, 0.96, 0.96, 1
            halign: "center"
            valign: "middle"
            text_size: self.size
            size_hint_y: None
            height: dp(48)

        GridLayout:
            cols: 2
            spacing: dp(6)
            size_hint_y: 1

            Button:
                text: "UNLOCK"
                font_size: "16sp"
                background_normal: ""
                background_color: 0.10, 0.55, 0.25, 1
                on_release: app.on_manual_unlock()

            Button:
                text: "LOCK"
                font_size: "16sp"
                background_normal: ""
                background_color: 0.72, 0.18, 0.18, 1
                on_release: app.on_manual_lock()

            Button:
                text: "VIEW LOGS"
                font_size: "15sp"
                background_normal: ""
                background_color: 0.12, 0.35, 0.70, 1
                on_release: app.show_logs()

            Button:
                text: "EXIT ADMIN"
                font_size: "15sp"
                background_normal: ""
                background_color: 0.35, 0.35, 0.40, 1
                on_release: app.on_exit_admin_button()

        Label:
            text: "Scan an unknown card to enroll it"
            font_size: "11sp"
            color: 0.70, 0.70, 0.75, 1
            size_hint_y: None
            height: dp(18)

<EnrollScreen>:
    name: "enroll"

    BoxLayout:
        orientation: "vertical"
        padding: dp(8)
        spacing: dp(6)

        canvas.before:
            Color:
                rgba: 0.04, 0.07, 0.08, 1
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: "ENROLL NEW CARD"
            font_size: "19sp"
            bold: True
            color: 0.25, 0.90, 0.75, 1
            size_hint_y: None
            height: dp(30)

        Label:
            text: root.uid_text
            font_size: "15sp"
            color: 0.95, 0.95, 0.95, 1
            size_hint_y: None
            height: dp(24)

        TextInput:
            id: name_input
            hint_text: "Cardholder name"
            multiline: False
            font_size: "16sp"
            padding: dp(8), dp(8)
            size_hint_y: None
            height: dp(42)

        Spinner:
            id: tier_spinner
            text: "employee"
            values: ["guest", "employee", "admin"]
            font_size: "15sp"
            size_hint_y: None
            height: dp(40)

        GridLayout:
            cols: 2
            spacing: dp(6)
            size_hint_y: None
            height: dp(50)

            Button:
                text: "SAVE"
                font_size: "16sp"
                background_normal: ""
                background_color: 0.10, 0.55, 0.25, 1
                on_release: app.on_submit_enrollment(
                    name_input.text,
                    tier_spinner.text
                )

            Button:
                text: "CANCEL"
                font_size: "16sp"
                background_normal: ""
                background_color: 0.60, 0.20, 0.20, 1
                on_release: app.on_cancel_enrollment()

        Label:
            text: root.enroll_status_text
            font_size: "13sp"
            color: 1, 0.82, 0.30, 1
            halign: "center"
            valign: "middle"
            text_size: self.size
            size_hint_y: 1

<LogsScreen>:
    name: "logs"

    BoxLayout:
        orientation: "vertical"
        padding: dp(6)
        spacing: dp(5)

        canvas.before:
            Color:
                rgba: 0.04, 0.06, 0.10, 1
            Rectangle:
                pos: self.pos
                size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(32)
            spacing: dp(6)

            Label:
                text: "RECENT ACCESS LOGS"
                font_size: "17sp"
                bold: True
                color: 0.25, 0.75, 1, 1

            Button:
                text: "BACK"
                font_size: "13sp"
                size_hint_x: 0.27
                background_normal: ""
                background_color: 0.35, 0.35, 0.40, 1
                on_release: app.back_to_admin()

        ScrollView:
            do_scroll_x: False

            GridLayout:
                id: logs_grid
                cols: 1
                spacing: dp(3)
                padding: dp(2)
                size_hint_y: None
                height: self.minimum_height
"""


class HomeScreen(Screen):
    door_state_text = StringProperty("DOOR: LOCKED")
    door_colour = StringProperty("0.30, 0.90, 0.45, 1")
    status_text = StringProperty("Waiting for RFID card...")


class AdminScreen(Screen):
    status_text = StringProperty(
        "Admin mode active\\nDoor is under manual control."
    )


class EnrollScreen(Screen):
    uid_text = StringProperty("")
    enroll_status_text = StringProperty("")


class LogsScreen(Screen):
    pass


class AccessControlApp(App):
    def build(self):
        Window.size = (320, 240)
        Window.fullscreen = True

        self.database = Database()
        self.policy = AccessPolicy(self.database)

        self.reader = RFIDBitBang()
        self.relay = RelayController()
        self.buzzer = BuzzerController()
        self.door = MockDoorSensor(MOCK_DOOR_CYCLE_SECONDS)

        self.door_controller = DoorController(
            relay=self.relay,
            buzzer=self.buzzer,
            door_sensor=self.door,
            database=self.database,
        )

        self.controller = AppController(
            database=self.database,
            access_policy=self.policy,
            door_controller=self.door_controller,
            buzzer=self.buzzer,
        )

        self.reader.initialize()

        self.card_ready = True
        self.consecutive_misses = 0
        self.miss_threshold = 6

        self.sm = Builder.load_string(KV)
        self.sm.transition = NoTransition()

        Clock.schedule_interval(self.poll_system, 0.05)
        return self.sm

    def poll_system(self, dt):
        self.controller.update()
        self.update_door_display()

        uid = self.reader.read_uid()

        if uid is None:
            self.consecutive_misses += 1

            if self.consecutive_misses >= self.miss_threshold:
                self.card_ready = True

            return

        self.consecutive_misses = 0

        if not self.card_ready:
            return

        self.card_ready = False

        normalized_uid = self.database.normalize_uid(uid)
        result = self.controller.handle_rfid_uid(normalized_uid)
        self.handle_result(result)

    def update_door_display(self):
        home = self.sm.get_screen("home")

        if self.door_controller.unlock_active:
            home.door_state_text = "DOOR: UNLOCKED"
            home.door_colour = "1, 0.65, 0.15, 1"
        else:
            home.door_state_text = "DOOR: LOCKED"
            home.door_colour = "0.30, 0.90, 0.45, 1"

    def handle_result(self, result):
        outcome = result.get("result", "")
        reason = result.get("reason", "")
        uid = result.get("uid", "")

        if outcome == "admin_mode":
            admin = self.sm.get_screen("admin")
            admin.status_text = (
                f"Admin authenticated\\n"
                f"UID: {uid}\\n"
                f"Door unlocked"
            )
            self.sm.current = "admin"
            return

        if outcome == "admin_mode_exited":
            home = self.sm.get_screen("home")
            home.status_text = "Admin mode exited\\nDoor locked"
            self.sm.current = "home"
            return

        if outcome == "enrollment_started":
            enroll = self.sm.get_screen("enroll")
            enroll.uid_text = f"Card UID: {uid}"
            enroll.enroll_status_text = ""
            enroll.ids.name_input.text = ""
            enroll.ids.tier_spinner.text = "employee"
            self.sm.current = "enroll"
            return

        if outcome == "enrollment_pending":
            return

        if outcome == "enrolled":
            admin = self.sm.get_screen("admin")
            admin.status_text = f"{reason}\\nReady to enroll another card."
            self.sm.current = "admin"
            return

        if outcome == "admin_card_lookup":
            admin = self.sm.get_screen("admin")
            admin.status_text = reason
            self.sm.current = "admin"
            return

        home = self.sm.get_screen("home")

        if outcome == "granted":
            home.status_text = f"ACCESS GRANTED\\n{reason}\\nUID: {uid}"
        else:
            home.status_text = f"ACCESS DENIED\\n{reason}\\nUID: {uid}"

        self.sm.current = "home"

    def on_manual_unlock(self):
        self.controller.admin_manual_unlock()

        admin = self.sm.get_screen("admin")
        admin.status_text = "Manual unlock active."

    def on_manual_lock(self):
        self.controller.admin_manual_lock()

        admin = self.sm.get_screen("admin")
        admin.status_text = "Manual lock applied."

    def on_exit_admin_button(self):
        admin_uid = self.controller.admin_uid

        if not admin_uid:
            return

        result = self.controller.handle_rfid_uid(admin_uid)
        self.handle_result(result)

    def on_submit_enrollment(self, label, tier):
        enroll = self.sm.get_screen("enroll")
        uid = self.controller.pending_enrollment_uid

        if not uid:
            enroll.enroll_status_text = "No card waiting for enrollment."
            return

        if not label.strip():
            enroll.enroll_status_text = "Enter a cardholder name."
            return

        result = self.controller.submit_enrollment(
            uid=uid,
            label=label.strip(),
            tier_value=tier,
        )

        self.handle_result(result)

    def on_cancel_enrollment(self):
        self.controller.cancel_enrollment()

        admin = self.sm.get_screen("admin")
        admin.status_text = "Enrollment cancelled."
        self.sm.current = "admin"

    def show_logs(self):
        logs_screen = self.sm.get_screen("logs")
        logs_grid = logs_screen.ids.logs_grid
        logs_grid.clear_widgets()

        rows = self.database.connection.execute(
            """
            SELECT uid, event_type, result, reason, created_at
            FROM access_logs
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()

        if not rows:
            logs_grid.add_widget(
                Label(
                    text="No access events recorded yet.",
                    size_hint_y=None,
                    height=30,
                    font_size="13sp",
                )
            )

        for row in rows:
            timestamp = row["created_at"][11:19]
            uid = row["uid"] or "-"
            result = row["result"] or "-"
            reason = row["reason"] or ""

            text = (
                f"{timestamp}  {uid}\\n"
                f"{result}: {reason}"
            )

            logs_grid.add_widget(
                Label(
                    text=text,
                    size_hint_y=None,
                    height=42,
                    font_size="11sp",
                    halign="left",
                    valign="middle",
                    text_size=(300, None),
                    color=(0.92, 0.92, 0.92, 1),
                )
            )

        self.sm.current = "logs"

    def back_to_admin(self):
        self.sm.current = "admin"

    def on_stop(self):
        if hasattr(self, "controller"):
            self.controller.cleanup()

        if hasattr(self, "buzzer"):
            self.buzzer.cleanup()

        if hasattr(self, "reader"):
            self.reader.cleanup()

        if hasattr(self, "database"):
            self.database.close()


if __name__ == "__main__":
    AccessControlApp().run()
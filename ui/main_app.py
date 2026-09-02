from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout

from config import MOCK_DOOR_CYCLE_SECONDS
from database.database import Database
from core.access_policy import AccessPolicy
from core.app_controller import AppController
from core.door_controller import DoorController
from hardware.rfid_bitbang import RFIDBitBang
from hardware.relay_controller import RelayController
from hardware.buzzer_controller import BuzzerController
from hardware.mock_door import MockDoorSensor


KV = """
ScreenManager:
    HomeScreen:
    AdminScreen:
    EnrollScreen:
    LogsScreen:

<HomeScreen>:
    name: "home"
    BoxLayout:
        orientation: "vertical"
        padding: 20
        spacing: 10

        Label:
            text: "Access Control"
            font_size: "28sp"
            size_hint_y: 0.2

        Label:
            text: root.door_state_text
            font_size: "22sp"
            size_hint_y: 0.2

        Label:
            id: status_label
            text: root.status_text
            font_size: "18sp"
            size_hint_y: 0.6
            halign: "center"
            valign: "middle"
            text_size: self.size

<AdminScreen>:
    name: "admin"
    BoxLayout:
        orientation: "horizontal"

        BoxLayout:
            orientation: "vertical"
            size_hint_x: 0.35
            padding: 10
            spacing: 10

            Label:
                text: "Admin Menu"
                font_size: "20sp"
                size_hint_y: 0.15

            Button:
                text: "Manual Unlock"
                on_release: app.on_manual_unlock()

            Button:
                text: "Manual Lock"
                on_release: app.on_manual_lock()

            Button:
                text: "View Logs"
                on_release: app.show_logs()

            Button:
                text: "Exit Admin"
                on_release: app.on_exit_admin_button()

        BoxLayout:
            orientation: "vertical"
            padding: 20

            Label:
                text: root.status_text
                font_size: "18sp"
                halign: "center"
                valign: "middle"
                text_size: self.size

<EnrollScreen>:
    name: "enroll"
    BoxLayout:
        orientation: "vertical"
        padding: 20
        spacing: 15

        Label:
            text: "Enroll New Card"
            font_size: "22sp"
            size_hint_y: 0.15

        Label:
            text: root.uid_text
            font_size: "18sp"
            size_hint_y: 0.15

        TextInput:
            id: name_input
            hint_text: "Cardholder name"
            multiline: False
            size_hint_y: 0.15

        Spinner:
            id: tier_spinner
            text: "guest"
            values: ["guest", "employee", "admin"]
            size_hint_y: 0.15

        BoxLayout:
            size_hint_y: 0.2
            spacing: 10

            Button:
                text: "Save"
                on_release: app.on_submit_enrollment(name_input.text, tier_spinner.text)

            Button:
                text: "Cancel"
                on_release: app.on_cancel_enrollment()

        Label:
            id: enroll_status
            text: root.enroll_status_text
            size_hint_y: 0.2

<LogsScreen>:
    name: "logs"
    BoxLayout:
        orientation: "vertical"
        padding: 10
        spacing: 10

        Button:
            text: "Back"
            size_hint_y: 0.1
            on_release: app.back_to_admin()

        ScrollView:
            GridLayout:
                id: logs_grid
                cols: 1
                size_hint_y: None
                height: self.minimum_height
"""


class HomeScreen(Screen):
    door_state_text = StringProperty("Door: LOCKED")
    status_text = StringProperty("Waiting for RFID card...")


class AdminScreen(Screen):
    status_text = StringProperty("Admin mode active. Scan admin card to exit.")


class EnrollScreen(Screen):
    uid_text = StringProperty("")
    enroll_status_text = StringProperty("")


class LogsScreen(Screen):
    pass


class AccessControlApp(App):
    def build(self):
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

        root = Builder.load_string(KV)
        self.sm = root
        self.sm.transition = NoTransition()

        Clock.schedule_interval(self.poll_rfid, 0.05)

        return root

    def poll_rfid(self, dt):
        self.controller.update()
        self.update_home_door_state()

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

    def update_home_door_state(self):
        home = self.sm.get_screen("home")
        locked = not self.door_controller.unlock_active
        home.door_state_text = f"Door: {'LOCKED' if locked else 'UNLOCKED'}"

    def handle_result(self, result):
        outcome = result.get("result")
        reason = result.get("reason", "")
        uid = result.get("uid", "")

        if outcome == "admin_mode":
            admin = self.sm.get_screen("admin")
            admin.status_text = f"Admin mode active. UID: {uid}\n{reason}"
            self.sm.current = "admin"
            return

        if outcome == "admin_mode_exited":
            home = self.sm.get_screen("home")
            home.status_text = reason
            self.sm.current = "home"
            return

        if outcome == "enrollment_started":
            enroll = self.sm.get_screen("enroll")
            enroll.uid_text = f"UID: {uid}"
            enroll.enroll_status_text = ""
            self.sm.current = "enroll"
            return

        if outcome == "enrollment_pending":
            return

        if outcome == "enrolled":
            admin = self.sm.get_screen("admin")
            admin.status_text = f"{reason}\nScan admin card to exit."
            self.sm.current = "admin"
            return

        if outcome == "admin_card_lookup":
            admin = self.sm.get_screen("admin")
            admin.status_text = f"{reason}\nScan admin card to exit."
            self.sm.current = "admin"
            return

        # Normal granted/denied scans while on the home screen.
        home = self.sm.get_screen("home")
        home.status_text = f"UID: {uid}\n{reason}"

    def on_manual_unlock(self):
        self.controller.admin_manual_unlock()
        admin = self.sm.get_screen("admin")
        admin.status_text = "Door manually unlocked."

    def on_manual_lock(self):
        self.controller.admin_manual_lock()
        admin = self.sm.get_screen("admin")
        admin.status_text = "Door manually locked."

    def on_exit_admin_button(self):
        # Reuses the same exit path as re-scanning the admin card.
        admin_uid = self.controller.admin_uid
        if admin_uid:
            self.controller.handle_rfid_uid(admin_uid)
            self.handle_result({
                "result": "admin_mode_exited",
                "reason": "Exited admin mode via button",
                "uid": admin_uid,
            })

    def on_submit_enrollment(self, label, tier):
        enroll = self.sm.get_screen("enroll")
        uid = self.controller.pending_enrollment_uid

        if not uid:
            enroll.enroll_status_text = "No pending enrollment."
            return

        if not label.strip():
            enroll.enroll_status_text = "Name cannot be empty."
            return

        result = self.controller.submit_enrollment(uid, label, tier)
        self.handle_result(result)

    def on_cancel_enrollment(self):
        self.controller.cancel_enrollment()
        admin = self.sm.get_screen("admin")
        admin.status_text = "Enrollment cancelled."
        self.sm.current = "admin"

    def show_logs(self):
        logs_screen = self.sm.get_screen("logs")
        grid = logs_screen.ids.logs_grid
        grid.clear_widgets()

        from kivy.uix.label import Label

        rows = self.database.connection.execute(
            """
            SELECT uid, event_type, result, reason, created_at
            FROM access_logs
            ORDER BY id DESC
            LIMIT 30
            """
        ).fetchall()

        for row in rows:
            text = f"{row['created_at']} | {row['uid'] or '-'} | {row['event_type']} | {row['result']} | {row['reason'] or ''}"
            grid.add_widget(Label(text=text, size_hint_y=None, height=30, font_size="12sp"))

        self.sm.current = "logs"

    def back_to_admin(self):
        self.sm.current = "admin"

    def on_stop(self):
        self.controller.cleanup()
        self.buzzer.cleanup()
        self.reader.cleanup()
        self.database.close()


if __name__ == "__main__":
    AccessControlApp().run()
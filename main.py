import queue
import traceback    
import time
import json
import threading
from datetime import datetime, timezone

from kivy.config import Config

from config import SIMULATION_MODE, Tier

if SIMULATION_MODE:
    Config.set("graphics", "width", "900")
    Config.set("graphics", "height", "600")
    Config.set("graphics", "resizable", "1")
else:
    Config.set("graphics", "width", "240")
    Config.set("graphics", "height", "320")
    Config.set("graphics", "resizable", "0")

Config.set("kivy", "exit_on_escape", "0")
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from config import SIMULATION_MODE
from core.access_policy import AccessPolicy
from core.app_controller import AppController
from core.door_controller import DoorController
from database.database import Database
from hardware.hardware_factory import create_hardware
from ui import build_ui
from ui.theme import WEEKDAYS, action_button, message_label

# On-screen keyboard pages: (page name, keys). Each page holds up to 28 keys.
KEYBOARD_PAGES_TEXT = [
    ("ABC", list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
    ("abc", list("abcdefghijklmnopqrstuvwxyz")),
    ("123", list("0123456789-_.,:/@")),
]
KEYBOARD_PAGES_NUMERIC = [
    ("123", list("0123456789-.")),
]

class ReaderPoller(threading.Thread):
    def __init__(self, reader, interval=0.1):
        super().__init__(daemon=True)
        self.reader = reader
        self.interval = interval
        self.samples = queue.Queue(maxsize=50)
        self.stop_event = threading.Event()

    def check_health(self):
        check = getattr(self.reader, "is_healthy", None)
        if check is None:
            return  # simulated reader has no health check

        try:
            if not check():
                print("RFID reader lost its configuration, re-initializing")
                self.reader.initialize()
        except Exception:
            traceback.print_exc()

    def run(self):
        last_check = time.monotonic()

        while not self.stop_event.is_set():
            now = time.monotonic()
            if now - last_check >= 1.0:
                last_check = now
                self.check_health()

            try:
                uid = self.reader.read_uid()
            except Exception:
                traceback.print_exc()
                uid = None

            try:
                self.samples.put_nowait(uid)
            except queue.Full:
                pass

            time.sleep(self.interval)

    def drain(self):
        items = []
        while True:
            try:
                items.append(self.samples.get_nowait())
            except queue.Empty:
                return items

    def stop(self):
        self.stop_event.set()

class AccessControlKivyApp(App):
    simulation_mode = BooleanProperty(SIMULATION_MODE)

    def build(self):
        self.database = Database()
        self.policy = AccessPolicy(self.database)

        self.exit_requested = threading.Event()
        self.hardware = create_hardware(self.on_physical_exit_button)

        self.reader = self.hardware["reader"]
        self.relay = self.hardware["relay"]
        self.buzzer = self.hardware["buzzer"]
        self.door_sensor = self.hardware["door_sensor"]
        self.button = self.hardware["button"]

        self.door_controller = DoorController(
            relay=self.relay,
            buzzer=self.buzzer,
            door_sensor=self.door_sensor,
            database=self.database,
        )

        self.controller = AppController(
            database=self.database,
            access_policy=self.policy,
            door_controller=self.door_controller,
            buzzer=self.buzzer,
        )

        self.reader.initialize()
        self.relay.lock()

        self.reader_poller = ReaderPoller(self.reader)
        self.reader_poller.start()

        self.card_ready = True
        self.consecutive_misses = 0
        self.miss_threshold = 6

        self.current_edit_card_id = None
        self.current_edit_schedule_id = None

        self.keyboard_callback = None
        self.keyboard_numeric = False
        self.keyboard_value = ""

        self.datetime_callback = None
        self.confirm_callback = None

        self.last_card_uid = None
        self.last_card_time = 0.0
        self.same_card_cooldown = 3.0

        self.sm = build_ui(self)

        Clock.schedule_interval(self.system_tick, 0.05)
        return self.sm

    # ---------------- Hardware / polling ----------------

    def on_physical_exit_button(self):
        self.exit_requested.set()

    def system_tick(self, dt):
        try:
            self.button.poll()
            self.controller.update()
            self.update_home_state()
            self.process_exit_request()

            for uid in self.reader_poller.drain():
                self.process_reader_sample(uid)
        except Exception:
            print("ERROR IN SYSTEM TICK:")
            traceback.print_exc()

    def process_reader_sample(self, uid):
        if uid is None:
            self.consecutive_misses += 1
            if self.consecutive_misses >= self.miss_threshold:
                self.card_ready = True
                self.last_card_uid = None
            return

        self.consecutive_misses = 0
        normalized_uid = self.database.normalize_uid(uid)

        '''print(
            f"UID {normalized_uid} ready={self.card_ready} "
            f"last={self.last_card_uid} mode={self.controller.mode}"
        )'''

        if normalized_uid == self.last_card_uid or not self.card_ready:
            return

        # In normal mode, ignore cards while the door is unlocked.
        # In admin/enrollment mode, cards must still be read.
        if (self.controller.mode == "normal"
                and self.door_controller.unlock_active):
            return

        self.card_ready = False
        self.last_card_uid = normalized_uid
        result = self.controller.handle_rfid_uid(normalized_uid)
        self.handle_result(result)

    def process_exit_request(self):
        if not self.exit_requested.is_set():
            return

        self.exit_requested.clear()

        if self.door_controller.unlock_active:
            return

        self.door_controller.unlock(
            reason="inside_exit_button",
            actor_uid=None,
        )

        self.home_status_label.text = "Exit request accepted\nDoor unlocked"

    def update_home_state(self):
        if self.door_controller.unlock_active:
            self.home_door_label.text = "DOOR: UNLOCKED"
            self.home_door_label.color = (1, 0.65, 0.15, 1)
        else:
            self.home_door_label.text = "DOOR: LOCKED"
            self.home_door_label.color = (0.30, 0.90, 0.45, 1)

        if self.controller.mode == "admin_menu":
            self.home_mode_label.text = "MODE: ADMIN"
        elif self.controller.mode == "enrollment":
            self.home_mode_label.text = "MODE: ENROLLMENT"
        else:
            self.home_mode_label.text = "MODE: NORMAL"

    def handle_result(self, result):
        outcome = result.get("result", "")
        uid = result.get("uid", "")
        reason = result.get("reason", "")

        if outcome == "admin_mode":
            self.admin_status_label.text = (
                f"Admin authenticated\nUID: {uid}\nDoor unlocked"
            )
            self.refresh_users()
            self.refresh_schedules()
            self.refresh_user_schedule_choices()
            self.refresh_schedule_spinner(self.enroll_schedule_spinner)
            self.sm.current = "admin"
            return

        if outcome == "admin_mode_exited":
            self.home_status_label.text = "Admin mode exited"
            self.sm.current = "home"
            return

        if outcome == "enrollment_started":
            self.enroll_uid_label.text = f"Card UID: {uid}"
            self.enroll_name_button.text = "Cardholder name"
            self.enroll_tier_spinner.text = "employee"
            self.enroll_message_label.text = ""
            self.refresh_schedule_spinner(self.enroll_schedule_spinner)
            self.sm.current = "enroll"
            return

        if outcome == "enrollment_pending":
            return

        if outcome == "admin_card_lookup":
            self.admin_status_label.text = reason
            self.sm.current = "admin"
            return

        if outcome == "granted":
            self.home_status_label.text = (
                f"ACCESS GRANTED\n{reason}\nUID: {uid}"
            )
        else:
            self.home_status_label.text = (
                f"ACCESS DENIED\n{reason}\nUID: {uid}"
            )

        self.sm.current = "home"

    # ---------------- Navigation ----------------

    def open_users(self):
        self.refresh_users()
        self.sm.current = "users"

    def back_to_users(self):
        self.refresh_users()
        self.sm.current = "users"

    def open_schedules(self):
        self.refresh_schedules()
        self.sm.current = "schedules"

    def back_to_schedules(self):
        self.refresh_schedules()
        self.sm.current = "schedules"

    def open_logs(self):
        self.refresh_logs()
        self.sm.current = "logs"

    def back_to_admin(self):
        self.refresh_users()
        self.refresh_schedules()
        self.refresh_user_schedule_choices()
        self.sm.current = "admin"

    # ---------------- Users ----------------

    def refresh_users(self):
        self.users_list.clear_widgets()

        cards = self.database.list_cards()

        if not cards:
            empty = message_label("No users enrolled.")
            empty.size_hint_y = None
            empty.height = dp(40)
            self.users_list.add_widget(empty)
            return

        for card in cards:
            row = BoxLayout(
                spacing=dp(4),
                size_hint_y=None,
                height=dp(46),
            )

            info = Label(
                text=(
                    f"{card['label']}\n"
                    f"{card['tier'].upper()} | "
                    f"{'ACTIVE' if card['active'] else 'DISABLED'}"
                ),
                font_size="12sp",
                halign="left",
                valign="middle",
                color=(0.93, 0.93, 0.93, 1),
                size_hint_x=0.70,
            )
            info.bind(
                width=lambda instance, value: setattr(
                    instance, "text_size", (value, None)
                )
            )

            edit = action_button(
                "EDIT",
                lambda card_id=card["id"]: self.open_user_editor(card_id),
                (0.12, 0.45, 0.80, 1),
                40,
            )
            edit.size_hint_x = 0.30

            row.add_widget(info)
            row.add_widget(edit)
            self.users_list.add_widget(row)

    def open_user_editor(self, card_id):
        print(f"EDIT: open_user_editor({card_id}) start")    
        self.current_edit_card_id = card_id
        card = self.database.get_card_by_id(card_id)

        if not card:
            return

        self.user_name_button.text = card["label"]
        self.user_tier_spinner.text = card["tier"]
        self.user_status_spinner.text = (
            "active" if card["active"] else "disabled"
        )

        schedule_ids = self.database.get_card_schedule_ids(card_id)
        schedules = self.database.list_schedules()

        selected = "No schedule"
        for schedule in schedules:
            if schedule["id"] in schedule_ids:
                selected = schedule["name"]
                break

        self.user_schedule_spinner.text = selected
        self.user_valid_from_button.text = card["valid_from"] or "Not set"
        self.user_valid_until_button.text = card["valid_until"] or "Not set"
        self.user_max_uses_button.text = (
            str(card["max_uses"])
            if card["max_uses"] is not None
            else "No limit"
        )

        self.user_editor_status_label.text = ""
        self.sm.current = "user_editor"
        print("EDIT: switched to user_editor")

    def set_user_name(self, value):
        self.user_name_button.text = f"Name: {value}"
        self.sm.current = "user_editor"

    def set_user_valid_from(self, value):
        self.user_valid_from_button.text = f"Valid from: {value or 'Not set'}"
        self.sm.current = "user_editor"

    def set_user_valid_until(self, value):
        self.user_valid_until_button.text = (
            f"Valid until: {value or 'Not set'}"
        )
        self.sm.current = "user_editor"

    def set_user_max_uses(self, value):
        if not value.strip():
            self.user_max_uses_button.text = "Max uses: No limit"
        else:
            self.user_max_uses_button.text = f"Max uses: {value.strip()}"

        self.sm.current = "user_editor"

    def save_user(self):
        if self.current_edit_card_id is None:
            return

        name = self.user_name_button.text.replace("Name: ", "")
        status = self.user_status_spinner.text == "active"
        schedule_name = self.user_schedule_spinner.text

        schedule_ids = []
        if schedule_name != "No schedule":
            schedule = self.database.get_schedule_by_name(schedule_name)
            if schedule:
                schedule_ids.append(schedule["id"])

        valid_from = self.user_valid_from_button.text.replace(
            "Valid from: ", ""
        )
        valid_until = self.user_valid_until_button.text.replace(
            "Valid until: ", ""
        )
        max_uses_text = self.user_max_uses_button.text.replace(
            "Max uses: ", ""
        )

        max_uses = None
        if max_uses_text not in ("No limit", ""):
            try:
                max_uses = int(max_uses_text)
            except ValueError:
                self.user_editor_status_label.text = (
                    "Max uses must be a number"
                )
                return

        result = self.controller.update_user(
            card_id=self.current_edit_card_id,
            actor_uid=self.controller.admin_uid,
            label=name,
            tier_value=self.user_tier_spinner.text,
            active=status,
            valid_from=valid_from if valid_from != "Not set" else None,
            valid_until=valid_until if valid_until != "Not set" else None,
            max_uses=max_uses,
            schedule_ids=schedule_ids,
        )

        self.user_editor_status_label.text = result["message"]

        if result["ok"]:
            self.refresh_users()
            self.refresh_user_schedule_choices()

    def confirm_delete_user(self):
        if self.current_edit_card_id is None:
            return

        card = self.database.get_card_by_id(self.current_edit_card_id)
        if not card:
            return

        self.open_confirm(
            f"Delete {card['label']}?\nThis cannot be undone.",
            self.delete_user_confirmed,
        )

    def delete_user_confirmed(self):
        result = self.controller.delete_user(
            self.current_edit_card_id,
            self.controller.admin_uid,
        )

        if result["ok"]:
            self.current_edit_card_id = None
            self.refresh_users()
            self.back_to_users()
        else:
            self.user_editor_status_label.text = result["message"]

    # ---------------- Enrollment ----------------

    def open_enroll(self):
        print("ENROLL: open_enroll start")
        self.enroll_uid_label.text = "Scan an unknown RFID card."
        self.enroll_name_button.text = "Cardholder name"
        self.enroll_tier_spinner.text = "employee"
        self.enroll_message_label.text = ""
        self.refresh_schedule_spinner(self.enroll_schedule_spinner)
        self.sm.current = "enroll"
        print("ENROLL: switched to enroll")

    def set_enroll_name(self, value):
        self.enroll_name_button.text = value or "Cardholder name"
        self.sm.current = "enroll"

    def on_enroll_tier_changed(self, spinner, value):
        if value == Tier.ADMIN.value:
            schedule = self.database.get_schedule_by_name("Always allowed")
        elif value == Tier.EMPLOYEE.value:
            schedule = self.database.get_schedule_by_name("Employee weekdays")
        else:
            schedule = self.database.get_schedule_by_name("Guest daytime")

        if schedule:
            self.enroll_schedule_spinner.text = schedule["name"]

    def save_enrollment(self):
        uid = self.controller.pending_enrollment_uid

        if not uid:
            self.enroll_message_label.text = (
                "No card is waiting for enrollment."
            )
            return

        name = self.enroll_name_button.text

        if name == "Cardholder name" or not name.strip():
            self.enroll_message_label.text = "Enter a cardholder name."
            return

        schedule_name = self.enroll_schedule_spinner.text
        schedule_id = None

        if schedule_name != "No schedule":
            schedule = self.database.get_schedule_by_name(schedule_name)
            if schedule:
                schedule_id = schedule["id"]

        result = self.controller.submit_enrollment(
            uid=uid,
            label=name.strip(),
            tier_value=self.enroll_tier_spinner.text,
            schedule_id=schedule_id,
        )

        self.enroll_message_label.text = result["reason"]

        if result["result"] == "enrolled":
            self.refresh_users()
            self.refresh_user_schedule_choices()
            self.back_to_admin()

    def cancel_enrollment(self):
        self.controller.cancel_enrollment()
        self.back_to_admin()

    # ---------------- Schedules ----------------

    def refresh_schedules(self):
        self.schedules_list.clear_widgets()

        schedules = self.database.list_schedules()

        if not schedules:
            empty = message_label("No schedules found.")
            empty.size_hint_y = None
            empty.height = dp(40)
            self.schedules_list.add_widget(empty)
            return

        for schedule in schedules:
            days = json.loads(schedule["days_json"])
            day_text = ", ".join(WEEKDAYS[d] for d in days)

            row = BoxLayout(
                spacing=dp(4),
                size_hint_y=None,
                height=dp(54),
            )

            info = Label(
                text=(
                    f"{schedule['name']}\n"
                    f"{day_text}\n"
                    f"{schedule['start_time']} - {schedule['end_time']} | "
                    f"{'ON' if schedule['enabled'] else 'OFF'}"
                ),
                font_size="11sp",
                halign="left",
                valign="middle",
                color=(0.93, 0.93, 0.93, 1),
                size_hint_x=0.70,
            )
            info.bind(
                width=lambda instance, value: setattr(
                    instance, "text_size", (value, None)
                )
            )

            edit = action_button(
                "EDIT",
                lambda schedule_id=schedule["id"]: self.open_schedule_editor(
                    schedule_id
                ),
                (0.45, 0.25, 0.70, 1),
                44,
            )
            edit.size_hint_x = 0.30

            row.add_widget(info)
            row.add_widget(edit)
            self.schedules_list.add_widget(row)

    def open_new_schedule(self):
        self.current_edit_schedule_id = None
        self.schedule_name_button.text = "Schedule name"
        self.schedule_start_button.text = "Start: 08:00"
        self.schedule_end_button.text = "End: 18:00"
        self.schedule_enabled_spinner.text = "enabled"

        for index, button in enumerate(self.weekday_buttons):
            selected = index < 5
            button.selected = selected
            button.background_color = (
                (0.10, 0.45, 0.80, 1)
                if selected
                else (0.22, 0.22, 0.28, 1)
            )

        self.schedule_editor_status_label.text = ""
        self.sm.current = "schedule_editor"

    def open_schedule_editor(self, schedule_id):
        self.current_edit_schedule_id = schedule_id
        schedule = self.database.get_schedule(schedule_id)

        if not schedule:
            return

        self.schedule_name_button.text = schedule["name"]
        self.schedule_start_button.text = f"Start: {schedule['start_time']}"
        self.schedule_end_button.text = f"End: {schedule['end_time']}"
        self.schedule_enabled_spinner.text = (
            "enabled" if schedule["enabled"] else "disabled"
        )

        days = json.loads(schedule["days_json"])

        for index, button in enumerate(self.weekday_buttons):
            selected = index in days
            button.selected = selected
            button.background_color = (
                (0.10, 0.45, 0.80, 1)
                if selected
                else (0.22, 0.22, 0.28, 1)
            )

        self.schedule_editor_status_label.text = ""
        self.sm.current = "schedule_editor"

    def toggle_weekday(self, button):
        button.selected = not button.selected
        button.background_color = (
            (0.10, 0.45, 0.80, 1)
            if button.selected
            else (0.22, 0.22, 0.28, 1)
        )

    def set_schedule_name(self, value):
        self.schedule_name_button.text = value or "Schedule name"
        self.sm.current = "schedule_editor"

    def set_schedule_start(self, value):
        self.schedule_start_button.text = f"Start: {value}"
        self.sm.current = "schedule_editor"

    def set_schedule_end(self, value):
        self.schedule_end_button.text = f"End: {value}"
        self.sm.current = "schedule_editor"

    def get_selected_weekdays(self):
        return [
            index
            for index, button in enumerate(self.weekday_buttons)
            if button.selected
        ]

    def save_schedule(self):
        name = self.schedule_name_button.text
        start = self.schedule_start_button.text.replace("Start: ", "")
        end = self.schedule_end_button.text.replace("End: ", "")
        enabled = self.schedule_enabled_spinner.text == "enabled"
        days = self.get_selected_weekdays()

        if self.current_edit_schedule_id is None:
            result = self.controller.create_schedule(
                actor_uid=self.controller.admin_uid,
                name=name,
                days=days,
                start_time=start,
                end_time=end,
                enabled=enabled,
            )
        else:
            result = self.controller.update_schedule(
                schedule_id=self.current_edit_schedule_id,
                actor_uid=self.controller.admin_uid,
                name=name,
                days=days,
                start_time=start,
                end_time=end,
                enabled=enabled,
            )

        self.schedule_editor_status_label.text = result["message"]

        if result["ok"]:
            self.refresh_schedules()
            self.refresh_user_schedule_choices()
            self.refresh_schedule_spinner(self.enroll_schedule_spinner)
            self.back_to_schedules()

    def confirm_delete_schedule(self):
        if self.current_edit_schedule_id is None:
            return

        schedule = self.database.get_schedule(self.current_edit_schedule_id)
        if not schedule:
            return

        self.open_confirm(
            f"Delete schedule\n{schedule['name']}?",
            self.delete_schedule_confirmed,
        )

    def delete_schedule_confirmed(self):
        result = self.controller.delete_schedule(
            self.current_edit_schedule_id,
            self.controller.admin_uid,
        )

        if result["ok"]:
            self.current_edit_schedule_id = None
            self.refresh_schedules()
            self.refresh_user_schedule_choices()
            self.back_to_schedules()
        else:
            self.schedule_editor_status_label.text = result["message"]

    # ---------------- Logs ----------------

    def refresh_logs(self):
        self.logs_list.clear_widgets()

        rows = self.database.list_logs(100)

        if not rows:
            empty = message_label("No events logged yet.")
            empty.size_hint_y = None
            empty.height = dp(40)
            self.logs_list.add_widget(empty)
            return

        for row in rows:
            timestamp = row["created_at"][11:19]
            uid = row["uid"] or "-"
            result = row["result"] or "-"
            reason = row["reason"] or "-"

            label = Label(
                text=f"{timestamp} | {uid}\n{result}: {reason}",
                font_size="11sp",
                color=(0.93, 0.93, 0.93, 1),
                halign="left",
                valign="middle",
                size_hint_y=None,
                height=dp(34),
            )
            label.bind(
                width=lambda instance, value: setattr(
                    instance, "text_size", (value, None)
                )
            )

            self.logs_list.add_widget(label)

    # ---------------- Keyboard ----------------

    def open_keyboard(self, callback, initial_text="", numeric=False):
        self.keyboard_callback = callback
        self.keyboard_numeric = numeric
        self.keyboard_value = initial_text or ""
        self.keyboard_display.text = self.keyboard_value
        self.keyboard_page = 0
        self.build_keyboard_keys()
        self.sm.current = "keyboard"

    def keyboard_pages(self):
        if self.keyboard_numeric:
            return KEYBOARD_PAGES_NUMERIC
        return KEYBOARD_PAGES_TEXT

    def build_keyboard_keys(self):
        self.keyboard_grid.clear_widgets()

        pages = self.keyboard_pages()
        self.keyboard_page %= len(pages)
        name, keys = pages[self.keyboard_page]

        self.keyboard_page_label.text = (
            f"{name}  ({self.keyboard_page + 1}/{len(pages)})"
        )

        for key in keys:
            button = Button(
                text=key,
                font_size="18sp",
                background_normal="",
                background_color=(0.15, 0.22, 0.38, 1),
            )
            button.bind(
                on_release=lambda instance, k=key: self.keyboard_press(k)
            )
            self.keyboard_grid.add_widget(button)

    def keyboard_next_page(self):
        self.keyboard_page += 1
        self.build_keyboard_keys()

    def keyboard_prev_page(self):
        self.keyboard_page -= 1
        self.build_keyboard_keys()

    def keyboard_press(self, value):
        self.keyboard_value += value
        self.keyboard_display.text = self.keyboard_value

    def keyboard_backspace(self):
        self.keyboard_value = self.keyboard_value[:-1]
        self.keyboard_display.text = self.keyboard_value

    def keyboard_clear(self):
        self.keyboard_value = ""
        self.keyboard_display.text = ""

    def keyboard_done(self):
        callback = self.keyboard_callback
        value = self.keyboard_value
        self.keyboard_callback = None
        self.sm.current = "user_editor"

        if callback:
            callback(value)

    # ---------------- Date/time ----------------

    def open_datetime(self, callback, initial_value=""):
        self.datetime_callback = callback

        if initial_value and initial_value != "Not set":
            try:
                value = datetime.fromisoformat(initial_value)
                self.year_spinner.text = str(value.year)
                self.month_spinner.text = str(value.month)
                self.day_spinner.text = str(value.day)
                self.hour_spinner.text = f"{value.hour:02d}"
                self.minute_spinner.text = f"{value.minute:02d}"
            except ValueError:
                pass

        self.datetime_title.text = "SELECT DATE / TIME"
        self.sm.current = "datetime"

    def open_time_picker(self, callback, initial_value="08:00"):
        self.datetime_callback = callback

        try:
            hour, minute = initial_value.split(":")
            self.hour_spinner.text = hour.zfill(2)
            self.minute_spinner.text = minute.zfill(2)
        except ValueError:
            self.hour_spinner.text = "08"
            self.minute_spinner.text = "00"

        self.datetime_title.text = "SELECT TIME"
        self.sm.current = "datetime"

    def datetime_clear(self):
        callback = self.datetime_callback
        self.datetime_callback = None
        self.sm.current = "user_editor"

        if callback:
            callback(None)

    def datetime_done(self):
        callback = self.datetime_callback
        self.datetime_callback = None

        try:
            value = datetime(
                int(self.year_spinner.text),
                int(self.month_spinner.text),
                int(self.day_spinner.text),
                int(self.hour_spinner.text),
                int(self.minute_spinner.text),
                tzinfo=timezone.utc,
            )
            result = value.isoformat()
        except ValueError:
            result = None

        self.datetime_title.text = "SELECT DATE / TIME"
        self.sm.current = "user_editor"

        if callback:
            callback(result)

    # ---------------- Confirmation ----------------

    def open_confirm(self, message, callback):
        self.confirm_message.text = message
        self.confirm_callback = callback
        self.sm.current = "confirm"

    def confirm_cancel(self):
        self.confirm_callback = None
        self.sm.current = "user_editor"

    def confirm_yes(self):
        callback = self.confirm_callback
        self.confirm_callback = None

        if callback:
            callback()

    # ---------------- Helpers ----------------

    def refresh_user_schedule_choices(self):
        schedules = self.database.list_schedules()
        values = ["No schedule"] + [s["name"] for s in schedules]
        self.user_schedule_spinner.values = values

    def refresh_schedule_spinner(self, spinner):
        schedules = self.database.list_schedules()
        spinner.values = ["No schedule"] + [s["name"] for s in schedules]

        if spinner.text not in spinner.values:
            spinner.text = "No schedule"

    # ---------------- Simulation ----------------

    def simulate_card(self):
        if not self.simulation_mode:
            return

        uid = self.sim_uid_input.text.strip()

        if not uid:
            self.home_status_label.text = (
                "Enter a UID before simulating a scan."
            )
            return

        if self.door_controller.unlock_active:
            self.home_status_label.text = (
                "Card scan ignored\nDoor is currently unlocked."
            )
            return

        self.reader.queue_uid(uid)

    def simulate_door_open(self):
        if self.simulation_mode:
            self.door_sensor.open()

    def simulate_door_close(self):
        if self.simulation_mode:
            self.door_sensor.close()

    def simulate_exit_button(self):
        if self.simulation_mode:
            self.button.press()

    # ---------------- Admin actions ----------------

    def manual_unlock(self):
        if self.controller.mode != "admin_menu":
            return

        self.door_controller.unlock(
            reason="admin_manual_unlock",
            actor_uid=self.controller.admin_uid,
        )
        self.admin_status_label.text = "Manual unlock active."

    def manual_lock(self):
        if self.controller.mode != "admin_menu":
            return

        self.door_controller.lock(
            reason="admin_manual_lock",
            actor_uid=self.controller.admin_uid,
        )
        self.admin_status_label.text = "Manual lock applied."

    def exit_admin(self):
        admin_uid = self.controller.admin_uid

        if not admin_uid:
            self.sm.current = "home"
            return

        result = self.controller.handle_rfid_uid(admin_uid)
        self.handle_result(result)

    # ---------------- Lifecycle ----------------

    def on_stop(self):
        if hasattr(self, "controller"):
            self.controller.cleanup()

        if hasattr(self, "button"):
            self.button.cleanup()

        if hasattr(self, "buzzer"):
            self.buzzer.cleanup()

        if hasattr(self, "reader_poller"):
            self.reader_poller.stop()
            self.reader_poller.join(timeout=1.0)

        if hasattr(self, "reader"):
            self.reader.cleanup()

        if hasattr(self, "database"):
            self.database.close()


if __name__ == "__main__":
    AccessControlKivyApp().run()

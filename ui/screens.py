import json
from datetime import datetime, timezone

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

from config import Tier
from ui.theme import (
    WEEKDAYS,
    action_button,
    add_background,
    back_bar,
    message_label,
    title_label,
)


class HomeScreen(Screen):
    pass


class AdminScreen(Screen):
    pass


class UsersScreen(Screen):
    pass


class UserEditorScreen(Screen):
    pass


class EnrollScreen(Screen):
    pass


class SchedulesScreen(Screen):
    pass


class ScheduleEditorScreen(Screen):
    pass


class LogsScreen(Screen):
    pass


class KeyboardScreen(Screen):
    pass


class DateTimeScreen(Screen):
    pass


class ConfirmScreen(Screen):
    pass


def build_ui(app):
    sm = ScreenManager()
    sm.transition = NoTransition()

    sm.add_widget(build_home_screen(app))
    sm.add_widget(build_admin_screen(app))
    sm.add_widget(build_users_screen(app))
    sm.add_widget(build_user_editor_screen(app))
    sm.add_widget(build_enroll_screen(app))
    sm.add_widget(build_schedules_screen(app))
    sm.add_widget(build_schedule_editor_screen(app))
    sm.add_widget(build_logs_screen(app))
    sm.add_widget(build_keyboard_screen(app))
    sm.add_widget(build_datetime_screen(app))
    sm.add_widget(build_confirm_screen(app))

    return sm


# ---------------------------------------------------------------- Home


def build_home_screen(app):
    screen = HomeScreen(name="home")
    root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
    add_background(root, 0.06, 0.08, 0.12)

    root.add_widget(title_label("ACCESS CONTROL SYSTEM", size=28))

    app.home_door_label = Label(
        text="DOOR: LOCKED",
        font_size="24sp",
        bold=True,
        color=(0.30, 0.90, 0.45, 1),
        size_hint_y=None,
        height=dp(40),
    )
    root.add_widget(app.home_door_label)

    app.home_mode_label = Label(
        text="MODE: NORMAL",
        font_size="18sp",
        color=(0.92, 0.92, 0.92, 1),
        size_hint_y=None,
        height=dp(28),
    )
    root.add_widget(app.home_mode_label)

    app.home_status_label = message_label("Waiting for RFID card...")
    app.home_status_label.size_hint_y = 1
    root.add_widget(app.home_status_label)

    if app.simulation_mode:
        root.add_widget(title_label(
            "LAPTOP SIMULATION CONTROLS",
            (1, 0.78, 0.25, 1),
            16,
        ))

        uid_row = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(48))

        app.sim_uid_input = TextInput = __import__(
            "kivy.uix.textinput", fromlist=["TextInput"]
        ).TextInput(
            hint_text="UID, e.g. 9E-24-41-06",
            multiline=False,
            font_size="16sp",
        )
        uid_row.add_widget(app.sim_uid_input)
        uid_row.add_widget(action_button(
            "SCAN", app.simulate_card, (0.10, 0.45, 0.80, 1), 48
        ))
        root.add_widget(uid_row)

        controls = GridLayout(
            cols=3, spacing=dp(8), size_hint_y=None, height=dp(52)
        )
        controls.add_widget(action_button(
            "DOOR OPEN", app.simulate_door_open, (0.70, 0.48, 0.12, 1), 52
        ))
        controls.add_widget(action_button(
            "DOOR CLOSE", app.simulate_door_close, (0.12, 0.55, 0.28, 1), 52
        ))
        controls.add_widget(action_button(
            "EXIT BTN", app.simulate_exit_button, (0.50, 0.18, 0.18, 1), 52
        ))
        root.add_widget(controls)

    screen.add_widget(root)
    return screen


# ---------------------------------------------------------------- Admin


def build_admin_screen(app):
    screen = AdminScreen(name="admin")
    root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
    add_background(root, 0.10, 0.07, 0.12)

    root.add_widget(title_label("ADMIN DASHBOARD", (1, 0.78, 0.25, 1), 26))

    app.admin_status_label = message_label("Admin mode active.")
    app.admin_status_label.size_hint_y = 0.18
    root.add_widget(app.admin_status_label)

    grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=1)

    grid.add_widget(action_button(
        "USERS", app.open_users, (0.12, 0.35, 0.70, 1), 70
    ))
    grid.add_widget(action_button(
        "ENROLL CARD", app.open_enroll, (0.10, 0.55, 0.45, 1), 70
    ))
    grid.add_widget(action_button(
        "SCHEDULES", app.open_schedules, (0.45, 0.25, 0.70, 1), 70
    ))
    grid.add_widget(action_button(
        "LOGS", app.open_logs, (0.12, 0.45, 0.60, 1), 70
    ))
    grid.add_widget(action_button(
        "UNLOCK DOOR", app.manual_unlock, (0.10, 0.55, 0.25, 1), 70
    ))
    grid.add_widget(action_button(
        "LOCK DOOR", app.manual_lock, (0.72, 0.18, 0.18, 1), 70
    ))

    root.add_widget(grid)

    root.add_widget(action_button(
        "EXIT ADMIN", app.exit_admin, (0.35, 0.35, 0.40, 1), 56
    ))

    screen.add_widget(root)
    return screen


# ---------------------------------------------------------------- Users


def build_users_screen(app):
    screen = UsersScreen(name="users")
    root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
    add_background(root, 0.06, 0.08, 0.12)

    root.add_widget(back_bar("USERS", app.back_to_admin))

    app.users_status_label = message_label("")
    root.add_widget(app.users_status_label)

    app.users_list = GridLayout(
        cols=1, spacing=dp(6), size_hint_y=None, height=dp(1)
    )

    scroll = ScrollView(do_scroll_x=False)
    scroll.add_widget(app.users_list)
    root.add_widget(scroll)

    screen.add_widget(root)
    return screen


def build_user_editor_screen(app):
    screen = UserEditorScreen(name="user_editor")
    root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
    add_background(root, 0.07, 0.09, 0.14)

    root.add_widget(back_bar("EDIT USER", app.back_to_users))

    app.user_editor_status_label = message_label("")
    root.add_widget(app.user_editor_status_label)

    scroll = ScrollView(do_scroll_x=False)

    form = BoxLayout(
        orientation="vertical",
        spacing=dp(8),
        size_hint_y=None,
        height=dp(560),
    )

    app.user_name_button = action_button(
        "Name: Not set",
        lambda: app.open_keyboard(
            app.set_user_name,
            app.user_name_button.text.replace("Name: ", ""),
        ),
        (0.15, 0.25, 0.45, 1),
        48,
    )
    form.add_widget(app.user_name_button)

    app.user_tier_spinner = Spinner(
        text="employee",
        values=[tier.value for tier in Tier],
        font_size="16sp",
        size_hint_y=None,
        height=dp(48),
    )
    form.add_widget(app.user_tier_spinner)

    app.user_status_spinner = Spinner(
        text="active",
        values=["active", "disabled"],
        font_size="16sp",
        size_hint_y=None,
        height=dp(48),
    )
    form.add_widget(app.user_status_spinner)

    app.user_schedule_spinner = Spinner(
        text="No schedule",
        values=["No schedule"],
        font_size="16sp",
        size_hint_y=None,
        height=dp(48),
    )
    form.add_widget(app.user_schedule_spinner)

    app.user_valid_from_button = action_button(
        "Valid from: Not set",
        lambda: app.open_datetime(
            app.set_user_valid_from,
            app.user_valid_from_button.text.replace("Valid from: ", ""),
        ),
        (0.15, 0.25, 0.45, 1),
        48,
    )
    form.add_widget(app.user_valid_from_button)

    app.user_valid_until_button = action_button(
        "Valid until: Not set",
        lambda: app.open_datetime(
            app.set_user_valid_until,
            app.user_valid_until_button.text.replace("Valid until: ", ""),
        ),
        (0.15, 0.25, 0.45, 1),
        48,
    )
    form.add_widget(app.user_valid_until_button)

    app.user_max_uses_button = action_button(
        "Max uses: No limit",
        lambda: app.open_keyboard(
            app.set_user_max_uses,
            app.user_max_uses_button.text.replace("Max uses: ", ""),
            numeric=True,
        ),
        (0.15, 0.25, 0.45, 1),
        48,
    )
    form.add_widget(app.user_max_uses_button)

    form.add_widget(action_button(
        "SAVE USER", app.save_user, (0.10, 0.55, 0.25, 1), 52
    ))
    form.add_widget(action_button(
        "DELETE USER", app.confirm_delete_user, (0.70, 0.18, 0.18, 1), 52
    ))

    scroll.add_widget(form)
    root.add_widget(scroll)
    screen.add_widget(root)

    return screen


# ---------------------------------------------------------------- Enroll


def build_enroll_screen(app):
    screen = EnrollScreen(name="enroll")
    root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
    add_background(root, 0.05, 0.10, 0.10)

    root.add_widget(back_bar("ENROLL CARD", app.cancel_enrollment))

    app.enroll_uid_label = Label(
        text="",
        font_size="17sp",
        color=(0.95, 0.95, 0.95, 1),
        size_hint_y=None,
        height=dp(30),
    )
    root.add_widget(app.enroll_uid_label)

    app.enroll_name_button = action_button(
        "Cardholder name",
        lambda: app.open_keyboard(
            app.set_enroll_name,
            app.enroll_name_button.text,
        ),
        (0.15, 0.25, 0.45, 1),
        48,
    )
    root.add_widget(app.enroll_name_button)

    app.enroll_tier_spinner = Spinner(
        text="employee",
        values=[tier.value for tier in Tier],
        font_size="16sp",
        size_hint_y=None,
        height=dp(48),
    )
    app.enroll_tier_spinner.bind(text=app.on_enroll_tier_changed)
    root.add_widget(app.enroll_tier_spinner)

    app.enroll_schedule_spinner = Spinner(
        text="No schedule",
        values=["No schedule"],
        font_size="16sp",
        size_hint_y=None,
        height=dp(48),
    )
    root.add_widget(app.enroll_schedule_spinner)

    app.enroll_message_label = message_label("")
    app.enroll_message_label.size_hint_y = 1
    root.add_widget(app.enroll_message_label)

    buttons = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(52))
    buttons.add_widget(action_button(
        "SAVE", app.save_enrollment, (0.10, 0.55, 0.25, 1), 52
    ))
    buttons.add_widget(action_button(
        "CANCEL", app.cancel_enrollment, (0.65, 0.20, 0.20, 1), 52
    ))
    root.add_widget(buttons)

    screen.add_widget(root)
    return screen


# ---------------------------------------------------------------- Schedules


def build_schedules_screen(app):
    screen = SchedulesScreen(name="schedules")
    root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
    add_background(root, 0.08, 0.06, 0.12)

    root.add_widget(back_bar("SCHEDULES", app.back_to_admin))

    app.schedules_status_label = message_label("")
    root.add_widget(app.schedules_status_label)

    app.schedules_list = GridLayout(
        cols=1, spacing=dp(6), size_hint_y=None, height=dp(1)
    )

    scroll = ScrollView(do_scroll_x=False)
    scroll.add_widget(app.schedules_list)
    root.add_widget(scroll)

    root.add_widget(action_button(
        "NEW SCHEDULE", app.open_new_schedule, (0.10, 0.55, 0.25, 1), 52
    ))

    screen.add_widget(root)
    return screen


def build_schedule_editor_screen(app):
    screen = ScheduleEditorScreen(name="schedule_editor")
    root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
    add_background(root, 0.09, 0.07, 0.14)

    root.add_widget(back_bar("EDIT SCHEDULE", app.back_to_schedules))

    app.schedule_editor_status_label = message_label("")
    root.add_widget(app.schedule_editor_status_label)

    scroll = ScrollView(do_scroll_x=False)

    form = BoxLayout(
        orientation="vertical",
        spacing=dp(8),
        size_hint_y=None,
        height=dp(560),
    )

    app.schedule_name_button = action_button(
        "Schedule name",
        lambda: app.open_keyboard(
            app.set_schedule_name,
            app.schedule_name_button.text,
        ),
        (0.15, 0.25, 0.45, 1),
        48,
    )
    form.add_widget(app.schedule_name_button)

    days_grid = GridLayout(
        cols=4, spacing=dp(5), size_hint_y=None, height=dp(110)
    )
    app.weekday_buttons = []

    for day in WEEKDAYS:
        button = Button(
            text=day,
            font_size="15sp",
            background_normal="",
            background_color=(0.22, 0.22, 0.28, 1),
            size_hint_y=None,
            height=dp(48),
        )
        button.selected = False
        button.bind(on_release=lambda instance: app.toggle_weekday(instance))
        app.weekday_buttons.append(button)
        days_grid.add_widget(button)

    form.add_widget(days_grid)

    app.schedule_start_button = action_button(
        "Start: 08:00",
        lambda: app.open_time_picker(
            app.set_schedule_start,
            app.schedule_start_button.text.replace("Start: ", ""),
        ),
        (0.15, 0.25, 0.45, 1),
        48,
    )
    form.add_widget(app.schedule_start_button)

    app.schedule_end_button = action_button(
        "End: 18:00",
        lambda: app.open_time_picker(
            app.set_schedule_end,
            app.schedule_end_button.text.replace("End: ", ""),
        ),
        (0.15, 0.25, 0.45, 1),
        48,
    )
    form.add_widget(app.schedule_end_button)

    app.schedule_enabled_spinner = Spinner(
        text="enabled",
        values=["enabled", "disabled"],
        font_size="16sp",
        size_hint_y=None,
        height=dp(48),
    )
    form.add_widget(app.schedule_enabled_spinner)

    form.add_widget(action_button(
        "SAVE SCHEDULE", app.save_schedule, (0.10, 0.55, 0.25, 1), 52
    ))
    form.add_widget(action_button(
        "DELETE SCHEDULE", app.confirm_delete_schedule,
        (0.70, 0.18, 0.18, 1), 52
    ))

    scroll.add_widget(form)
    root.add_widget(scroll)
    screen.add_widget(root)
    return screen


# ---------------------------------------------------------------- Logs


def build_logs_screen(app):
    screen = LogsScreen(name="logs")
    root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
    add_background(root, 0.06, 0.08, 0.12)

    root.add_widget(back_bar("ACCESS LOGS", app.back_to_admin))

    app.logs_list = GridLayout(
        cols=1, spacing=dp(5), size_hint_y=None, height=dp(1)
    )

    scroll = ScrollView(do_scroll_x=False)
    scroll.add_widget(app.logs_list)
    root.add_widget(scroll)

    screen.add_widget(root)
    return screen


# ---------------------------------------------------------------- Keyboard


def build_keyboard_screen(app):
    screen = KeyboardScreen(name="keyboard")
    root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(8))
    add_background(root, 0.06, 0.08, 0.12)

    app.keyboard_display = Label(
        text="",
        font_size="20sp",
        color=(0.95, 0.95, 0.95, 1),
        size_hint_y=None,
        height=dp(48),
    )
    root.add_widget(app.keyboard_display)

    app.keyboard_grid = GridLayout(cols=6, spacing=dp(5), size_hint_y=1)
    root.add_widget(app.keyboard_grid)

    buttons = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(52))
    buttons.add_widget(action_button(
        "SPACE", lambda: app.keyboard_press(" "), (0.20, 0.25, 0.40, 1), 52
    ))
    buttons.add_widget(action_button(
        "BACK", app.keyboard_backspace, (0.55, 0.35, 0.10, 1), 52
    ))
    buttons.add_widget(action_button(
        "CLEAR", app.keyboard_clear, (0.60, 0.20, 0.20, 1), 52
    ))
    buttons.add_widget(action_button(
        "DONE", app.keyboard_done, (0.10, 0.55, 0.25, 1), 52
    ))
    root.add_widget(buttons)

    screen.add_widget(root)
    return screen


# ---------------------------------------------------------------- Date/time


def build_datetime_screen(app):
    screen = DateTimeScreen(name="datetime")
    root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
    add_background(root, 0.06, 0.08, 0.12)

    app.datetime_title = title_label("SELECT DATE / TIME")
    root.add_widget(app.datetime_title)

    grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=1)

    now = datetime.now()

    app.year_spinner = Spinner(
        text=str(now.year),
        values=[str(year) for year in range(2024, 2036)],
        font_size="17sp",
    )
    app.month_spinner = Spinner(
        text=str(now.month),
        values=[str(month) for month in range(1, 13)],
        font_size="17sp",
    )
    app.day_spinner = Spinner(
        text=str(now.day),
        values=[str(day) for day in range(1, 32)],
        font_size="17sp",
    )
    app.hour_spinner = Spinner(
        text="08",
        values=[f"{hour:02d}" for hour in range(24)],
        font_size="17sp",
    )
    app.minute_spinner = Spinner(
        text="00",
        values=[f"{minute:02d}" for minute in range(60)],
        font_size="17sp",
    )

    for label, widget in [
        ("Year", app.year_spinner),
        ("Month", app.month_spinner),
        ("Day", app.day_spinner),
        ("Hour", app.hour_spinner),
        ("Minute", app.minute_spinner),
    ]:
        box = BoxLayout(orientation="vertical", spacing=dp(4))
        box.add_widget(Label(text=label, font_size="15sp"))
        box.add_widget(widget)
        grid.add_widget(box)

    root.add_widget(grid)

    buttons = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(52))
    buttons.add_widget(action_button(
        "CLEAR", app.datetime_clear, (0.60, 0.20, 0.20, 1), 52
    ))
    buttons.add_widget(action_button(
        "DONE", app.datetime_done, (0.10, 0.55, 0.25, 1), 52
    ))
    root.add_widget(buttons)

    screen.add_widget(root)
    return screen


# ---------------------------------------------------------------- Confirm


def build_confirm_screen(app):
    screen = ConfirmScreen(name="confirm")
    root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
    add_background(root, 0.16, 0.06, 0.06)

    app.confirm_message = Label(
        text="Are you sure?",
        font_size="20sp",
        color=(0.98, 0.90, 0.90, 1),
        halign="center",
        valign="middle",
    )
    app.confirm_message.bind(
        size=lambda instance, value: setattr(instance, "text_size", value)
    )
    root.add_widget(app.confirm_message)

    buttons = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(60))
    buttons.add_widget(action_button(
        "CANCEL", app.confirm_cancel, (0.30, 0.30, 0.36, 1), 60
    ))
    buttons.add_widget(action_button(
        "CONFIRM", app.confirm_yes, (0.72, 0.18, 0.18, 1), 60
    ))
    root.add_widget(buttons)

    screen.add_widget(root)
    return screen
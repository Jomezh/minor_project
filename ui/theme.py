from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def title_label(text, color=(0.25, 0.75, 1, 1), size=26):
    return Label(
        text=text,
        font_size=f"{size}sp",
        bold=True,
        color=color,
        size_hint_y=None,
        height=dp(44),
    )


def message_label(text="", color=(0.95, 0.95, 0.95, 1)):
    label = Label(
        text=text,
        font_size="17sp",
        color=color,
        halign="left",
        valign="top",
        size_hint_y=None,
        height=dp(70),
    )
    label.bind(
        width=lambda instance, value: setattr(
            instance, "text_size", (value, None)
        )
    )
    return label


def action_button(text, callback, color=(0.12, 0.45, 0.80, 1), height=52):
    button = Button(
        text=text,
        font_size="17sp",
        background_normal="",
        background_color=color,
        size_hint_y=None,
        height=dp(height),
    )
    button.bind(on_release=lambda instance: callback())
    return button


def back_bar(title, back_callback):
    layout = BoxLayout(
        orientation="horizontal",
        spacing=dp(8),
        size_hint_y=None,
        height=dp(48),
    )

    back = action_button(
        "BACK", back_callback, (0.35, 0.35, 0.40, 1), 44
    )
    back.size_hint_x = 0.22

    layout.add_widget(back)
    layout.add_widget(title_label(title))
    return layout


def add_background(widget, r, g, b):
    from kivy.graphics import Color, Rectangle

    with widget.canvas.before:
        Color(r, g, b, 1)
        Rectangle(pos=widget.pos, size=widget.size)
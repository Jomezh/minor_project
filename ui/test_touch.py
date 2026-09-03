import os

os.environ["KIVY_WINDOW"] = "sdl2"

from kivy.config import Config

Config.set("graphics", "width", "320")
Config.set("graphics", "height", "240")
Config.set("graphics", "fullscreen", "0")
Config.set("graphics", "borderless", "0")
Config.set("graphics", "resizable", "0")

# Avoid duplicated automatic touchscreen registration.
Config.set("input", "device_%(name)s", "")
Config.set("input", "mouse", "mouse")

# XPT2046 appears in Linux/Kivy logs as ADS7846 Touchscreen.
Config.set(
    "input",
    "xpt2046",
    "hidinput,/dev/input/event2",
)

from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.properties import ListProperty, StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label


class TouchTest(FloatLayout):
    message = StringProperty("TOUCH TEST\\n\\nTap anywhere on the screen")
    background_colour = ListProperty([0.06, 0.10, 0.18, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            self.background = Color(*self.background_colour)
            self.rectangle = Rectangle(pos=self.pos, size=self.size)

        self.label = Label(
            text=self.message,
            font_size="20sp",
            halign="center",
            valign="middle",
            color=(1, 1, 1, 1),
        )

        self.add_widget(self.label)

        self.bind(
            pos=self.update_rectangle,
            size=self.update_layout,
            message=self.update_message,
            background_colour=self.update_background,
        )

        self.update_layout()

    def update_rectangle(self, *args):
        self.rectangle.pos = self.pos

    def update_layout(self, *args):
        self.rectangle.pos = self.pos
        self.rectangle.size = self.size

        self.label.pos = self.pos
        self.label.size = self.size
        self.label.text_size = self.size

    def update_message(self, instance, value):
        self.label.text = value

    def update_background(self, instance, value):
        self.background.rgba = value

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        self.background_colour = [0.10, 0.60, 0.30, 1]

        self.message = (
            "TOUCH RECEIVED\\n\\n"
            f"X: {touch.x:.0f}\\n"
            f"Y: {touch.y:.0f}"
        )

        print(
            f"TOUCH RECEIVED: "
            f"x={touch.x:.0f}, y={touch.y:.0f}"
        )

        return True

    def on_touch_up(self, touch):
        self.background_colour = [0.06, 0.10, 0.18, 1]
        return super().on_touch_up(touch)


class TouchTestApp(App):
    def build(self):
        return TouchTest()


if __name__ == "__main__":
    TouchTestApp().run()
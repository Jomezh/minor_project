import os
import sys

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["KIVY_WINDOW"] = "sdl2"

from kivy.config import Config

Config.set("graphics", "width", "320")
Config.set("graphics", "height", "240")
Config.set("graphics", "resizable", "0")
Config.set("graphics", "fullscreen", "0")
Config.set("graphics", "borderless", "0")

# Disable Kivy's automatic provider registration to avoid event2
# being opened twice.
Config.set("input", "mouse", "")
Config.set(
    "input",
    "xpt2046",
    "hidinput,/dev/input/event2,invert_y=0",
)

from kivy.app import App
from kivy.properties import ListProperty, StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label


class TouchTestRoot(FloatLayout):
    background_colour = ListProperty([0.08, 0.12, 0.20, 1])
    message = StringProperty(
        "TOUCH TEST\\n\\nTap anywhere on the display"
    )

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        self.background_colour = [0.15, 0.60, 0.35, 1]

        self.message = (
            "TOUCH RECEIVED\\n\\n"
            f"x = {touch.x:.0f}\\n"
            f"y = {touch.y:.0f}"
        )

        print(
            f"TOUCH RECEIVED: "
            f"x={touch.x:.0f}, y={touch.y:.0f}"
        )

        return True

    def on_touch_up(self, touch):
        self.background_colour = [0.08, 0.12, 0.20, 1]
        return super().on_touch_up(touch)


class TouchTestApp(App):
    def build(self):
        root = TouchTestRoot()

        with root.canvas.before:
            from kivy.graphics import Color, Rectangle

            root.background_color_instruction = Color(
                *root.background_colour
            )

            root.background_rectangle = Rectangle(
                pos=root.pos,
                size=root.size,
            )

        root.bind(
            background_colour=self.update_background,
            pos=self.update_rectangle,
            size=self.update_rectangle,
        )

        root.add_widget(
            Label(
                text=root.message,
                font_size="22sp",
                halign="center",
                valign="middle",
                text_size=(320, 240),
                color=(1, 1, 1, 1),
            )
        )

        root.children[0].bind(
            size=lambda instance, value: setattr(
                instance,
                "text_size",
                value,
            )
        )

        root.bind(
            message=lambda instance, value: setattr(
                root.children[0],
                "text",
                value,
            )
        )

        return root

    def update_background(self, root, colour):
        root.background_color_instruction.rgba = colour

    def update_rectangle(self, root, *args):
        root.background_rectangle.pos = root.pos
        root.background_rectangle.size = root.size


if __name__ == "__main__":
    TouchTestApp().run()
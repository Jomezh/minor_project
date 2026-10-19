import time
import RPi.GPIO as GPIO
from config import BUTTON_PIN


class ButtonInput:
    def __init__(self, on_pressed, debounce=0.3):
        self.on_pressed = on_pressed
        self.debounce = debounce
        self._last_level = GPIO.HIGH
        self._last_press = 0.0

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def poll(self):
        level = GPIO.input(BUTTON_PIN)
        now = time.monotonic()
        if (level == GPIO.LOW and self._last_level == GPIO.HIGH
                and now - self._last_press > self.debounce):
            self._last_press = now
            self.on_pressed()
        self._last_level = level

    def cleanup(self):
        pass
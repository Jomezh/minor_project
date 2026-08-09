import RPi.GPIO as GPIO

from config import RELAY_PIN, RELAY_ACTIVE_LEVEL, RELAY_INACTIVE_LEVEL


class RelayController:
    def __init__(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(
            RELAY_PIN,
            GPIO.OUT,
            initial=RELAY_INACTIVE_LEVEL,
        )

    def unlock(self):
        GPIO.output(RELAY_PIN, RELAY_ACTIVE_LEVEL)

    def lock(self):
        GPIO.output(RELAY_PIN, RELAY_INACTIVE_LEVEL)

    def is_energized(self):
        return GPIO.input(RELAY_PIN) == RELAY_ACTIVE_LEVEL

    def cleanup(self):
        self.lock()

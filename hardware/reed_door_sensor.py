import RPi.GPIO as GPIO

from config import REED_SWITCH_PIN


class ReedDoorSensor:
    """
    Two-wire normally-open reed switch:

    GPIO16 ---- reed switch ---- GND

    Door closed / magnet near:
        Reed contacts close
        GPIO is pulled LOW
        is_closed() returns True

    Door open / magnet away:
        Reed contacts open
        Internal pull-up makes GPIO HIGH
        is_closed() returns False
    """

    def __init__(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(
            REED_SWITCH_PIN,
            GPIO.IN,
            pull_up_down=GPIO.PUD_UP,
        )

    def is_closed(self):
        return GPIO.input(REED_SWITCH_PIN) == GPIO.LOW

    def cleanup(self):
        # GPIO.cleanup() is handled centrally by RFIDBitBang.cleanup().
        pass
import traceback
import RPi.GPIO as GPIO

from config import BUTTON_PIN


class ButtonInput:
    def __init__(self, on_pressed):
        self.on_pressed = on_pressed

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(
            BUTTON_PIN,
            GPIO.IN,
            pull_up_down=GPIO.PUD_UP,
        )

        GPIO.add_event_detect(
            BUTTON_PIN,
            GPIO.FALLING,
            callback=self._pressed_callback,
            bouncetime=250,
        )

        def _pressed_callback(self, channel):
            try:
                time.sleep(0.05)

                if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    self.on_pressed()

            except Exception:
                print("ERROR IN BUTTON CALLBACK:")
                traceback.print_exc()

    def cleanup(self):
        GPIO.remove_event_detect(BUTTON_PIN)

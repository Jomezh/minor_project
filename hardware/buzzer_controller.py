import threading
import time

import RPi.GPIO as GPIO

from config import BUZZER_PIN


class BuzzerController:
    def __init__(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)
        self._lock = threading.Lock()

    def _beep(self, duration):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(BUZZER_PIN, GPIO.LOW)

    def _run_pattern(self, pattern):
        with self._lock:
            for on_time, off_time in pattern:
                self._beep(on_time)
                time.sleep(off_time)

    def play_async(self, pattern):
        thread = threading.Thread(
            target=self._run_pattern,
            args=(pattern,),
            daemon=True,
        )
        thread.start()

    def unlock_beep(self):
        # One short beep.
        self.play_async([
            (0.10, 0.0),
        ])

    def lock_beep(self):
        # Two short beeps.
        self.play_async([
            (0.10, 0.10),
            (0.10, 0.0),
        ])

    def denied_beep(self):
        # Three short beeps for denied access.
        self.play_async([
            (0.08, 0.08),
            (0.08, 0.08),
            (0.08, 0.0),
        ])

    def alarm_beep(self):
        # One alarm cycle. The door controller can repeat it.
        self.play_async([
            (0.40, 0.20),
            (0.40, 0.0),
        ])

    def cleanup(self):
        GPIO.output(BUZZER_PIN, GPIO.LOW)

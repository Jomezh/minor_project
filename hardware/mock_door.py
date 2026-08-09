import threading
import time


class MockDoorSensor:
    def __init__(self, cycle_seconds=5):
        self.cycle_seconds = cycle_seconds
        self._closed = True
        self._timer = None
        self._lock = threading.Lock()

    def is_closed(self):
        with self._lock:
            return self._closed

    def simulate_unlock_cycle(self):
        if self._timer and self._timer.is_alive():
            return

        self._timer = threading.Thread(
            target=self._cycle,
            daemon=True,
        )
        self._timer.start()

    def _cycle(self):
        time.sleep(0.5)

        with self._lock:
            self._closed = False

        time.sleep(self.cycle_seconds)

        with self._lock:
            self._closed = True

    def force_open(self):
        with self._lock:
            self._closed = False

    def force_closed(self):
        with self._lock:
            self._closed = True

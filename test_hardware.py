import time

import RPi.GPIO as GPIO

from config import MOCK_DOOR_CYCLE_SECONDS
from hardware.relay_controller import RelayController
from hardware.buzzer_controller import BuzzerController
from hardware.button_input import ButtonInput
from hardware.mock_door import MockDoorSensor


relay = RelayController()
buzzer = BuzzerController()
door = MockDoorSensor(MOCK_DOOR_CYCLE_SECONDS)


def on_exit_pressed():
    print("Exit button pressed")
    relay.unlock()
    buzzer.unlock_beep()
    door.simulate_unlock_cycle()


button = ButtonInput(on_exit_pressed)

try:
    print("Hardware test running")
    print("Relay starts locked.")
    print("Press the exit button.")
    print("Ctrl+C to stop.")

    while True:
        if not door.is_closed():
            print("Mock door: OPEN")
        else:
            if relay.is_energized():
                print("Mock door: CLOSED; locking relay")
                relay.lock()
                buzzer.lock_beep()

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nStopping hardware test")

finally:
    button.cleanup()
    relay.cleanup()
    buzzer.cleanup()
    GPIO.cleanup()

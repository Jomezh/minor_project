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

unlock_active = False
door_has_opened = False


def on_exit_pressed():
    global unlock_active
    global door_has_opened

    if unlock_active:
        print("Exit request ignored: unlock already active")
        return

    print("Exit button pressed")
    print("Unlocking relay")

    relay.unlock()
    buzzer.unlock_beep()

    unlock_active = True
    door_has_opened = False

    door.simulate_unlock_cycle()


button = ButtonInput(on_exit_pressed)

try:
    print("Hardware test running")
    print("Relay starts locked.")
    print("Press the exit button.")
    print("Ctrl+C to stop.")

    while True:
        closed = door.is_closed()

        if unlock_active and not closed:
            if not door_has_opened:
                print("Mock door: OPEN")
                door_has_opened = True

        if unlock_active and door_has_opened and closed:
            print("Mock door: CLOSED")
            print("Locking relay")

            relay.lock()
            buzzer.lock_beep()

            unlock_active = False
            door_has_opened = False

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping hardware test")

finally:
    print("Forcing relay to locked state")
    relay.lock()
    button.cleanup()
    buzzer.cleanup()
    GPIO.cleanup()

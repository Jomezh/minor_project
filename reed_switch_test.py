import time

import RPi.GPIO as GPIO

REED_SWITCH_PIN = 16


GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(
    REED_SWITCH_PIN,
    GPIO.IN,
    pull_up_down=GPIO.PUD_UP,
)

try:
    print("Reed switch test started")
    print("Move the magnet toward and away from the sensor")
    print("Press Ctrl+C to stop")

    previous_state = None

    while True:
        circuit_closed = GPIO.input(REED_SWITCH_PIN) == GPIO.LOW

        if circuit_closed != previous_state:
            if circuit_closed:
                print("Door state: CLOSED")
            else:
                print("Door state: OPEN")

            previous_state = circuit_closed

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping reed switch test")

finally:
    GPIO.cleanup()
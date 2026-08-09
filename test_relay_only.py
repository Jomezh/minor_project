import time
import RPi.GPIO as GPIO

RELAY_PIN = 5

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)

try:
    print("Relay should be OFF")
    GPIO.output(RELAY_PIN, GPIO.LOW)
    print("GPIO5 state:", GPIO.input(RELAY_PIN))
    time.sleep(5)

    print("Relay should be ON")
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    print("GPIO5 state:", GPIO.input(RELAY_PIN))
    time.sleep(5)

    print("Relay should be OFF again")
    GPIO.output(RELAY_PIN, GPIO.LOW)
    print("GPIO5 state:", GPIO.input(RELAY_PIN))
    time.sleep(5)

finally:
    print("Cleanup: forcing relay OFF")
    GPIO.output(RELAY_PIN, GPIO.LOW)
    GPIO.cleanup()
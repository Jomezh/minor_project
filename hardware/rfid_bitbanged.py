import time
import RPi.GPIO as GPIO


class RFIDBitBang:
    CS_PIN = 18
    MISO_PIN = 19
    MOSI_PIN = 20
    SCK_PIN = 21
    RST_PIN = 12

    COMMAND_REG = 0x01
    MODE_REG = 0x11
    TX_MODE_REG = 0x12
    RX_MODE_REG = 0x13
    TX_CONTROL_REG = 0x14
    TX_ASK_REG = 0x15
    T_MODE_REG = 0x2A
    T_PRESCALER_REG = 0x2B
    T_RELOAD_H_REG = 0x2C
    T_RELOAD_L_REG = 0x2D
    VERSION_REG = 0x37

    PCD_IDLE = 0x00
    PCD_SOFT_RESET = 0x0F

    def __init__(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(self.CS_PIN, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(self.MOSI_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.SCK_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.MISO_PIN, GPIO.IN)
        GPIO.setup(self.RST_PIN, GPIO.OUT, initial=GPIO.HIGH)

    def _transfer_byte(self, value):
        received = 0

        for bit in range(7, -1, -1):
            GPIO.output(self.MOSI_PIN, (value >> bit) & 1)

            GPIO.output(self.SCK_PIN, GPIO.HIGH)
            received <<= 1
            received |= GPIO.input(self.MISO_PIN)
            GPIO.output(self.SCK_PIN, GPIO.LOW)

        return received

    def write_register(self, register, value):
        address = (register << 1) & 0x7E

        GPIO.output(self.CS_PIN, GPIO.LOW)
        self._transfer_byte(address)
        self._transfer_byte(value)
        GPIO.output(self.CS_PIN, GPIO.HIGH)

    def read_register(self, register):
        address = ((register << 1) & 0x7E) | 0x80

        GPIO.output(self.CS_PIN, GPIO.LOW)
        self._transfer_byte(address)
        value = self._transfer_byte(0x00)
        GPIO.output(self.CS_PIN, GPIO.HIGH)

        return value

    def reset(self):
        GPIO.output(self.RST_PIN, GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(self.RST_PIN, GPIO.HIGH)
        time.sleep(0.05)

        self.write_register(
            self.COMMAND_REG,
            self.PCD_SOFT_RESET,
        )

        time.sleep(0.05)

    def initialize(self):
        self.reset()

        self.write_register(self.T_MODE_REG, 0x8D)
        self.write_register(self.T_PRESCALER_REG, 0x3E)
        self.write_register(self.T_RELOAD_L_REG, 30)
        self.write_register(self.T_RELOAD_H_REG, 0)

        self.write_register(self.TX_ASK_REG, 0x40)
        self.write_register(self.MODE_REG, 0x3D)
        self.write_register(self.TX_MODE_REG, 0x00)
        self.write_register(self.RX_MODE_REG, 0x00)

        tx_control = self.read_register(self.TX_CONTROL_REG)

        if (tx_control & 0x03) != 0x03:
            self.write_register(
                self.TX_CONTROL_REG,
                tx_control | 0x03,
            )

    def version(self):
        return self.read_register(self.VERSION_REG)

    def cleanup(self):
        GPIO.output(self.CS_PIN, GPIO.HIGH)
        GPIO.output(self.SCK_PIN, GPIO.LOW)
        GPIO.cleanup()
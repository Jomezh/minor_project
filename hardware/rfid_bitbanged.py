import time

import RPi.GPIO as GPIO


class RFIDBitBang:
    CS_PIN = 18
    MISO_PIN = 19
    MOSI_PIN = 20
    SCK_PIN = 21
    RST_PIN = 12

    COMMAND_REG = 0x01
    COM_IRQ_REG = 0x04
    ERROR_REG = 0x06
    FIFO_DATA_REG = 0x09
    FIFO_LEVEL_REG = 0x0A
    CONTROL_REG = 0x0C
    BIT_FRAMING_REG = 0x0D

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
    PCD_TRANSCEIVE = 0x0C
    PCD_SOFT_RESET = 0x0F

    PICC_REQA = 0x26
    PICC_ANTICOLL = 0x93

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
            GPIO.output(
                self.MOSI_PIN,
                (value >> bit) & 1,
            )

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

        tx_control = self.read_register(
            self.TX_CONTROL_REG
        )

        if (tx_control & 0x03) != 0x03:
            self.write_register(
                self.TX_CONTROL_REG,
                tx_control | 0x03,
            )

    def _set_bitmask(self, register, mask):
        value = self.read_register(register)
        self.write_register(register, value | mask)

    def _clear_bitmask(self, register, mask):
        value = self.read_register(register)
        self.write_register(register, value & ~mask)

    def _transceive(self, data, valid_bits=0):
        self.write_register(
            self.COMMAND_REG,
            self.PCD_IDLE,
        )

        self.write_register(
            self.COM_IRQ_REG,
            0x7F,
        )

        self.write_register(
            self.FIFO_LEVEL_REG,
            0x80,
        )

        for value in data:
            self.write_register(
                self.FIFO_DATA_REG,
                value,
            )

        self.write_register(
            self.BIT_FRAMING_REG,
            valid_bits,
        )

        self.write_register(
            self.COMMAND_REG,
            self.PCD_TRANSCEIVE,
        )

        self._set_bitmask(
            self.BIT_FRAMING_REG,
            0x80,
        )

        for _ in range(100):
            irq = self.read_register(self.COM_IRQ_REG)

            if irq & 0x30:
                break

            if irq & 0x01:
                self._clear_bitmask(
                    self.BIT_FRAMING_REG,
                    0x80,
                )
                return None

            time.sleep(0.001)
        else:
            self._clear_bitmask(
                self.BIT_FRAMING_REG,
                0x80,
            )
            return None

        self._clear_bitmask(
            self.BIT_FRAMING_REG,
            0x80,
        )

        error = self.read_register(self.ERROR_REG)

        if error & 0x1B:
            return None

        fifo_count = self.read_register(
            self.FIFO_LEVEL_REG
        )

        if fifo_count == 0 or fifo_count > 16:
            return None

        last_bits = self.read_register(
            self.CONTROL_REG
        ) & 0x07

        response = []

        for _ in range(fifo_count):
            response.append(
                self.read_register(
                    self.FIFO_DATA_REG
                )
            )

        return bytes(response), last_bits

    def request(self):
        self.write_register(
            self.BIT_FRAMING_REG,
            0x07,
        )

        result = self._transceive(
            [self.PICC_REQA],
            valid_bits=7,
        )

        if result is None:
            return None

        response, last_bits = result

        if last_bits != 0:
            return None

        if len(response) != 2:
            return None

        return response

    def read_uid(self):
        atqa = self.request()

        if atqa is None:
            return None

        self.write_register(
            self.BIT_FRAMING_REG,
            0x00,
        )

        result = self._transceive(
            [
                self.PICC_ANTICOLL,
                0x20,
            ],
            valid_bits=0,
        )

        if result is None:
            return None

        response, _ = result

        if len(response) != 5:
            return None

        uid_bytes = response[:4]
        received_bcc = response[4]

        calculated_bcc = 0

        for value in uid_bytes:
            calculated_bcc ^= value

        if calculated_bcc != received_bcc:
            return None

        return "-".join(
            f"{value:02X}"
            for value in uid_bytes
        )

    def version(self):
        return self.read_register(
            self.VERSION_REG
        )

    def cleanup(self):
        GPIO.output(self.CS_PIN, GPIO.HIGH)
        GPIO.output(self.SCK_PIN, GPIO.LOW)
        GPIO.cleanup()
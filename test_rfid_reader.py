from hardware.rfid_bitbang import RFIDBitBang


reader = RFIDBitBang()

try:
    reader.initialize()

    version = reader.version()

    print(f"MFRC522 version register: 0x{version:02X}")

    if version in (0x88, 0x90, 0x91, 0x92):
        print("RFID reader communication OK")
    else:
        print("Unexpected version; check wiring and reader power")

finally:
    reader.cleanup()
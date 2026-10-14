from config import SIMULATION_MODE


def create_hardware(exit_button_callback):
    if SIMULATION_MODE:
        from hardware.simulated_hardware import (
            SimulatedBuzzerController,
            SimulatedButtonInput,
            SimulatedDoorSensor,
            SimulatedRFIDReader,
            SimulatedRelayController,
        )

        return {
            "reader": SimulatedRFIDReader(),
            "relay": SimulatedRelayController(),
            "buzzer": SimulatedBuzzerController(),
            "door_sensor": SimulatedDoorSensor(),
            "button": SimulatedButtonInput(exit_button_callback),
        }

    from hardware.button_input import ButtonInput
    from hardware.buzzer_controller import BuzzerController
    from hardware.reed_door_sensor import ReedDoorSensor
    from hardware.relay_controller import RelayController
    from hardware.rfid_bitbanged import RFIDBitBang

    return {
        "reader": RFIDBitBang(),
        "relay": RelayController(),
        "buzzer": BuzzerController(),
        "door_sensor": ReedDoorSensor(),
        "button": ButtonInput(exit_button_callback),
    }
#!/usr/bin/env python3


""" INIR2-ME-100% Methane sensor

    --------- ! info ! -------------
    you might need to
    sudo chmod 666 /dev/serial0
    --------------------------------
    https://www.farnell.com/datasheets/3811223.pdf
    https://www.sgxsensortech.com/content/uploads/2019/03/AN1_INIR_Communication-_Algorithms-_V9.pdf

    ! The data sheet advises to warm up the sensor for 45 seconds before taking a reading, but it's not clear
    how much this affects the accuracy.

    related reference
    https://github.com/JohnathanSorrentino/Arduino-Due-SGX-INIR-ME-100/blob/1eba91832d06dbbd856ada810fc87a8fa4667f66/CH4_Recording_Code/CH4_Recording_Code.ino
    https://github.com/immortal-sniper1/PCB-projects-BEIA
    
    important attributes
    3.3 - 5v (5max)

    UART
    8 data, 2 stop, no parity
    baud 38400
"""

# Todo: check/monitor for serial port usage?
#  https://github.com/pyserial/pyserial/issues/415
# Todo: set timer for warmup 45 secs

from FaultCodes import FaultCodes

import os
import serial
import logging
import time

from logging import NullHandler
logging.getLogger(__name__).addHandler(NullHandler())

START_FRAME = '0000005b'
END_FRAME = '0000005d'

""" Time in seconds to attempt to read from sensor """
TIMEOUT = 4


class INIR2ME100:

    def __init__(self):
        self._serial_port_object = None
        self._serial_port_path = "/dev/serial0"
        self.check_serial_port()

    """ ascii output from sensor """
    _raw_sensor_frame = None

    def read_frame(self) -> list:
        """ This wraps the frame read in a context manager because port closing is not happening for some reason? """
        with serial.Serial(port=self._serial_port_path,
                                                 baudrate=38400,
                                                 bytesize=serial.EIGHTBITS,
                                                 timeout=2,
                                                 stopbits=serial.STOPBITS_TWO,
                                                 parity=serial.PARITY_NONE) as self._serial_port_object:
            return self._read_frame()

    def _read_frame(self) -> list:
        """ Read a single frame from the sensor over serial uart
            returns a line break stripped ascii decoded list
            :raise TimeoutError
        """

        """ counter to read serial buffer because we might try to read the port during a frame transmission"""
        read_attempts = 0
        message = []

        """ Attempt to read from sensor for TIMEOUT seconds """
        t_end = time.time() + TIMEOUT
        while time.time() < t_end:
            time.sleep(0.5)  # don't hammer the pi cpu!
            while self._serial_port_object.in_waiting and read_attempts < 20:
                read_attempts += 1

                # Todo: this will fail if the serial port is in use, like if another.service is running in the background
                # and this script is manually run! see https://github.com/pyserial/pyserial/issues/415 for exception handling
                # https://stackoverflow.com/questions/6178705/python-pyserial-how-to-know-if-a-port-is-already-open
                # logging.debug("DEBUG self._serial_port_object.readline")
                data_in = self._serial_port_object.read_until()
                data_in = data_in.strip()

                try:
                    data_decoded = data_in.decode("ascii")
                except UnicodeDecodeError as unierr:
                    logging.error("ERROR _read_frame() serial data is garbage {}".format(unierr))
                    continue

                logging.debug("DEBUG  Data: {} ({})".format(data_decoded, data_in))
                if data_decoded != START_FRAME and len(message) == 0:
                    """ if it's not the start brace [ and we've not stored any values already, keep waiting """
                    logging.debug("DEBUG {} rejected: {} len {}".format(__name__, data_decoded, len(message)))
                    # print(f"DEBUG  {data_decoded} != {START_FRAME}")
                    # print(f"DEBUG  data decoded:{data_decoded}")
                    continue
                message.append(data_decoded)
                # print(f"DEBUG appended to message, new length {len(message)}")
                if data_decoded == END_FRAME:
                    break

            if len(message) == 7:
                break

        if len(message) < 7:
            raise TimeoutError("Could not read value from INIR2ME100 Methane Sensor" + str(message))

        return message

    def check_serial_port(self):
        """
        check if the file /dev/serial0 exists
        is the serial port enabled in raspi-config?
        :return: None
        :raises FileNotFoundError
        """
        if not os.path.exists(self._serial_port_path):
            raise FileNotFoundError("self._serial_port_path: \"{}\" not found, is serial enabled in raspi-config?".format(self._serial_port_path))

class Sensor(INIR2ME100):

    """ There are 7 values returned in the frame, all hex format
        but are converted differently. Have a good read of the data sheet and the comms protocal pdf
        https://www.sgxsensortech.com/content/uploads/2019/03/AN1_INIR_Communication-_Algorithms-_V9.pdf
        [0] Start Character [ 0x000005B (HEX encoded ascii)
        [1] Gas concentration in PPM (HEX encoded int)
        [2] Faults (HEX) each bit represents a fault id, see FaultCodes
        [3] Sensor Temperature (HEX)
        [4] CRC
        [5] 1’s Compliment of CRC
        [6] End Character ] 0x000005D (HEX)
    """
    START_CHAR = '0000005b'
    END_CHAR = '0000005d'

    """ gas concentration as a percentage of volume, converted from PPM value returned from sensor """
    _gas_concentration = float

    """ temp in centigrade """
    _temperature = float

    """ hex code fault string """
    _faults = str

    def __init__(self):
        super(Sensor, self).__init__()

    def validate_response(self, message) -> bool:
        """ check message for correct ascii start and end chars
            :throws MessageIntegrityError
            Todo: do CRC check in here?
        """
        # check start and end brackets
        if not message[0] == self.START_CHAR:
            raise MessageIntegrityError(f"Bad start char. should be [, got {message[0]}")
        if not message[6] == self.END_CHAR:
            raise MessageIntegrityError(f"Bad end char. should be [, got {message[6]}")

        return True

    def gas_concentration(self, frame=None) -> float:
        """ return gas concentration as a percentage of volume.
            process ascii frame from sensor with option to pass it in for testing

            @:raises INIRException
        """
        try:
            raw_ascii_frame = frame or self.read_frame()
            logging.debug("raw frame response: {}".format(raw_ascii_frame))
            self.validate_response(raw_ascii_frame)
        except (UnicodeDecodeError, MessageIntegrityError) as e:
            raise INIRException("ERROR {}: {}".format(__name__, e))

        self._gas_concentration = self._ppm_to_percentage_by_vol(raw_ascii_frame[1])
        self.faults = raw_ascii_frame[2]
        self.temperature = raw_ascii_frame[3]
        return self._gas_concentration

    def _ppm_to_percentage_by_vol(self, ppm_in_hex) -> float:
        """ Convert ppm to percentage by volume """
        return int(ppm_in_hex, 16) / 10000

    @property
    def faults(self):
        """ fault bits """
        return self._faults

    @faults.setter
    def faults(self, faults_hex: str):
        """ hex value of fault codes """
        self._faults = faults_hex

    def get_fault_descriptions(self) -> list:
        """ return list of fault descriptions from lookup table in FaultCodes """
        faults = FaultCodes(self.faults)
        return faults.extract_faults()

    @property
    def temperature(self) -> float:
        return self._temperature

    @temperature.setter
    def temperature(self, temp_in_kelvin):
        """ Convert (kelvin * 10) to Celsius """
        self._temperature = round(int(temp_in_kelvin, 16) / 10 - 273.15, 2)


def decode_single_hex_value(hex_value: str, conversion_type: str):
    """
        hex_value: 2 char value to convert from hex
        conversion_type can be ascii or decimal
        :returns str or int depending on the response item
        :raises ValueError
    """
    decoded_value = None
    if len(hex_value) != 2:
        raise ValueError("hex value should be 2 chars")

    if conversion_type == "ascii":
        decoded_value = bytes.fromhex(hex_value).decode('utf-8')
    elif conversion_type == "decimal":
        decoded_value = int(hex_value, 16)
    else:
        raise ValueError("method only supports ascii or decimal conversion")

    return decoded_value


class MessageIntegrityError(Exception):
    pass

class INIRException(Exception):
    pass

if __name__ == '__main__':
    sensor = Sensor()
    concentration = sensor.gas_concentration()
    print("{}%".format(concentration))


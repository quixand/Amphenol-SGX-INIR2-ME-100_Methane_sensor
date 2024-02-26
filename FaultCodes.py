#!/usr/bin/env python3


# fault code response is 00000002

class FaultCodes:

    """ bit0 is lsb (00000001)
        bit7 is msb (10000000)
    """
    fault_table = {
        0: {
            '1': "Sensor not Present",
            '2': "Temperature sensor not working OR Device Temperature Out of the Operating Range",
            '3': "Active or Reference are weak",
            '4': "First Time Configuration Mode, no settings present"
        },
        1: {
            '1': "Last Reset was because of a Power on Reset",
            '2': "Last Reset was because of a Watchdog Timer",
            '3': "Last Reset was because of a Software Reset",
            '4': "Last Reset was because of an External Pin Interrupt"
        },
        2: {
            '1': "Gas concentration is not stable yet."
        },
        3: {
            '1': "DAC is switched off",
            '2': "DAC output disable in Configuration mode"
        },
        4: {
            '1': "Break Indicator P1.0 set LOW for more than the maximum word length",
            '2': "Framing Error, stop bit was invalid",
            '3': "Parity Error, stop bit was invalid",
            '4': "Overrun Error, data overwrite before being read"
        },
        5: {
            '1': "Timer1 Error",
            '2': "Timer2/Watchdog Error"
        },
        6: {
            '1': "Over Range of Conc.%v.v Operation > Full Scale",
            '2': "Under Range of Conc.%v.v",
            '3': "Warm-Up Time, data not valid"
        },
        7: {
            '1': "Unable to store Data, to the INIR",
            '2': "Unable to read Data from the INIR"
        },
    }

    def __init__(self, raw_hex_fault_code: str):
        self._raw_value = raw_hex_fault_code
        self.validate_fault_code_response()
        self._faults_reported = self.extract_faults()

    def validate_fault_code_response(self):
        if not len(self._raw_value):
            raise ValueError("expecting 8 bits in the fault code")

    def extract_faults(self) -> list:
        """ Process bits in fault string MSB first
            Ignore "a" values, this indicates no error
        """

        fault_descriptions = []
        category = 7
        for fault_bit in self._raw_value:
            print(f"got bit {fault_bit}")
            if fault_bit.lower() == 'a':
                category -= 1
                continue
            else:
                try:
                    print(f"checking category {category}")
                    print(f"checking fault_bit {fault_bit}")
                    fault_descriptions.append(self.fault_table[category][fault_bit])
                except KeyError:
                    raise UnknownFaultCode("Fault value not in known faults dictionary")
            category -= 1
        return fault_descriptions


class UnknownFaultCode(Exception):
    pass


if __name__ == '__main__':
    faults1 = FaultCodes('00000001')
    faults2 = FaultCodes('a1aaaa1a')
    faults1.extract_faults()
    faults2.extract_faults()

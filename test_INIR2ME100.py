#!/usr/bin/env python3

"""
Run in the current directory
$python -m unittest
or from project root
$python -m unittest discover lib/INIR2ME100/
"""

from INIR2ME100Methane import Sensor, MessageIntegrityError, decode_single_hex_value
from FaultCodes import FaultCodes
import unittest

example_frame_response_good = ['0000005b', '000489ae', 'a1aaaa1a', '00000ba6', '0000031b', 'fffffce4', '0000005d']
example_frame_response_bad = ['00000000', '00010011', 'a1aaaa1a', '00000ba6', '0000031b', 'fffffce4', '0000005d']


class INIR2ME100Test(unittest.TestCase):

    def test_decode_single_hex_value(self):
        self.assertEqual(decode_single_hex_value('5b', 'ascii'), "[")

    def test_decode_single_hex_value_exception(self):
        self.assertRaises(ValueError, decode_single_hex_value, '5b0', 'ascii')


class SensorTest(unittest.TestCase):
    def setUp(self):
        self.sensor = Sensor()
        self.sensor.gas_concentration(example_frame_response_good)

    # def test_first_value_is_string(self):
    #     self.assertEqual(example_frame_response[0], '0000005b')

    # def test_regex(self):
    #     self.assertRegex("FunctionCount string", 'FunctionCount', 'Should match')

    def test_validate_response(self):
        self.assertTrue(self.sensor.validate_response(example_frame_response_good))

    def test_validate_response_exception(self):
        self.assertRaises(MessageIntegrityError, self.sensor.validate_response, example_frame_response_bad)

    # def test_gas_concentration_setter(self):
    #     self.assertEqual(self.sensor.gas_concentration, 29.739)

    def test_temperature(self):
        self.assertEqual(25.05, self.sensor.temperature)


class FaultCodesTest(unittest.TestCase):

    def setUp(self):
        self.fault_codes = FaultCodes(example_frame_response_good[2])

    def test_extract_faults(self):
        expected_fault_list = ['Over Range of Conc.%v.v Operation > Full Scale', 'Last Reset was because of a Power on Reset']
        self.assertEqual(expected_fault_list, self.fault_codes.extract_faults())


if __name__ == '__main__':
    unittest.main()

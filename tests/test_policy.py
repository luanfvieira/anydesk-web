import math
import unittest
from bridge.policy import validate_id, validate_event, map_point


class PolicyTests(unittest.TestCase):
    def test_id_is_only_numeric_address(self):
        self.assertEqual(validate_id('123 456 789'), '123456789')
        for value in ['1;calc', '--settings', '123\n456', '', 123, '１２３４５６７８９', '1' * 40]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_id(value)

    def test_coordinates_are_finite_normalized(self):
        self.assertEqual(map_point(1, 1, 100, 50), (99, 49))
        self.assertEqual(map_point(0, 0, 100, 50), (0, 0))
        for x in [-1, 1.1, math.nan, math.inf, True, '0.5']:
            with self.subTest(x=x), self.assertRaises(ValueError):
                map_point(x, .5, 100, 50)

    def test_event_schema_rejects_unknown_and_shell_keys(self):
        good = {'type': 'key', 'code': 'KeyA', 'down': True}
        self.assertEqual(validate_event(good), good)
        for bad in [{}, [], {'type': 'exec'}, {'type': 'key', 'code': 'MetaLeft', 'down': True},
                    {'type': 'key', 'code': 'KeyA', 'down': 'yes'},
                    {'type': 'move', 'x': float('nan'), 'y': 0},
                    {'type': 'button', 'button': 7, 'down': True, 'x': 0, 'y': 0},
                    {'type': 'wheel', 'delta': 999999, 'x': 0, 'y': 0}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_event(bad)

    def test_geometry_must_be_positive(self):
        with self.assertRaises(ValueError):
            map_point(.5, .5, 0, 50)

import unittest

from liquid_types.ast import Const
from liquid_types.interp import interp
from liquid_types.parse import parse


class ArithmeticTests(unittest.TestCase):
    def test_precedence_and_associativity(self):
        cases = {
            "2 + 3 * 4": 14,
            "10 - 6 / 2": 7,
            "(2 + 3) * 4": 20,
            "10 - 3 - 2": 5,
            "24 / 3 / 2": 4,
            "12 / 3 * 2": 8,
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                exp = parse(source)
                self.assertEqual(interp(exp), expected)

    def test_negative_literals_and_subtraction(self):
        self.assertEqual(parse("-40"), Const(-40))
        cases = {
            "-1": -1,
            "-1 : int": -1,
            "1-2": -1,
            "1--2": 3,
            "1 - - 2": 3,
            "2*-3": -6,
            "-6 / -2": 3,
            "let x = -40; x + 42": 2,
            "let f = (x) => { x - -1 } : int => int; let x = -2; f(x)": -1,
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                exp = parse(source)
                self.assertEqual(interp(exp), expected)


if __name__ == "__main__":
    unittest.main()

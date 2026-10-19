import unittest

from lark.exceptions import UnexpectedInput

from stlc.ast import Bop, Const
from stlc.interp import interp
from stlc.parse import parse


class ArithmeticTests(unittest.TestCase):
    def test_binary_operators_take_variable_operands(self):
        for op in ("+", "-", "*", "/"):
            with self.subTest(op=op):
                self.assertEqual(parse(f"x {op} y"), Bop(op, "x", "y"))

    def test_non_anf_operands_are_rejected(self):
        for source in (
            "1 + 2", "x + 1", "1 + x", "x + -1", "x + y * z",
            "(x + y) * z", "x * (y + z)", "f(x) + y", "x + f(y)",
            "(x : int) + y", "x + (let z = 1; z)", "f(1)", "f(x + y)",
        ):
            with self.subTest(source=source), self.assertRaises(UnexpectedInput):
                parse(source)

    def test_explicit_intermediate_results(self):
        cases = {
            "let x = 2; let y = 3; let z = 4; let yz = y * z; x + yz": 14,
            "let x = 10; let y = 6; let z = 2; let yz = y / z; x - yz": 7,
            "let x = 2; let y = 3; let z = 4; let xy = x + y; xy * z": 20,
            "let x = 10; let y = 3; let z = 2; let xy = x - y; xy - z": 5,
            "let x = 24; let y = 3; let z = 2; let xy = x / y; xy / z": 4,
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(interp(parse(source)), expected)

    def test_negative_literals_and_subtraction(self):
        self.assertEqual(parse("-40"), Const(-40))
        cases = {
            "-1": -1,
            "-1 : int": -1,
            "let x = 1; let y = -2; x-y": 3,
            "let x = 2; let y = -3; x*y": -6,
            "let x = -6; let y = -2; x/y": 3,
            "let x = -40; let y = 42; x + y": 2,
            "let f = (x) => { let negone = -1; x - negone } : int => int; let x = -2; f(x)": -1,
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(interp(parse(source)), expected)


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

import z3

from liquid_types.ast import TInt, TRefine
from liquid_types.errors import TypeCheckError
from liquid_types.interp import interp
from liquid_types.logic import ConsConj, Implication, PBool, to_z3, valid
from liquid_types.parse import parse, parse_pred
from liquid_types.type import typecheck


INT = TRefine(TInt(), "v", PBool(True))


class LogicTests(unittest.TestCase):
    def test_validity_is_not_satisfiability(self):
        self.assertTrue(valid(PBool(True)))
        self.assertFalse(valid(PBool(False)))
        self.assertFalse(valid(Implication("x", TInt(), PBool(True), parse_pred("x > 0"))))
        self.assertTrue(valid(Implication("x", TInt(), parse_pred("x > 0"), parse_pred("x >= 0"))))

    def test_shadowed_binders_and_sibling_scopes(self):
        c = Implication(
            "x", TInt(), parse_pred("x = 0"),
            ConsConj(
                Implication("x", TInt(), parse_pred("x = 1"), parse_pred("x = 0")),
                parse_pred("x = 0"),
            ),
        )
        self.assertFalse(valid(c))
        with self.assertRaises(TypeCheckError):
            valid(ConsConj(Implication("x", TInt(), PBool(True), PBool(True)), parse_pred("x = x")))

    def test_unbound_names_and_malformed_formulas(self):
        for source in ("missing = missing", "1 + 2", "true = 1", "true + 1 = 2"):
            with self.subTest(source=source), self.assertRaises(TypeCheckError):
                valid(parse_pred(source))

    def test_floor_division_matches_interpreter(self):
        for x in (-5, 0, 5):
            for y in (-2, 2):
                with self.subTest(x=x, y=y):
                    source = f"let x = {x}; let y = {y}; x / y"
                    result = interp(parse(source))
                    self.assertEqual(z3.simplify(to_z3(parse_pred(f"{x} / {y}"))).as_long(), result)
                    typecheck(parse(source), TRefine(TInt(), "v", parse_pred(f"v = {result}")))

    def test_unknown_is_reported_separately(self):
        with patch("liquid_types.logic.z3.Solver") as solver:
            solver.return_value.check.return_value = z3.unknown
            solver.return_value.reason_unknown.return_value = "timeout"
            with self.assertRaisesRegex(TypeCheckError, "unknown: timeout"):
                valid(PBool(True))


class VerificationTests(unittest.TestCase):
    def test_inc_contract(self):
        for contract, accepted in (("v > x", True), ("v > x + 1", False)):
            exp = parse(f"""
                (x) => {{ let one = 1; x + one }} : x:int => int[v | {contract}]
            """)
            if accepted:
                self.assertEqual(typecheck(exp), exp.t)
            else:
                with self.assertRaisesRegex(TypeCheckError, "not valid"):
                    typecheck(exp)

    def test_division_requires_nonzero_argument(self):
        for denominator in (0, 2):
            exp = parse(f"let x = 6; let y = {denominator}; x / y")
            if denominator:
                self.assertEqual(typecheck(exp, INT), INT)
            else:
                with self.assertRaisesRegex(TypeCheckError, "not valid"):
                    typecheck(exp, INT)

    def test_external_environment_assumptions(self):
        positive = TRefine(TInt(), "v", parse_pred("v > 0"))
        exp = parse("x / y")
        typecheck(exp, INT, {"x": INT, "y": positive})
        with self.assertRaisesRegex(TypeCheckError, "not valid"):
            typecheck(exp, INT, {"x": INT, "y": INT})

    def test_dependent_environment(self):
        typecheck(
            parse("y"), TRefine(TInt(), "v", parse_pred("v > x")),
            {"x": INT, "y": TRefine(TInt(), "v", parse_pred("v = x + 1"))},
        )

    def test_bad_local_annotation_is_not_discarded(self):
        with self.assertRaisesRegex(TypeCheckError, "not valid"):
            typecheck(parse("let unused = 0 : int[v | v > 0]; 1"), INT)

    def test_higher_order_call(self):
        typecheck(parse("""
            val inc : x:int => int[v | v > x]
            let inc = (x) => { let one = 1; x + one };
            val apply : f:(int[v | v >= 0] => int[v | v > 0]) => int[v | v > 0]
            let apply = (f) => { let one = 1; f(one) };
            let result = apply(inc);
            result
        """), INT)


if __name__ == "__main__":
    unittest.main()

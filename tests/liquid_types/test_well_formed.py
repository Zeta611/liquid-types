import unittest

from liquid_types.ast import Const, TFun, TInt, TRefine
from liquid_types.errors import TypeCheckError
from liquid_types.logic import PBool
from liquid_types.parse import parse, parse_pred
from liquid_types.type import check, synth, well_formed


INT = TRefine(TInt(), "v", PBool(True))


def refined(predicate: str, binder: str = "v") -> TRefine:
    return TRefine(TInt(), binder, parse_pred(predicate))


class WellFormedTests(unittest.TestCase):
    def test_boolean_predicates_and_integer_arithmetic(self):
        for predicate in (
            "true",
            "false",
            "v > v",
            "v + 1 * 2 / 3 - 4 >= 0",
            "v <= 1 && !(v != 0) || v < 5",
            "true = false",
            "v == 0",
        ):
            with self.subTest(predicate=predicate):
                self.assertIsNone(well_formed(refined(predicate)))

    def test_rejects_wrong_sorts(self):
        for predicate in (
            "v + 1",
            "v",
            "true + 1 = 2",
            "true < false",
            "v = true",
            "v && true",
            "false || v",
            "!v",
        ):
            with self.subTest(predicate=predicate), self.assertRaises(TypeCheckError):
                well_formed(refined(predicate))

    def test_refinement_can_reference_context_and_its_own_binder(self):
        well_formed(refined("v > x"), {"x": INT})
        with self.assertRaisesRegex(TypeCheckError, "Unbound refinement variable x"):
            well_formed(refined("v > x"))

    def test_parameter_scopes_over_result_only(self):
        well_formed(TFun("x", INT, refined("v > x")))
        with self.assertRaises(TypeCheckError):
            well_formed(TFun("x", refined("v > x"), INT))

    def test_refinement_binder_does_not_escape(self):
        with self.assertRaises(TypeCheckError):
            well_formed(
                TFun("x", refined("local > 0", "local"), refined("v > local"))
            )

    def test_higher_order_parameters_and_refinement_shadowing(self):
        function = TFun("x", INT, INT)
        well_formed(TFun("f", function, INT))
        well_formed(refined("f > 0", "f"), {"f": function})
        with self.assertRaises(TypeCheckError):
            well_formed(refined("f = f"), {"f": function})

    def test_logical_calls_require_declared_signatures(self):
        for env in ({}, {"f": TFun("x", INT, INT)}):
            with self.subTest(env=env), self.assertRaisesRegex(
                TypeCheckError, "logical signature"
            ):
                well_formed(refined("f(v) > 0"), env)

    def test_annotations_and_direct_checks_validate_expected_types(self):
        for source in (
            "1 : int[v | v + 1]",
            "(x) => { x } : x:int => int[v | v > missing]",
        ):
            with self.subTest(source=source), self.assertRaises(TypeCheckError):
                synth(parse(source))
        with self.assertRaises(TypeCheckError):
            check(Const(1), refined("v > missing"))


if __name__ == "__main__":
    unittest.main()

import unittest

from liquid_types.ast import TFun, TInt, TRefine
from liquid_types.errors import TypeCheckError
from liquid_types.logic import ConsConj, Implication, InterpOp, PBool, PVar
from liquid_types.parse import parse_pred
from liquid_types.type import sub


INT = TRefine(TInt(), "v", PBool(True))


class SubtypingTests(unittest.TestCase):
    def test_base_subtyping_aligns_value_binders(self):
        source = TRefine(TInt(), "a", parse_pred("a = x + 1"))
        target = TRefine(TInt(), "b", parse_pred("b > x"))
        self.assertEqual(
            sub(source, target),
            Implication("a", TInt(), parse_pred("a = x + 1"), parse_pred("a > x")),
        )

    def test_function_subtyping_matches_textbook_example(self):
        source = TFun("x", INT, TRefine(TInt(), "r", parse_pred("r = x + 1")))
        target = TFun(
            "y",
            TRefine(TInt(), "a", parse_pred("a >= 0")),
            TRefine(TInt(), "b", parse_pred("b >= 0")),
        )
        self.assertEqual(
            sub(source, target),
            ConsConj(
                # The target domain must be a subtype of the source domain.
                Implication("a", TInt(), parse_pred("a >= 0"), PBool(True)),
                Implication(
                    "y", TInt(), parse_pred("y >= 0"),
                    Implication(
                        "r", TInt(), parse_pred("r = y + 1"), parse_pred("r >= 0")
                    ),
                ),
            ),
        )

    def test_function_parameters_do_not_become_logical_assumptions(self):
        function_arg = TFun("x", INT, INT)
        constraint = sub(TFun("f", function_arg, INT), TFun("g", function_arg, INT))
        self.assertIsInstance(constraint.c1, ConsConj)
        self.assertEqual(constraint.c2, Implication("v", TInt(), PBool(True), PBool(True)))

    def test_incompatible_shapes_are_rejected(self):
        function = TFun("x", INT, INT)
        for source, target in ((INT, function), (function, INT)):
            with self.subTest(source=source, target=target), self.assertRaises(TypeCheckError):
                sub(source, target)

    def test_parameter_alignment_cannot_capture_output_value_binder(self):
        source = TFun("x", INT, TRefine(TInt(), "y", parse_pred("y > x")))
        target = TFun("y", INT, TRefine(TInt(), "z", parse_pred("z > y")))
        result_obligation = sub(source, target).c2.c
        self.assertNotEqual(result_obligation.x, "y")
        expected = InterpOp(">", PVar(result_obligation.x), PVar("y"))
        self.assertEqual(result_obligation.p, expected)
        self.assertEqual(result_obligation.c, expected)

import unittest

from liquid_types.ast import Annot, App, Const, Fun, TFun, TInt, TRefine, Var
from liquid_types.errors import TypeCheckError
from liquid_types.logic import ConsConj, Implication, InterpOp, PBool, PVar
from liquid_types.parse import parse, parse_pred
from liquid_types.type import check, synth


TRUE = PBool(True)
INT = TRefine(TInt(), "v", TRUE)


class ConstraintGenerationTests(unittest.TestCase):
    def test_variable_synthesis_has_no_obligation(self):
        self.assertEqual(synth(Var("x"), {"x": INT}), (TRUE, INT))

    def test_application_checks_input_and_instantiates_output(self):
        function = TFun(
            "formal",
            TRefine(TInt(), "v", parse_pred("v >= 0")),
            TRefine(TInt(), "v", parse_pred("v > formal")),
        )
        env = {"f": function, "actual": TRefine(TInt(), "a", parse_pred("a = 2"))}
        self.assertEqual(
            synth(App(Var("f"), "actual"), env),
            (
                ConsConj(
                    TRUE,
                    ConsConj(TRUE, Implication("a", TInt(), parse_pred("a = 2"), parse_pred("a >= 0"))),
                ),
                TRefine(TInt(), "v", parse_pred("v > actual")),
            ),
        )

    def test_application_preserves_function_annotation_obligation(self):
        positive = TRefine(TInt(), "v", parse_pred("v > 0"))
        function = Annot(Fun("x", Const(1)), TFun("formal", INT, positive))
        self.assertEqual(
            synth(App(function, "arg"), {"arg": INT}),
            (
                ConsConj(
                    Implication(
                        "x", TInt(), TRUE,
                        ConsConj(TRUE, Implication("v", TInt(), parse_pred("v = 1"), parse_pred("v > 0"))),
                    ),
                    ConsConj(TRUE, Implication("v", TInt(), TRUE, TRUE)),
                ),
                positive,
            ),
        )

    def test_let_preserves_binding_obligation_and_scopes_body(self):
        # An invalid annotation generates an obligation; no solver runs here.
        self.assertEqual(
            check(parse("let x = 0 : int[v | v > 0]; 1"), INT),
            ConsConj(
                ConsConj(TRUE, Implication("v", TInt(), parse_pred("v = 0"), parse_pred("v > 0"))),
                Implication(
                    "x", TInt(), parse_pred("x > 0"),
                    ConsConj(TRUE, Implication("v", TInt(), parse_pred("v = 1"), TRUE)),
                ),
            ),
        )

    def test_inc_constraint_matches_section_3_4_with_true_conjuncts(self):
        function = parse("(actual) => { let one = 1; actual + one }")
        contract = TFun(
            "formal",
            TRefine(TInt(), "v", parse_pred("v >= 0")),
            TRefine(TInt(), "v", parse_pred("formal < v")),
        )
        argument_constraints = ConsConj(
            ConsConj(TRUE, Implication("v", TInt(), parse_pred("v >= 0"), TRUE)),
            ConsConj(TRUE, Implication("v", TInt(), parse_pred("v = 1"), TRUE)),
        )
        result_constraint = Implication(
            "%result", TInt(),
            InterpOp("=", PVar("%result"), parse_pred("actual + one")),
            InterpOp("<", PVar("actual"), PVar("%result")),
        )
        self.assertEqual(
            check(function, contract),
            Implication(
                "actual", TInt(), parse_pred("actual >= 0"),
                ConsConj(
                    TRUE,
                    Implication(
                        "one", TInt(), parse_pred("one = 1"),
                        ConsConj(argument_constraints, result_constraint),
                    ),
                ),
            ),
        )

    def test_higher_order_parameter_is_not_a_logical_assumption(self):
        contract = TFun("callback", TFun("x", INT, INT), INT)
        self.assertEqual(
            check(Fun("f", Const(1)), contract),
            ConsConj(TRUE, Implication("v", TInt(), parse_pred("v = 1"), TRUE)),
        )

    def test_lambda_parameter_cannot_capture_output_value_binder(self):
        exp = parse("""
        (y) => { let one = 1; y + one } : x:int => int[y | y > x]
        """)
        c, _ = synth(exp)
        result_obligation = c.c.c2.c.c2
        self.assertEqual(result_obligation.p, InterpOp(
            "=", PVar("%result"), parse_pred("y + one")
        ))
        self.assertEqual(result_obligation.c, InterpOp(">", PVar("%result"), PVar("y")))

    def test_application_argument_cannot_capture_output_value_binder(self):
        exp = parse("""
        ((x) => { let one = 1; x + one } : x:int => int[y | y > x])(y)
        """)
        _, result = synth(exp, {"y": INT})
        self.assertNotEqual(result.binder, "y")
        self.assertEqual(result.predicate, InterpOp(">", PVar(result.binder), PVar("y")))

    def test_shape_errors_remain_immediate(self):
        for exp in (Fun("x", Var("x")), App(Const(1), "arg")):
            with self.subTest(exp=exp), self.assertRaises(TypeCheckError):
                check(exp, INT, {"arg": INT})

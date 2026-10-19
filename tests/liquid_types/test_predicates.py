import unittest

from lark.exceptions import UnexpectedInput

from liquid_types.ast import Annot, Const, TFun, TInt, TRefine
from liquid_types.logic import Conj, Disj, InterpOp, Neg, PBool, PInt, PVar, UninterpFun
from liquid_types.parse import parse, parse_pred


class PredicateParserTests(unittest.TestCase):
    def test_plain_int_abbreviates_true_refinement(self):
        self.assertEqual(
            parse("1 : int"), Annot(Const(1), TRefine(TInt(), "v", PBool(True)))
        )
        for plain, explicit in (
            ("1 : int", "1 : int[v | true]"),
            (
                "(x) => { x } : int => int",
                "(x) => { x } : int[v | true] => int[v | true]",
            ),
        ):
            with self.subTest(source=plain):
                self.assertEqual(parse(plain), parse(explicit))

    def test_predicate_leaves(self):
        cases = {
            "x1": PVar("x1"),
            "true_value": PVar("true_value"),
            "falsehood": PVar("falsehood"),
            "true": PBool(True),
            "false": PBool(False),
            "42": PInt(42),
            "-42": PInt(-42),
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(parse_pred(source), expected)
        self.assertNotEqual(parse_pred("true"), parse_pred("1"))
        self.assertNotEqual(parse_pred("false"), parse_pred("0"))

    def test_arithmetic_precedence_and_subtraction(self):
        self.assertEqual(
            parse_pred("x + 2 * 3 - -1"),
            InterpOp(
                "-",
                InterpOp("+", PVar("x"), InterpOp("*", PInt(2), PInt(3))),
                PInt(-1),
            ),
        )
        self.assertEqual(
            parse_pred("8 / 2 / 2"),
            InterpOp("/", InterpOp("/", PInt(8), PInt(2)), PInt(2)),
        )

    def test_boolean_precedence(self):
        self.assertEqual(
            parse_pred("!x < 0 && x != 1 || false"),
            Disj(
                Conj(
                    Neg(InterpOp("<", PVar("x"), PInt(0))),
                    InterpOp("!=", PVar("x"), PInt(1)),
                ),
                PBool(False),
            ),
        )
        self.assertEqual(
            parse_pred("!(true || false) && true"),
            Conj(Neg(Disj(PBool(True), PBool(False))), PBool(True)),
        )

    def test_comparison_operators(self):
        for op in ("=", "==", "!=", "<", "<=", ">", ">="):
            with self.subTest(op=op):
                self.assertEqual(
                    parse_pred(f"x {op} 0"), InterpOp(op, PVar("x"), PInt(0))
                )

    def test_uninterpreted_function_arguments(self):
        self.assertEqual(
            parse_pred("f(x, g(), 1 + 2, true)"),
            UninterpFun(
                "f",
                [
                    PVar("x"),
                    UninterpFun("g", []),
                    InterpOp("+", PInt(1), PInt(2)),
                    PBool(True),
                ],
            ),
        )

    def test_refinement_annotation(self):
        self.assertEqual(
            parse("1 : int[v | v >= 0 && v < 10]"),
            Annot(
                Const(1),
                TRefine(
                    TInt(),
                    "v",
                    Conj(
                        InterpOp(">=", PVar("v"), PInt(0)),
                        InterpOp("<", PVar("v"), PInt(10)),
                    ),
                ),
            ),
        )

    def test_refinements_in_function_signature(self):
        exp = parse("""
        val inc : int[v | v >= 0] => int[result | result > 0]
        let inc = (x) => { let one = 1; x + one };
        inc
        """)
        self.assertEqual(
            exp.e1.t,
            TFun(
                "%arg0",
                TRefine(TInt(), "v", InterpOp(">=", PVar("v"), PInt(0))),
                TRefine(TInt(), "result", InterpOp(">", PVar("result"), PInt(0))),
            ),
        )

    def test_malformed_predicates(self):
        for source in ("x <", "x &&", "f(x,)", "x < y < z"):
            with self.subTest(source=source), self.assertRaises(UnexpectedInput):
                parse_pred(source)


if __name__ == "__main__":
    unittest.main()

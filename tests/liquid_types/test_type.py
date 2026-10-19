import unittest

from liquid_types.ast import TFun, TInt, TRefine
from liquid_types.logic import ConsConj, Implication, InterpOp, PBool, PVar
from liquid_types.errors import TypeCheckError
from liquid_types.interp import interp
from liquid_types.parse import parse, parse_pred
from liquid_types.type import check, prim, subst_t, synth


INT = TRefine(TInt(), "v", PBool(True))


class TypeCheckerTests(unittest.TestCase):
    def test_arithmetic_primitive_signatures(self):
        for name, op in (("add", "+"), ("sub", "-"), ("mul", "*"), ("div", "/")):
            with self.subTest(primitive=name):
                typ = prim(name)
                self.assertEqual(typ, prim(op))
                self.assertIsInstance(typ, TFun)
                self.assertEqual(typ.arg, INT)
                second = subst_t(typ.ret, typ.binder, "x")
                self.assertIsInstance(second, TFun)
                expected_arg = (
                    TRefine(TInt(), "v", parse_pred("v != 0")) if op == "/" else INT
                )
                self.assertEqual(second.arg, expected_arg)
                result = subst_t(second.ret, second.binder, "y")
                self.assertEqual(
                    result,
                    TRefine(
                        TInt(), "%result",
                        InterpOp("=", PVar("%result"), parse_pred(f"x {op} y")),
                    ),
                )

    def test_synthesize_arithmetic(self):
        for op in ("+", "-", "*", "/"):
            source = f"x {op} y"
            rhs = TRefine(TInt(), "v", parse_pred("v != 0")) if op == "/" else INT
            with self.subTest(source=source):
                c, t = synth(parse(source), {"x": INT, "y": rhs})
                self.assertEqual(
                    t,
                    TRefine(
                        TInt(), "%result",
                        InterpOp("=", PVar("%result"), parse_pred(source)),
                    ),
                )
                self.assertEqual(
                    c,
                    ConsConj(
                        ConsConj(
                            PBool(True),
                            Implication("v", TInt(), PBool(True), PBool(True)),
                        ),
                        ConsConj(PBool(True), Implication("v", TInt(), rhs.predicate, rhs.predicate)),
                    ),
                )

    def test_synthesize_integer_singletons(self):
        for source in ("0", "6", "-42"):
            with self.subTest(source=source):
                self.assertEqual(
                    synth(parse(source)),
                    (PBool(True), TRefine(TInt(), "v", parse_pred(f"v = {source}"))),
                )

    def test_arithmetic_retains_free_variables(self):
        _, result = synth(parse("v + one"), {"v": INT, "one": INT})
        self.assertEqual(
            result,
            TRefine(TInt(), "%result", InterpOp(
                "=", PVar("%result"), parse_pred("v + one")
            )),
        )

    def test_division_generates_primitive_input_obligation(self):
        for rhs in (INT, prim(0)):
            with self.subTest(rhs=rhs):
                c, _ = synth(parse("x / y"), {"x": INT, "y": rhs})
                self.assertEqual(
                    c.c2,
                    ConsConj(
                        PBool(True),
                        Implication("v", TInt(), rhs.predicate, parse_pred("v != 0")),
                    ),
                )

    def test_both_operator_arguments_must_be_bound(self):
        for env in ({"x": INT}, {"y": INT}):
            with self.subTest(env=env), self.assertRaises(TypeCheckError):
                synth(parse("x + y"), env)

    def test_arithmetic_rejects_function_operands_directly(self):
        env = {"f": TFun("x", INT, INT), "x": INT}
        for op in ("+", "-", "*", "/"):
            for source in (f"f {op} x", f"x {op} f"):
                with self.subTest(source=source), self.assertRaises(TypeCheckError):
                    synth(parse(source), env)

    def test_synthesize_plain_and_explicit_int_annotations(self):
        for source in ("1 : int", "1 : int[v | true]"):
            with self.subTest(source=source):
                self.assertEqual(
                    synth(parse(source)),
                    (
                        ConsConj(
                            PBool(True),
                            Implication("v", TInt(), parse_pred("v = 1"), PBool(True)),
                        ),
                        INT,
                    ),
                )

    def test_arithmetic_rejects_function_operands(self):
        for op in ("+", "-", "*", "/"):
            for operands in (f"f {op} x", f"x {op} f"):
                with self.subTest(operands=operands):
                    exp = parse(f"""
                    val f : int => int
                    let f = (x) => {{ x }};
                    let x = 1;
                    {operands}
                    """)
                    with self.assertRaises(TypeCheckError):
                        check(exp, INT)

    def test_synthesize_function_with_local_signature(self):
        exp = parse("""
        (answer) => {
            val inc : x:int => int
            let inc = (x) => { let one = 1; x + one };
            inc(answer)
        } : int => int
        """)
        c, t = synth(exp)
        self.assertEqual(t, TFun("%arg0", INT, INT))
        self.assertIsInstance(c, Implication)
        self.assertEqual(c.x, "answer")

    def test_nested_signatures_and_numbered_identifiers(self):
        exp = parse("""
        val inc2 : y:int => int
        let inc2 = (y) => {
            val inc1 : x1:int => int
            let inc1 = (x1) => { let one = 1; x1 + one };
            let y1 = inc1(y);
            inc1(y1)
        };
        let answer = 40;
        inc2(answer)
        """)
        self.assertIsInstance(check(exp, INT), ConsConj)
        self.assertEqual(interp(exp), 42)

    def test_function_application(self):
        exp = parse("""
        val inc : x:int => int
        let inc = (x) => {
            let one = 1;
            x + one
        };
        let answer = 40;
        let result = inc(answer);
        result
        """)
        self.assertIsInstance(check(exp, INT), ConsConj)

    def test_higher_order_application(self):
        exp = parse("""
        val inc : int => int
        let inc = (x) => { let one = 1; x + one };
        val twice : f:(int => int) => x:int => int
        let twice = (f) => {
            (x) => {
                let intermediate = f(x);
                f(intermediate)
            }
        };
        let addtwo = twice(inc);
        let answer = 40;
        let result = addtwo(answer);
        result
        """)
        self.assertIsInstance(check(exp, INT), ConsConj)


if __name__ == "__main__":
    unittest.main()

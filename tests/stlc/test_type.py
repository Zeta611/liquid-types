import unittest

from stlc.ast import TFun, TInt
from stlc.errors import TypeCheckError
from stlc.interp import interp
from stlc.parse import parse
from stlc.type import check, prim, synth


class TypeCheckerTests(unittest.TestCase):
    def test_synthesize_arithmetic(self):
        for op in ("+", "-", "*", "/"):
            with self.subTest(op=op):
                self.assertEqual(prim(op), TFun(TInt(), TFun(TInt(), TInt())))
                self.assertEqual(synth(parse(f"x {op} y"), {"x": TInt(), "y": TInt()}), TInt())

    def test_arithmetic_rejects_function_operands(self):
        env = {"f": TFun(TInt(), TInt()), "x": TInt()}
        for op in ("+", "-", "*", "/"):
            for source in (f"f {op} x", f"x {op} f"):
                with self.subTest(source=source), self.assertRaises(TypeCheckError):
                    synth(parse(source), env)

    def test_let_bound_arithmetic(self):
        exp = parse("let x = 40; let y = 2; let z = 3; let yz = y * z; x + yz")
        self.assertIsNone(check(exp, TInt()))

    def test_synthesize_function_with_local_signature(self):
        exp = parse("""
        (answer) => {
            val inc : x:int => int
            let inc = (x) => { let one = 1; x + one };
            inc(answer)
        } : int => int
        """)
        self.assertEqual(synth(exp), TFun(TInt(), TInt()))

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
        self.assertIsNone(check(exp, TInt()))
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
        self.assertIsNone(check(exp, TInt()))

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
        self.assertIsNone(check(exp, TInt()))


if __name__ == "__main__":
    unittest.main()

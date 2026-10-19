import unittest

from stlc.ast import TFun, TInt
from stlc.interp import interp
from stlc.parse import parse
from stlc.type import check, synth


class TypeCheckerTests(unittest.TestCase):
    def test_synthesize_arithmetic(self):
        exp = parse("40 + 2 * 3")
        self.assertEqual(synth(exp), TInt())

    def test_synthesize_function_with_local_signature(self):
        exp = parse("""
        (answer) => {
            val inc : x:int => int
            let inc = (x) => { x + 1 };
            inc(answer)
        } : int => int
        """)
        self.assertEqual(synth(exp), TFun(TInt(), TInt()))

    def test_nested_signatures_and_numbered_identifiers(self):
        exp = parse("""
        val inc2 : y:int => int
        let inc2 = (y) => {
            val inc1 : x1:int => int
            let inc1 = (x1) => { x1 + 1 };
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
        let inc = (x) => { x + 1 };
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

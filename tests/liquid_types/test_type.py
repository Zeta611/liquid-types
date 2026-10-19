import unittest

from liquid_types.ast import PBool, TFun, TInt, TRefine
from liquid_types.errors import TypeCheckError
from liquid_types.interp import interp
from liquid_types.parse import parse
from liquid_types.type import check, synth


INT = TRefine(TInt(), "v", PBool(True))


class TypeCheckerTests(unittest.TestCase):
    def test_synthesize_arithmetic(self):
        for source in ("40 + 2 * 3", "40 - 2", "40 / 2"):
            with self.subTest(source=source):
                self.assertEqual(synth(parse(source)), INT)

    def test_synthesize_plain_and_explicit_int_annotations(self):
        for source in ("1", "1 : int", "1 : int[v | true]"):
            with self.subTest(source=source):
                self.assertEqual(synth(parse(source)), INT)

    def test_arithmetic_rejects_function_operands(self):
        for op in ("+", "-", "*", "/"):
            for operands in (f"f {op} 1", f"1 {op} f"):
                with self.subTest(operands=operands):
                    exp = parse(f"""
                    val f : int => int
                    let f = (x) => {{ x }};
                    {operands}
                    """)
                    with self.assertRaises(TypeCheckError):
                        check(exp, INT)

    def test_synthesize_function_with_local_signature(self):
        exp = parse("""
        (answer) => {
            val inc : x:int => int
            let inc = (x) => { x + 1 };
            inc(answer)
        } : int => int
        """)
        self.assertEqual(synth(exp), TFun(INT, INT))

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
        self.assertIsNone(check(exp, INT))
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
        self.assertIsNone(check(exp, INT))

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
        self.assertIsNone(check(exp, INT))


if __name__ == "__main__":
    unittest.main()

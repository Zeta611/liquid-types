import unittest

from lark.exceptions import UnexpectedInput

from liquid_types.ast import Annot, Fun, Let, TFun, TInt, TRefine, Var
from liquid_types.logic import InterpOp, PBool, PVar
from liquid_types.interp import interp
from liquid_types.parse import parse


class ParserTests(unittest.TestCase):
    def test_signature_annotates_the_following_definition(self):
        int_type = TRefine(TInt(), "v", PBool(True))
        for separator in ("", ";"):
            with self.subTest(separator=separator):
                exp = parse(f"""
                val identity2 : arg:int => int{separator}
                let identity2 = (x1) => {{ x1 }};
                identity2
                """)
                self.assertEqual(
                    exp,
                    Let(
                        "identity2",
                        Annot(Fun("x1", Var("x1")), TFun("arg", int_type, int_type)),
                        Var("identity2"),
                    ),
                )

    def test_dependent_function_binders(self):
        exp = parse("(a) => { a } : x:int => y:int => int[v | v = x + y]")
        int_type = TRefine(TInt(), "v", PBool(True))
        self.assertEqual(
            exp.t,
            TFun(
                "x",
                int_type,
                TFun(
                    "y",
                    int_type,
                    TRefine(
                        TInt(),
                        "v",
                        InterpOp("=", PVar("v"), InterpOp("+", PVar("x"), PVar("y"))),
                    ),
                ),
            ),
        )

    def test_unnamed_arrow_does_not_capture_refinement_variables(self):
        exp = parse("1 : int => int[v | v > _arg0]")
        self.assertNotEqual(exp.t.binder, "_arg0")
        self.assertEqual(exp.t.ret.predicate, InterpOp(">", PVar("v"), PVar("_arg0")))

    def test_generated_binders_avoid_all_source_names(self):
        exp = parse("1 : _arg0:int => (int => int) => int[_arg1 | _arg1 > 0]")
        outer = exp.t.ret
        inner = outer.arg
        self.assertEqual(exp.t.binder, "_arg0")
        self.assertNotEqual(outer.binder, inner.binder)
        for binder in (outer.binder, inner.binder):
            self.assertNotIn(binder, {"_arg0", "_arg1"})
            self.assertTrue(binder.startswith("%arg"))

    def test_generated_binders_cannot_be_written_in_source(self):
        for source in (
            "%arg0",
            "1 : %arg0:int => int",
            "1 : int => int[v | v > %arg0]",
        ):
            with self.subTest(source=source), self.assertRaises(UnexpectedInput):
                parse(source)

    def test_generated_binders_are_deterministic_per_parse(self):
        source = "1 : int => int => int"
        first = parse(source)
        parse("1 : int => int")
        self.assertEqual(parse(source), first)
        self.assertNotEqual(first.t.binder, first.t.ret.binder)

    def test_nested_functions(self):
        exp = parse("""
        let inc = (x) => {
          let one = 1;
          x + one
        };
        let incf = (x) => {
          let tmp = (f) => {
            let result = f(x);
            let one = 1;
            result + one
          };
          tmp(inc)
        };
        let arg = 1;
        incf(arg)
        """)
        self.assertEqual(interp(exp), 3)


if __name__ == "__main__":
    unittest.main()

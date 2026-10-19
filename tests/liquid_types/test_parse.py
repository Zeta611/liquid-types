import unittest

from liquid_types.ast import Annot, Fun, Let, PBool, TFun, TInt, TRefine, Var
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
                        Annot(Fun("x1", Var("x1")), TFun(int_type, int_type)),
                        Var("identity2"),
                    ),
                )

    def test_nested_functions(self):
        exp = parse("""
        let inc = (x) => {
          let one = 1;
          x + one
        };
        let incf = (x) => {
          let tmp = (f) => {
            f(x) + 1
          };
          tmp(inc)
        };
        let arg = 1;
        incf(arg)
        """)
        self.assertEqual(interp(exp), 3)


if __name__ == "__main__":
    unittest.main()

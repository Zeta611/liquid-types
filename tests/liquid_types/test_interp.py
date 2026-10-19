import unittest

from liquid_types.ast import App, Bop, Const, Fun, Let, Var
from liquid_types.interp import interp


class InterpreterTests(unittest.TestCase):
    def test_let_bound_identity(self):
        exp = Let(
            "identity",
            Fun("x", Var("x")),
            Let("forty", Const(40), Let("two", Const(2),
                Let("answer", Bop("+", "forty", "two"), App(Var("identity"), "answer")),
            )),
        )
        self.assertEqual(interp(exp), 42)


if __name__ == "__main__":
    unittest.main()

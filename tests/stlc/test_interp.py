import unittest

from stlc.ast import App, Bop, Const, Fun, Let, Var
from stlc.interp import interp


class InterpreterTests(unittest.TestCase):
    def test_let_bound_identity(self):
        exp = Let(
            "identity",
            Fun("x", Var("x")),
            Let("answer", Bop("+", Const(40), Const(2)), App(Var("identity"), "answer")),
        )
        self.assertEqual(interp(exp), 42)


if __name__ == "__main__":
    unittest.main()

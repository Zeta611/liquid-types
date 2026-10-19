import unittest

from liquid_types.ast import Conj, Disj, InterpOp, Neg, PBool, PInt, PVar, UninterpFun
from liquid_types.type import subst_p


class PredicateSubstitutionTests(unittest.TestCase):
    def test_leaves(self):
        for predicate, expected in (
            (PVar("x"), PVar("y")),
            (PVar("x1"), PVar("x1")),
            (PVar("y"), PVar("y")),
            (PBool(True), PBool(True)),
            (PBool(False), PBool(False)),
            (PInt(42), PInt(42)),
        ):
            with self.subTest(predicate=predicate):
                self.assertEqual(subst_p(predicate, "x", "y"), expected)

    def test_nested_predicates_and_function_arguments(self):
        predicate = Conj(
            InterpOp(">", PVar("x"), PInt(0)),
            Disj(
                Neg(PVar("x")),
                UninterpFun("x", [PVar("x"), UninterpFun("g", [PVar("z")])]),
            ),
        )
        expected = Conj(
            InterpOp(">", PVar("y"), PInt(0)),
            Disj(
                Neg(PVar("y")),
                UninterpFun("x", [PVar("y"), UninterpFun("g", [PVar("z")])]),
            ),
        )
        self.assertEqual(subst_p(predicate, "x", "y"), expected)
        self.assertEqual(subst_p(predicate, "missing", "y"), predicate)
        self.assertEqual(subst_p(predicate, "x", "x"), predicate)
        self.assertEqual(predicate.p1.p1, PVar("x"))

    def test_binary_operands(self):
        for constructor in (Conj, Disj, lambda a, b: InterpOp("+", a, b)):
            predicate = constructor(PVar("x"), PVar("x"))
            with self.subTest(predicate=predicate):
                self.assertEqual(
                    subst_p(predicate, "x", "y"), constructor(PVar("y"), PVar("y"))
                )

    def test_nullary_function(self):
        self.assertEqual(subst_p(UninterpFun("x", []), "x", "y"), UninterpFun("x", []))

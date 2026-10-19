import unittest

from liquid_types.ast import TFun, TInt, TRefine
from liquid_types.logic import Conj, Disj, InterpOp, Neg, PBool, PInt, PVar, UninterpFun
from liquid_types.parse import parse_pred
from liquid_types.type import free_vars, subst_p, subst_t


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


class TypeSubstitutionTests(unittest.TestCase):
    def test_refinement_binder_cannot_capture_replacement(self):
        result = subst_t(TRefine(TInt(), "y", parse_pred("y > x")), "x", "y")
        self.assertNotEqual(result.binder, "y")
        self.assertEqual(result.predicate, InterpOp(">", PVar(result.binder), PVar("y")))
        self.assertEqual(free_vars(result), {"y"})

    def test_function_binder_is_renamed_only_in_its_scope(self):
        source = TFun(
            "y",
            TRefine(TInt(), "a", parse_pred("a > x")),
            TRefine(TInt(), "r", parse_pred("r = x + y")),
        )
        result = subst_t(source, "x", "y")
        self.assertNotEqual(result.binder, "y")
        self.assertEqual(result.arg, TRefine(TInt(), "a", parse_pred("a > y")))
        self.assertEqual(result.ret.predicate, InterpOp(
            "=", PVar("r"), InterpOp("+", PVar("y"), PVar(result.binder))
        ))
        self.assertEqual(free_vars(result), {"y"})

    def test_shadowing_still_stops_substitution(self):
        source = TFun(
            "x",
            TRefine(TInt(), "a", parse_pred("a > x")),
            TRefine(TInt(), "r", parse_pred("r > x")),
        )
        result = subst_t(source, "x", "y")
        self.assertEqual(result.binder, "x")
        self.assertEqual(result.arg, TRefine(TInt(), "a", parse_pred("a > y")))
        self.assertEqual(result.ret, source.ret)

    def test_nested_shadowing_is_preserved_during_renaming(self):
        source = TFun(
            "y", TRefine(TInt(), "v", PBool(True)),
            TFun(
                "y",
                TRefine(TInt(), "a", parse_pred("a = y")),
                TRefine(TInt(), "r", parse_pred("r = x + y")),
            ),
        )
        result = subst_t(source, "x", "y")
        self.assertEqual(result.ret.arg.predicate, InterpOp(
            "=", PVar("a"), PVar(result.binder)
        ))
        self.assertEqual(result.ret.ret.predicate, InterpOp(
            "=", PVar("r"), InterpOp("+", PVar("y"), PVar(result.ret.binder))
        ))
        self.assertEqual(free_vars(result), {"y"})

    def test_generated_names_already_present_are_preserved(self):
        predicate = InterpOp("=", PVar("y"), InterpOp("+", PVar("x"), PVar("%subst0")))
        result = subst_t(TRefine(TInt(), "y", predicate), "x", "y")
        self.assertNotIn(result.binder, {"y", "%subst0"})
        self.assertEqual(result.predicate, InterpOp(
            "=", PVar(result.binder), InterpOp("+", PVar("y"), PVar("%subst0"))
        ))

    def test_no_renaming_when_substitution_has_no_effect(self):
        source = TRefine(TInt(), "y", parse_pred("y > 0"))
        self.assertEqual(subst_t(source, "missing", "y"), source)
        self.assertEqual(subst_t(source, "y", "y"), source)

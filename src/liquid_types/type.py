from __future__ import annotations

from typing import assert_never

import z3

from liquid_types.ast import (
    Annot,
    App,
    Bop,
    Const,
    Exp,
    Fun,
    Let,
    TFun,
    TInt,
    TRefine,
    Type,
    Var,
)
from liquid_types.errors import TypeCheckError
from liquid_types.logic import (
    Conj,
    ConsConj,
    Constraint,
    Disj,
    Implication,
    InterpOp,
    Neg,
    PBool,
    PInt,
    Pred,
    PVar,
    UninterpFun,
    boolean,
    to_z3,
    valid,
)

type TyEnv = dict[str, Type]


def prim(v: int | str) -> Type:
    if isinstance(v, int):
        return TRefine(TInt(), "v", InterpOp("=", PVar("v"), PInt(v)))

    op = {"add": "+", "sub": "-", "mul": "*", "div": "/"}.get(v, v)
    if op in ("+", "-", "*", "/"):
        # Internal binders cannot collide with source identifiers.
        x, y, result = "%lhs", "%rhs", "%result"
        int_t = TRefine(TInt(), "v", PBool(True))
        nonzero_t = TRefine(TInt(), "v", InterpOp("!=", PVar("v"), PInt(0)))
        return TFun(
            x,
            int_t,
            TFun(
                y,
                nonzero_t if op == "/" else int_t,
                TRefine(
                    TInt(),
                    result,
                    InterpOp("=", PVar(result), InterpOp(op, PVar(x), PVar(y))),
                ),
            ),
        )
    raise NotImplementedError(f"Undefined primitive {v}")


def subst_p(p: Pred, old: str, new: str) -> Pred:
    # p[old := new]
    match p:
        case PVar(name):
            return PVar(new) if name == old else p
        case PBool() | PInt():
            return p
        case InterpOp(op, p1, p2):
            return InterpOp(op, subst_p(p1, old, new), subst_p(p2, old, new))
        case Conj(p1, p2):
            return Conj(subst_p(p1, old, new), subst_p(p2, old, new))
        case Disj(p1, p2):
            return Disj(subst_p(p1, old, new), subst_p(p2, old, new))
        case Neg(inner):
            return Neg(subst_p(inner, old, new))
        case UninterpFun(f, ps):
            return UninterpFun(f, [subst_p(arg, old, new) for arg in ps])
        case _:
            assert_never(p)


def free_vars(node: Type | Pred) -> set[str]:
    match node:
        case PVar(name):
            return {name}
        case PBool() | PInt():
            return set()
        case InterpOp(_, p1, p2) | Conj(p1, p2) | Disj(p1, p2):
            return free_vars(p1) | free_vars(p2)
        case Neg(p):
            return free_vars(p)
        case UninterpFun(_, ps):
            return set().union(*(free_vars(p) for p in ps))
        case TRefine(_, v, p):
            return free_vars(p) - {v}
        case TFun(x, s, t):
            return free_vars(s) | (free_vars(t) - {x})
        case _:
            assert_never(node)


def fresh_var(avoid: set[str]) -> str:
    i = 0
    while f"%subst{i}" in avoid:
        i += 1
    return f"%subst{i}"


def subst_t(t: Type, old: str, new: str) -> Type:
    # t[old := new]
    match t:
        case TRefine(b, v, _p) if v == old:
            # The refinement binder shadows old.
            # b{old: _p}[old := new] = b{old: _p}
            return t

        case TRefine(b, v, p):
            if v == new and old in free_vars(p):
                fresh = fresh_var(free_vars(p) | {old, new})
                p = subst_p(p, v, fresh)
                v = fresh
            # b{v: p}[old := new] = b{v: p[old := new]}
            return TRefine(b, v, subst_p(p, old, new))

        case TFun(x, s, t) if x == old:
            # The function binder shadows old only in the result type.
            # (old: s->t)[old := new] = old: s[old := new]->t
            return TFun(x, subst_t(s, old, new), t)

        case TFun(x, s, t):
            if x == new and old in free_vars(t):
                fresh = fresh_var(free_vars(t) | {old, new})
                t = subst_t(t, x, fresh)
                x = fresh
            # (x: s->t)[old := new] = x: s[old := new]->t[old := new]
            return TFun(x, subst_t(s, old, new), subst_t(t, old, new))

        case _:
            assert_never(t)


def impl_constraint(x: str, t: Type, c: Constraint) -> Constraint:
    """(x :: t) => c"""
    match t:
        case TRefine(b, v, p):
            return Implication(x, b, subst_p(p, v, x), c)
        case _:
            return c


def sub(t1: Type, t2: Type) -> Constraint:
    match t1, t2:
        case TRefine(b1, v1, p1), TRefine(b2, v2, p2) if b1 == b2:
            return Implication(v1, b1, p1, subst_p(p2, v2, v1))

        case TFun(x1, s1, t1), TFun(x2, s2, t2):
            ci = sub(s2, s1)
            co = sub(subst_t(t1, x1, x2), t2)
            return ConsConj(ci, impl_constraint(x2, s2, co))

        case _:
            raise TypeCheckError(f"Cannot subtype {t1} against {t2}")


def apply_t(t: Type, x: str, tyenv: TyEnv) -> tuple[Constraint, Type]:
    if not isinstance(t, TFun):
        raise TypeCheckError(f"{t} is not a function type")
    c = check(Var(x), t.arg, tyenv)
    return c, subst_t(t.ret, t.binder, x)


def synth(exp: Exp, tyenv: TyEnv | None = None) -> tuple[Constraint, Type]:
    if tyenv is None:
        tyenv = {}

    match exp:
        case Const(n):
            return PBool(True), prim(n)

        case Bop(op, x, y):
            c1, t1 = apply_t(prim(op), x, tyenv)
            c2, t2 = apply_t(t1, y, tyenv)
            return ConsConj(c1, c2), t2

        case Var(x):
            if x not in tyenv:
                raise TypeCheckError(f"Unbound variable {x}")
            return PBool(True), tyenv[x]

        case App(e, x):
            c_e, t = synth(e, tyenv)
            c_x, result = apply_t(t, x, tyenv)
            return ConsConj(c_e, c_x), result

        case Annot(e, t):
            return check(e, t, tyenv), t

        case Fun():
            raise TypeCheckError("Cannot infer the type of this function")

        case Let():
            raise TypeCheckError("Cannot infer the type of this let expression")


def well_formed(t: Type, tyenv: TyEnv | None = None) -> None:
    if tyenv is None:
        tyenv = {}

    match t:
        case TRefine(_, v, p):
            env = {
                x: z3.FreshInt(x) for x, s in tyenv.items() if isinstance(s, TRefine)
            }
            boolean(to_z3(p, {**env, v: z3.FreshInt(v)}))
        case TFun(x, s, t):
            well_formed(s, tyenv)
            well_formed(t, {**tyenv, x: s})
        case _:
            assert_never(t)


def check(exp: Exp, t: Type, tyenv: TyEnv | None = None) -> Constraint:
    if tyenv is None:
        tyenv = {}
    well_formed(t, tyenv)

    match exp:
        case Let(x, e1, e2):
            c1, t1 = synth(e1, tyenv)
            c2 = check(e2, t, {**tyenv, x: t1})
            return ConsConj(c1, impl_constraint(x, t1, c2))

        case Fun(x, body):
            if not isinstance(t, TFun):
                raise TypeCheckError(f"{t} is not a function type")
            result = subst_t(t.ret, t.binder, x)
            c = check(body, result, {**tyenv, x: t.arg})
            return impl_constraint(x, t.arg, c)

        case e:
            c, s = synth(e, tyenv)
            return ConsConj(c, sub(s, t))


def typecheck(exp: Exp, t: Type | None = None, tyenv: TyEnv | None = None) -> Type:
    if tyenv is None:
        tyenv = {}

    scope: TyEnv = {}
    for x, s in tyenv.items():
        well_formed(s, scope)
        scope[x] = s

    if t is None:
        c, t = synth(exp, tyenv)
    else:
        c = check(exp, t, tyenv)

    for x, s in reversed(list(tyenv.items())):
        c = impl_constraint(x, s, c)
    if not valid(c):
        raise TypeCheckError("Refinement constraint is not valid")
    return t

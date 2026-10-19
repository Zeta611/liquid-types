from __future__ import annotations

from typing import assert_never

from liquid_types.ast import (
    Annot,
    App,
    Bop,
    Const,
    Conj,
    Disj,
    Exp,
    Fun,
    Let,
    InterpOp,
    Neg,
    PBool,
    PInt,
    Pred,
    PVar,
    TFun,
    TInt,
    TRefine,
    Type,
    UninterpFun,
    Var,
)
from liquid_types.errors import TypeCheckError

type TyEnv = dict[str, Type]


def prim(v) -> Type:
    if isinstance(v, int):
        return TRefine(TInt(), "v", PBool(True))
    raise NotImplementedError()


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


def subst_t(t: Type, old: str, new: str) -> Type:
    # t[old := new]
    match t:
        case TRefine(b, v, _p) if v == old:
            # v is not free in _p
            # b{old: _p}[old := new] = b{old: _p}
            return t

        case TRefine(b, v, p):
            # v is free in p
            # b{v: p}[old := new] = b{v: p[old := new]}
            return TRefine(b, v, subst_p(p, old, new))

        case TFun(x, s, t) if x == old:
            # x is not free in p
            # (old: s->t)[old := new] = old: s[old := new]->t
            return TFun(x, subst_t(s, old, new), t)

        case TFun(x, s, t):
            # x is free in p
            # (x: s->t)[old := new] = x: s[old := new]->t[old := new]
            return TFun(x, subst_t(s, old, new), subst_t(t, old, new))

        case _:
            assert_never(t)


def synth(exp: Exp, tyenv: TyEnv | None = None) -> Type:
    if tyenv is None:
        tyenv = {}

    match exp:
        case Const(n):
            return prim(n)

        case Bop(op, e1, e2):
            t1 = synth(e1, tyenv)
            t2 = synth(e2, tyenv)
            match op:
                case "+":
                    if not (isinstance(t1, TRefine) and isinstance(t2, TRefine)):
                        raise TypeCheckError("Cannot add a function")
                    return TRefine(TInt(), "v", PBool(True))
                case "-":
                    if not (isinstance(t1, TRefine) and isinstance(t2, TRefine)):
                        raise TypeCheckError("Cannot subtract a function")
                    return TRefine(TInt(), "v", PBool(True))
                case "*":
                    if not (isinstance(t1, TRefine) and isinstance(t2, TRefine)):
                        raise TypeCheckError("Cannot multiply a function")
                    return TRefine(TInt(), "v", PBool(True))
                case "/":
                    if not (isinstance(t1, TRefine) and isinstance(t2, TRefine)):
                        raise TypeCheckError("Cannot divide a function")
                    return TRefine(TInt(), "v", PBool(True))
                case _:
                    raise NotImplementedError(f"Undefined operator {op}")

        case Var(x):
            if x not in tyenv:
                raise TypeCheckError(f"Unbound variable {x}")
            return tyenv[x]

        case App(e, x):
            t_fun = synth(e, tyenv)
            if not isinstance(t_fun, TFun):
                raise TypeCheckError(f"{t_fun} is not a function type")
            check(Var(x), t_fun.arg, tyenv)
            return t_fun.ret

        case Annot(e, t):
            check(e, t, tyenv)
            return t

        case Fun():
            raise TypeCheckError("Cannot infer the type of this function")

        case Let():
            raise TypeCheckError("Cannot infer the type of this let expression")


def is_base(t: Type) -> bool:
    return isinstance(t, TRefine)


def check(exp: Exp, t: Type, tyenv: TyEnv | None = None) -> None:
    if tyenv is None:
        tyenv = {}

    match exp:
        case Let(x, e1, e2):
            t1 = synth(e1, tyenv)
            check(e2, t, {**tyenv, x: t1})

        case Fun(x, body):
            if not isinstance(t, TFun):
                raise TypeCheckError(f"{t} is not a function type")
            check(body, t.ret, {**tyenv, x: t.arg})

        case e:
            s = synth(e, tyenv)
            if s != t:
                raise TypeCheckError(f"{s} is not {t}")

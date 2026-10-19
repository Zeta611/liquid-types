from __future__ import annotations

from stlc.ast import (
    Annot,
    App,
    Bop,
    Const,
    Exp,
    Fun,
    Let,
    TFun,
    TInt,
    Type,
    Var,
)
from stlc.errors import TypeCheckError

type TyEnv = dict[str, Type]


def prim(v: int | str) -> Type:
    if isinstance(v, int):
        return TInt()
    op = {"add": "+", "sub": "-", "mul": "*", "div": "/"}.get(v, v)
    if op in ("+", "-", "*", "/"):
        return TFun(TInt(), TFun(TInt(), TInt()))
    raise NotImplementedError(f"Undefined primitive {v}")


def apply_type(t: Type, x: str, tyenv: TyEnv) -> Type:
    if not isinstance(t, TFun):
        raise TypeCheckError(f"{t} is not a function type")
    check(Var(x), t.arg, tyenv)
    return t.ret


def synth(exp: Exp, tyenv: TyEnv | None = None) -> Type:
    if tyenv is None:
        tyenv = {}

    match exp:
        case Const(n):
            return prim(n)

        case Bop(op, x, y):
            return apply_type(apply_type(prim(op), x, tyenv), y, tyenv)

        case Var(x):
            if x not in tyenv:
                raise TypeCheckError(f"Unbound variable {x}")
            return tyenv[x]

        case App(e, x):
            return apply_type(synth(e, tyenv), x, tyenv)

        case Annot(e, t):
            check(e, t, tyenv)
            return t

        case Fun():
            raise TypeCheckError("Cannot infer the type of this function")

        case Let():
            raise TypeCheckError("Cannot infer the type of this let expression")


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

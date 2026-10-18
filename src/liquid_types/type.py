from __future__ import annotations

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
    Type,
    Var,
)
from liquid_types.errors import TypeCheckError

type TyEnv = dict[str, Type]


def prim(v) -> Type:
    if isinstance(v, int):
        return TInt()
    raise NotImplementedError()


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
                    if not (isinstance(t1, TInt) and isinstance(t2, TInt)):
                        raise TypeCheckError("Cannot add a function")
                    return TInt()
                case "-":
                    if not (isinstance(t1, TInt) and isinstance(t2, TInt)):
                        raise TypeCheckError("Cannot subtract a function")
                    return TInt()
                case "*":
                    if not (isinstance(t1, TInt) and isinstance(t2, TInt)):
                        raise TypeCheckError("Cannot multiply a function")
                    return TInt()
                case "/":
                    if not (isinstance(t1, TInt) and isinstance(t2, TInt)):
                        raise TypeCheckError("Cannot divide a function")
                    return TInt()
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

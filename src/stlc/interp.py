from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from stlc.ast import Annot, App, Bop, Const, Exp, Fun, Let, Var
from stlc.errors import RuntimeError


@dataclass(frozen=True)
class Closure:
    x: str
    body: Exp
    env: Env


type Value = int | Closure
type Env = dict[str, Value]


def interp(exp: Exp, env: Env | None = None) -> Value:
    """Evaluate an expression in an environment of variable bindings."""
    if env is None:
        env = {}

    match exp:
        case Const(n):
            return n

        case Bop(op, e1, e2):
            v1 = interp(e1, env)
            v2 = interp(e2, env)
            match op:
                case "+":
                    if not (isinstance(v1, int) and isinstance(v2, int)):
                        raise RuntimeError("Cannot add a function")
                    return v1 + v2
                case "-":
                    if not (isinstance(v1, int) and isinstance(v2, int)):
                        raise RuntimeError("Cannot subtract a function")
                    return v1 - v2
                case "*":
                    if not (isinstance(v1, int) and isinstance(v2, int)):
                        raise RuntimeError("Cannot multiply a function")
                    return v1 * v2
                case "/":
                    if not (isinstance(v1, int) and isinstance(v2, int)):
                        raise RuntimeError("Cannot divide a function")
                    if v2 == 0:
                        raise RuntimeError("Cannot divide by zero")
                    return v1 // v2
                case _:
                    raise RuntimeError(f"Undefined operator {op}")

        case Var(x):
            if x not in env:
                raise RuntimeError(f"Unbound variable {x}")
            return env[x]

        case Let(x, e1, e2):
            val = interp(e1, env)
            return interp(e2, {**env, x: val})

        case Fun(x, body):
            return Closure(x, body, env)

        case App(e, x):
            fun = interp(e, env)
            if not isinstance(fun, Closure):
                raise RuntimeError("Cannot apply a non-function")

            if x not in env:
                raise RuntimeError(f"Unbound variable {x}")
            return interp(fun.body, {**fun.env, fun.x: env[x]})

        case Annot(e, _):
            return interp(e, env)

        case _:
            assert_never(exp)

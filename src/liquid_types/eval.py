from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from liquid_types.ast import Annot, App, Const, Exp, Fun, Let, Var


@dataclass(frozen=True)
class Closure:
    x: str
    body: Exp
    env: Env


type Value = int | Closure
type Env = dict[str, Value]


def eval(exp: Exp, env: Env | None = None) -> Value:
    """Evaluate an expression in an environment of variable bindings."""
    if env is None:
        env = {}

    match exp:
        case Const(n):
            return n

        case Var(x):
            if x not in env:
                raise NameError(f"Unbound variable {x}")
            return env[x]

        case Let(x, e1, e2):
            val = eval(e1, env)
            return eval(e2, {**env, x: val})

        case Fun(x, body):
            return Closure(x, body, env)

        case App(e, x):
            fun = eval(e, env)
            if not isinstance(fun, Closure):
                raise TypeError("Cannot apply a non-function")

            if x not in env:
                raise NameError(f"Unbound variable {x}")
            return eval(fun.body, {**fun.env, fun.x: env[x]})

        case Annot(e, _):
            return eval(e, env)

        case _:
            assert_never(exp)


def main() -> None:
    exp = Let(
        "identity",
        Fun("x", Var("x")),
        Let("answer", Const(42), App(Var("identity"), "answer")),
    )
    print(eval(exp))  # 42


if __name__ == "__main__":
    main()

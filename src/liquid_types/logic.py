from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, assert_never

import z3
from lark.ast_utils import Ast as _Ast

from liquid_types.errors import TypeCheckError

if TYPE_CHECKING:
    from liquid_types.ast import TInt


@dataclass(frozen=True)
class PVar(_Ast):
    name: str


@dataclass(frozen=True)
class PBool(_Ast):
    value: bool


@dataclass(frozen=True)
class PInt(_Ast):
    value: int


@dataclass(frozen=True)
class InterpOp:
    op: str
    p1: Pred
    p2: Pred


@dataclass(frozen=True)
class Conj(_Ast):
    p1: Pred
    p2: Pred


@dataclass(frozen=True)
class Disj(_Ast):
    p1: Pred
    p2: Pred


@dataclass(frozen=True)
class Neg(_Ast):
    p: Pred


@dataclass(frozen=True)
class UninterpFun:
    f: str
    ps: list[Pred]


type Pred = PVar | PBool | PInt | InterpOp | Conj | Disj | Neg | UninterpFun


@dataclass(frozen=True)
class ConsConj:
    c1: Constraint
    c2: Constraint


@dataclass(frozen=True)
class Implication:
    r"""\forall x : b. p => c"""

    x: str
    b: TInt
    p: Pred
    c: Constraint


type Constraint = Pred | ConsConj | Implication

type LogicEnv = dict[str, Any]


def boolean(expr: Any) -> Any:
    if not isinstance(expr, z3.BoolRef):
        raise TypeCheckError("A refinement predicate must be Boolean")
    return expr


def to_z3(node: Constraint, env: LogicEnv | None = None) -> Any:
    if env is None:
        env = {}

    match node:
        case PVar(name):
            if name not in env:
                raise TypeCheckError(f"Unbound refinement variable {name}")
            return env[name]

        case PBool(value):
            return z3.BoolVal(value)

        case PInt(value):
            return z3.IntVal(value)

        case InterpOp(op, p1, p2):
            left, right = to_z3(p1, env), to_z3(p2, env)
            if op in ("=", "==", "!="):
                if left.sort() != right.sort():
                    raise TypeCheckError("Equality requires operands of the same sort")
                return left != right if op == "!=" else left == right
            if not (z3.is_int(left) and z3.is_int(right)):
                raise TypeCheckError(f"Operator {op} requires integer operands")
            match op:
                case "+":
                    return left + right
                case "-":
                    return left - right
                case "*":
                    return left * right
                case "/":
                    return z3.If(right < 0, (-left) / (-right), left / right)
                case "<":
                    return left < right
                case "<=":
                    return left <= right
                case ">":
                    return left > right
                case ">=":
                    return left >= right
                case _:
                    raise TypeCheckError(f"Undefined logical operator {op}")

        case Conj(p1, p2) | ConsConj(p1, p2):
            return z3.And(boolean(to_z3(p1, env)), boolean(to_z3(p2, env)))

        case Disj(p1, p2):
            return z3.Or(boolean(to_z3(p1, env)), boolean(to_z3(p2, env)))

        case Neg(p):
            return z3.Not(boolean(to_z3(p, env)))

        case Implication(x, _, p, c):
            binder = z3.FreshInt(x)
            scope = {**env, x: binder}
            return z3.ForAll(
                [binder],
                z3.Implies(boolean(to_z3(p, scope)), boolean(to_z3(c, scope))),
            )

        case UninterpFun(f, _):
            raise TypeCheckError(f"No logical signature declared for {f}")

        case _:
            assert_never(node)


def valid(c: Constraint, *, timeout_ms: int = 10_000) -> bool:
    solver = z3.Solver()
    solver.set(timeout=timeout_ms)
    solver.add(z3.Not(boolean(to_z3(c))))
    result = solver.check()
    if result == z3.unknown:
        raise TypeCheckError(
            f"Constraint validity is unknown: {solver.reason_unknown()}"
        )
    return result == z3.unsat

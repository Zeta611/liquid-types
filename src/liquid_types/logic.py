from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from lark.ast_utils import Ast as _Ast

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

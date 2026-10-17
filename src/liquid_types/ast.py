from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Const:
    n: int


@dataclass(frozen=True)
class Var:
    x: str


@dataclass(frozen=True)
class Let:
    x: str
    e1: Exp
    e2: Exp


@dataclass(frozen=True)
class Fun:
    x: str
    body: Exp


@dataclass(frozen=True)
class App:
    e: Exp
    x: str


@dataclass(frozen=True)
class Annot:
    e: Exp
    ty: str


type Exp = Const | Var | Let | Fun | App | Annot

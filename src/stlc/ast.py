from __future__ import annotations

from dataclasses import dataclass

from lark import ast_utils


class _Ast(ast_utils.Ast):
    pass


@dataclass(frozen=True)
class Const(_Ast):
    n: int


@dataclass(frozen=True)
class Bop(_Ast):
    op: str
    x: str
    y: str


@dataclass(frozen=True)
class Var(_Ast):
    x: str


@dataclass(frozen=True)
class Let(_Ast):
    x: str
    e1: Exp
    e2: Exp


@dataclass(frozen=True)
class Fun(_Ast):
    x: str
    body: Exp


@dataclass(frozen=True)
class App(_Ast):
    e: Exp
    x: str


@dataclass(frozen=True)
class Annot(_Ast):
    e: Exp
    t: Type


type Exp = Const | Bop | Var | Let | Fun | App | Annot


@dataclass(frozen=True)
class TInt:
    pass


@dataclass(frozen=True)
class TFun:
    arg: Type
    ret: Type


type Type = TInt | TFun

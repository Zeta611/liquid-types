from lark import Lark, Token, Transformer, ast_utils, v_args

from stlc import ast
from stlc.errors import ParseError

grammar = r"""
    ?exp: "val" VAR ":" typ ";"? "let" VAR "=" exp ";" exp -> signed_let
        | "let" VAR "=" exp ";" exp -> let
        | bop

    ?bop: VAR ADD_OP VAR -> binary_op
        | VAR MUL_OP VAR -> binary_op
        | postfix

    ?postfix: postfix "(" VAR ")" -> app
            | postfix ":" typ -> annot
            | atom

    ?atom: NUMBER -> const
         | "-" NUMBER -> negative_const
         | VAR -> var
         | "(" PARAM ")" "=>" "{" exp "}" -> fun
         | "(" exp ")"

    ?typ: VAR ":" type_atom "=>" typ -> named_fun_type
        | type_atom "=>" typ -> fun_type
        | type_atom

    ?type_atom: BASE -> int_type
              | "(" typ ")"

    BASE: "int"

    ADD_OP: "+" | "-"
    MUL_OP: "*" | "/"

    // Match a name followed by optional whitespace, ')' and '=>', without consuming them.
    // Priority 2 makes PARAM win over VAR.
    PARAM.2: VAR /(?=\s*\)\s*=>)/

    %import common.CNAME -> VAR
    %import common.INT -> NUMBER
    %import common.WS
    %ignore WS
"""

parser = Lark(grammar, start="exp", parser="lalr", strict=True)


class ToAst(Transformer):
    def NUMBER(self, token: Token) -> int:
        return int(token)

    def VAR(self, token: Token) -> str:
        return str(token)

    def PARAM(self, token: Token) -> str:
        return str(token)

    def ADD_OP(self, token: Token) -> str:
        return str(token)

    def MUL_OP(self, token: Token) -> str:
        return str(token)

    @v_args(inline=True)
    def negative_const(self, value: int) -> ast.Const:
        return ast.Const(-value)

    def BASE(self, token: Token) -> str:
        return str(token)

    @v_args(inline=True)
    def int_type(self, _base: str) -> ast.TInt:
        return ast.TInt()

    @v_args(inline=True)
    def fun_type(self, arg: ast.Type, ret: ast.Type) -> ast.TFun:
        return ast.TFun(arg, ret)

    @v_args(inline=True)
    def named_fun_type(self, _name: str, arg: ast.Type, ret: ast.Type) -> ast.TFun:
        # Parameter names carry no meaning in non-dependent STLC types.
        return ast.TFun(arg, ret)

    @v_args(inline=True)
    def signed_let(
        self, name: str, typ: ast.Type, bound_name: str, value: ast.Exp, body: ast.Exp
    ) -> ast.Let:
        if name != bound_name:
            raise ParseError(
                f"Signature for '{name}' must immediately precede 'let {name}', but found 'let {bound_name}'"
            )
        return ast.Let(name, ast.Annot(value, typ), body)

    @v_args(inline=True)
    def binary_op(self, left: str, op: str, right: str) -> ast.Bop:
        return ast.Bop(op, left, right)


# https://lark-parser.readthedocs.io/en/stable/classes.html#lark.ast_utils.create_transformer
# > For each class, we create a corresponding rule in the transformer, with a matching name.
# > CamelCase names will be converted into snake_case. Example: “CodeBlock” -> “code_block”.
transformer = ast_utils.create_transformer(ast, ToAst())


def parse(pgm: str) -> ast.Exp:
    return transformer.transform(parser.parse(pgm))

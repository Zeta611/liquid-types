from lark import Lark, Token, Transformer, ast_utils, v_args

from liquid_types import ast

grammar = """
    ?exp: "let" VAR "=" exp ";" exp -> let
        | bop

    ?bop: bop OP postfix -> binary_op
        | postfix

    ?postfix: postfix "(" VAR ")" -> app
            | postfix ":" typ -> annot
            | atom

    ?atom: NUMBER -> const
         | VAR -> var
         | "(" VAR ")" "=>" "{" exp "}" -> fun

    ?typ: BASE

    BASE: "int"

    OP: "+" | "-" | "*" | "/"
    VAR: LETTER+

    %import common.LETTER
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

    def OP(self, token: Token) -> str:
        return str(token)

    def BASE(self, token: Token) -> str:
        return str(token)

    @v_args(inline=True)
    def binary_op(self, left: ast.Exp, op: str, right: ast.Exp) -> ast.Bop:
        return ast.Bop(op, left, right)


# https://lark-parser.readthedocs.io/en/stable/classes.html#lark.ast_utils.create_transformer
# > For each class, we create a corresponding rule in the transformer, with a matching name.
# > CamelCase names will be converted into snake_case. Example: “CodeBlock” -> “code_block”.
transformer = ast_utils.create_transformer(ast, ToAst())


def parse(pgm: str) -> ast.Exp:
    return transformer.transform(parser.parse(pgm))


def main() -> None:
    from liquid_types.interp import interp

    exp = parse("""
    let inc = (x) => {
      let one = 1;
      x + one
    };
    let incf = (x) => {
      let tmp = (f) => {
        f(x) + 1
      };
      tmp(inc)
    };
    let arg = 1;
    incf(arg)
    """)
    print(interp(exp))  # 3


if __name__ == "__main__":
    main()

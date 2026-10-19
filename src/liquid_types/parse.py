from itertools import count

from lark import Lark, Token, Transformer, ast_utils, v_args

from liquid_types import ast, logic
from liquid_types.errors import ParseError

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

    ?type_atom: BASE "[" VAR "|" pred "]" -> refined_int
              | BASE -> int_type
              | "(" typ ")"

    ?pred: pred_or

    ?pred_or: pred_or "||" pred_and -> disj
            | pred_and

    ?pred_and: pred_and "&&" pred_not -> conj
             | pred_not

    ?pred_not: "!" pred_not -> neg
             | pred_cmp

    ?pred_cmp: pred_sum CMP_OP pred_sum -> pred_binary
             | pred_sum

    ?pred_sum: pred_sum ADD_OP pred_product -> pred_binary
             | pred_product

    ?pred_product: pred_product MUL_OP pred_atom -> pred_binary
                 | pred_atom

    ?pred_atom: NUMBER -> p_int
              | "-" NUMBER -> negative_pred_int
              | "true" -> pred_true
              | "false" -> pred_false
              | VAR "(" [pred ("," pred)*] ")" -> pred_call
              | VAR -> p_var
              | "(" pred ")"

    BASE: "int"

    ADD_OP: "+" | "-"
    MUL_OP: "*" | "/"
    CMP_OP: "=" | "==" | "!=" | "<" | "<=" | ">" | ">="

    // Match a name followed by optional whitespace, ')' and '=>', without consuming them.
    // Priority 2 makes PARAM win over VAR.
    PARAM.2: VAR /(?=\s*\)\s*=>)/

    %import common.CNAME -> VAR
    %import common.INT -> NUMBER
    %import common.WS
    %ignore WS
"""

parser = Lark(
    grammar, start=["exp", "pred"], parser="lalr", strict=True, maybe_placeholders=False
)


class ToAst(Transformer):
    def __init__(self):
        super().__init__()
        self.binders = count()

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

    def CMP_OP(self, token: Token) -> str:
        return str(token)

    @v_args(inline=True)
    def negative_const(self, value: int) -> ast.Const:
        return ast.Const(-value)

    def BASE(self, token: Token) -> str:
        return str(token)

    @v_args(inline=True)
    def int_type(self, _base: str) -> ast.TRefine:
        return ast.TRefine(ast.TInt(), "v", logic.PBool(True))

    @v_args(inline=True)
    def refined_int(self, _base: str, binder: str, predicate: logic.Pred) -> ast.TRefine:
        return ast.TRefine(ast.TInt(), binder, predicate)

    @v_args(inline=True)
    def negative_pred_int(self, value: int) -> logic.PInt:
        return logic.PInt(-value)

    @v_args(inline=True)
    def pred_true(self) -> logic.PBool:
        return logic.PBool(True)

    @v_args(inline=True)
    def pred_false(self) -> logic.PBool:
        return logic.PBool(False)

    @v_args(inline=True)
    def pred_binary(self, left: logic.Pred, op: str, right: logic.Pred) -> logic.InterpOp:
        return logic.InterpOp(op, left, right)

    @v_args(inline=True)
    def pred_call(self, name: str, *args: logic.Pred) -> logic.UninterpFun:
        return logic.UninterpFun(name, list(args))

    @v_args(inline=True)
    def fun_type(self, arg: ast.Type, ret: ast.Type) -> ast.TFun:
        # '%' cannot occur in source identifiers.
        return ast.TFun(f"%arg{next(self.binders)}", arg, ret)

    @v_args(inline=True)
    def named_fun_type(self, name: str, arg: ast.Type, ret: ast.Type) -> ast.TFun:
        return ast.TFun(name, arg, ret)

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
def parse(pgm: str) -> ast.Exp:
    transformer = ast_utils.create_transformer(logic, ToAst())
    transformer = ast_utils.create_transformer(ast, transformer)
    return transformer.transform(parser.parse(pgm, start="exp"))


def parse_pred(source: str) -> logic.Pred:
    transformer = ast_utils.create_transformer(logic, ToAst())
    transformer = ast_utils.create_transformer(ast, transformer)
    return transformer.transform(parser.parse(source, start="pred"))

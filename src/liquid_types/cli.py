import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from lark.exceptions import UnexpectedInput, VisitError

from liquid_types.errors import LanguageError
from liquid_types.interp import Closure, interp
from liquid_types.parse import parse
from liquid_types.type import typecheck


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check or run a Liquid Types source file."
    )
    modes = parser.add_subparsers(dest="mode", required=True)
    for mode, help_text in (
        ("check", "typecheck a source file"),
        ("run", "evaluate a source file"),
    ):
        command = modes.add_parser(mode, help=help_text)
        command.add_argument("file", type=Path, help="source file")
    args = parser.parse_args(argv)

    try:
        source = args.file.read_text(encoding="utf-8")
        exp = parse(source)

        if args.mode == "run":
            value = interp(exp)
            print("<function>" if isinstance(value, Closure) else value)
        else:
            typecheck(exp)
            print(f"{args.file}: type checks")
    except VisitError as error:
        if not isinstance(error.orig_exc, LanguageError):
            raise
        print(f"{args.file}: {error.orig_exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError, UnexpectedInput, LanguageError) as error:
        print(f"{args.file}: {error}", file=sys.stderr)
        return 1

    return 0

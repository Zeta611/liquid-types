class LanguageError(Exception):
    """Base language error"""


class TypeCheckError(LanguageError):
    """Static type check error"""


class ParseError(LanguageError):
    """Invalid source syntax or declaration"""


class RuntimeError(LanguageError):
    """Runtime evaluation error"""

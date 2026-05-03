import re
from typing import Callable

Pattern = tuple[re.Pattern, str]
Token = str | tuple[str, tuple[str, ...]]


def tokenize(text: str, patterns: list[Pattern]) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    n = len(text)
    while pos < n:
        best_start = n
        best_end = n
        best_kind: str | None = None
        best_groups: tuple[str, ...] = ()
        for regex, kind in patterns:
            m = regex.search(text, pos)
            if m and m.start() < best_start:
                best_start = m.start()
                best_end = m.end()
                best_kind = kind
                best_groups = tuple(g if g is not None else "" for g in m.groups())
        if best_kind is None:
            tokens.append(text[pos:])
            break
        if best_start > pos:
            tokens.append(text[pos:best_start])
        tokens.append((best_kind, best_groups))
        pos = best_end
    return tokens


Renderer = Callable[[tuple[str, ...], Callable[[str], str]], str]
LiteralRenderer = Callable[[str], str]


def render(
    tokens: list[Token],
    renderers: dict[str, Renderer],
    literal: LiteralRenderer,
    recur: Callable[[str], str],
) -> str:
    out: list[str] = []
    for tok in tokens:
        if isinstance(tok, str):
            out.append(literal(tok))
        else:
            kind, groups = tok
            fn = renderers.get(kind)
            if fn is None:
                out.append(literal("".join(groups)))
            else:
                out.append(fn(groups, recur))
    return "".join(out)

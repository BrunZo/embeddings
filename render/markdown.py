import re
from dataclasses import dataclass, field
from html import escape

from . import patterns as pat

INLINE_PATTERNS: list[pat.Pattern] = [
    (re.compile(r"\*\*\*(.+?)\*\*\*"), "bolditalic"),
    (re.compile(r"___(.+?)___"), "bolditalic"),
    (re.compile(r"\*\*(.+?)\*\*"), "bold"),
    (re.compile(r"__(.+?)__"), "bold"),
    (re.compile(r"\*(?!\s)(.+?)(?<!\s)\*"), "italic"),
    (re.compile(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)"), "italic"),
    (re.compile(r"~~(.+?)~~"), "strike"),
    (re.compile(r"==(.+?)=="), "highlight"),
    (re.compile(r"`([^`]+)`"), "code"),
    (re.compile(r"!\[([^\]]*)\]\(([^)]+)\)"), "image"),
    (re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), "link"),
]


@dataclass
class Block:
    kind: str
    text: str = ""
    depth: int = 0
    ordered: bool = False


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_HR_RE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
_FENCE_RE = re.compile(r"^\s*```")
_LI_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.*)$")
_BQ_RE = re.compile(r"^\s*>\s?(.*)$")


def parse_blocks(text: str) -> list[Block]:
    lines = text.splitlines()
    blocks: list[Block] = []
    i = 0
    para: list[str] = []

    def flush_para() -> None:
        if para:
            blocks.append(Block("p", " ".join(s.strip() for s in para).strip()))
            para.clear()

    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if _FENCE_RE.match(line):
            flush_para()
            buf: list[str] = []
            i += 1
            while i < n and not _FENCE_RE.match(lines[i]):
                buf.append(lines[i])
                i += 1
            if i < n:
                i += 1
            blocks.append(Block("code", "\n".join(buf)))
            continue

        if not stripped:
            flush_para()
            i += 1
            continue

        m = _HEADING_RE.match(line)
        if m:
            flush_para()
            level = len(m.group(1))
            blocks.append(Block(f"h{level}", m.group(2).strip()))
            i += 1
            continue

        if _HR_RE.match(line):
            flush_para()
            blocks.append(Block("hr"))
            i += 1
            continue

        bq = _BQ_RE.match(line)
        if bq:
            flush_para()
            buf = [bq.group(1)]
            i += 1
            while i < n:
                m2 = _BQ_RE.match(lines[i])
                if not m2:
                    break
                buf.append(m2.group(1))
                i += 1
            content = " ".join(s.strip() for s in buf if s.strip())
            blocks.append(Block("blockquote", content))
            continue

        m = _LI_RE.match(line)
        if m:
            flush_para()
            indent = len(m.group(1).expandtabs(4))
            marker = m.group(2)
            content = m.group(3)
            depth = indent // 2
            ordered = marker[0].isdigit()
            blocks.append(Block("li", content.strip(), depth=depth, ordered=ordered))
            i += 1
            continue

        para.append(line)
        i += 1

    flush_para()
    return blocks


def _literal_html(s: str) -> str:
    return escape(s)


def _literal_text(s: str) -> str:
    return s


def _h_bold(g, recur):
    return f"<strong>{recur(g[0])}</strong>"


def _h_italic(g, recur):
    return f"<em>{recur(g[0])}</em>"


def _h_bolditalic(g, recur):
    return f"<strong><em>{recur(g[0])}</em></strong>"


def _h_strike(g, recur):
    return f"<del>{recur(g[0])}</del>"


def _h_highlight(g, recur):
    return f"<mark>{recur(g[0])}</mark>"


def _h_code(g, recur):
    return f"<code>{escape(g[0])}</code>"


def _h_link(g, recur):
    text, url = g
    return f'<a href="{escape(url, quote=True)}">{recur(text)}</a>'


def _h_image(g, recur):
    alt, url = g
    return f'<img alt="{escape(alt, quote=True)}" src="{escape(url, quote=True)}">'


HTML_INLINE: dict[str, pat.Renderer] = {
    "bold": _h_bold,
    "italic": _h_italic,
    "bolditalic": _h_bolditalic,
    "strike": _h_strike,
    "highlight": _h_highlight,
    "code": _h_code,
    "link": _h_link,
    "image": _h_image,
}


def _passthrough_first(g, recur):
    return recur(g[0]) if g else ""


def _text_code(g, recur):
    return g[0]


def _text_link(g, recur):
    return recur(g[0])


def _text_image(g, recur):
    return g[0]


TEXT_INLINE: dict[str, pat.Renderer] = {
    "bold": _passthrough_first,
    "italic": _passthrough_first,
    "bolditalic": _passthrough_first,
    "strike": _passthrough_first,
    "highlight": _passthrough_first,
    "code": _text_code,
    "link": _text_link,
    "image": _text_image,
}


def _make_recur(patterns_list, renderers, literal):
    def recur(s: str) -> str:
        tokens = pat.tokenize(s, patterns_list)
        return pat.render(tokens, renderers, literal, recur)
    return recur


def render_inline_html(text: str, patterns_list=None, renderers=None) -> str:
    patterns_list = patterns_list if patterns_list is not None else INLINE_PATTERNS
    renderers = renderers if renderers is not None else HTML_INLINE
    return _make_recur(patterns_list, renderers, _literal_html)(text)


def render_inline_text(text: str, patterns_list=None, renderers=None) -> str:
    patterns_list = patterns_list if patterns_list is not None else INLINE_PATTERNS
    renderers = renderers if renderers is not None else TEXT_INLINE
    return _make_recur(patterns_list, renderers, _literal_text)(text)


EMBEDDABLE = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote"}

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=\S)")


def split_paragraphs(blocks: list[Block]) -> list[Block]:
    out: list[Block] = []
    for b in blocks:
        if b.kind != "p":
            out.append(b)
            continue
        parts = [s.strip() for s in _SENTENCE_SPLIT.split(b.text) if s.strip()]
        if len(parts) <= 1:
            out.append(b)
            continue
        for part in parts:
            out.append(Block("p", part))
    return out


def to_html(blocks: list[Block], inline_patterns=None, inline_renderers=None) -> str:
    out: list[str] = []
    embed_idx = 0
    i = 0
    n = len(blocks)

    def inline(text: str) -> str:
        return render_inline_html(text, inline_patterns, inline_renderers)

    while i < n:
        b = blocks[i]

        if b.kind == "li":
            stack: list[tuple] = []  # ('list', depth, tag) or ('li', depth)

            def close(entry):
                if entry[0] == "li":
                    out.append("</li>")
                else:
                    out.append(f"</{entry[2]}>")

            while i < n and blocks[i].kind == "li":
                li = blocks[i]
                tag = "ol" if li.ordered else "ul"

                while stack and stack[-1][1] > li.depth:
                    close(stack.pop())

                if stack and stack[-1][0] == "li" and stack[-1][1] == li.depth:
                    close(stack.pop())

                if (
                    stack
                    and stack[-1][0] == "list"
                    and stack[-1][1] == li.depth
                    and stack[-1][2] != tag
                ):
                    close(stack.pop())

                if not stack or stack[-1][1] < li.depth or stack[-1][0] != "list":
                    out.append(f"<{tag}>")
                    stack.append(("list", li.depth, tag))

                out.append(f'<li data-index="{embed_idx}">{inline(li.text)}')
                stack.append(("li", li.depth))
                embed_idx += 1
                i += 1

            while stack:
                close(stack.pop())
            continue

        if b.kind == "hr":
            out.append("<hr>")
            i += 1
            continue

        if b.kind == "code":
            out.append(f"<pre><code>{escape(b.text)}</code></pre>")
            i += 1
            continue

        if b.kind in EMBEDDABLE:
            out.append(f'<{b.kind} data-index="{embed_idx}">{inline(b.text)}</{b.kind}>')
            embed_idx += 1
            i += 1
            continue

        i += 1

    return "\n".join(out)


def to_text(blocks: list[Block], inline_patterns=None, inline_renderers=None) -> list[str]:
    texts: list[str] = []
    for b in blocks:
        if b.kind not in EMBEDDABLE:
            continue
        texts.append(render_inline_text(b.text, inline_patterns, inline_renderers))
    return texts

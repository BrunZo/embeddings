import re
from html import escape
from typing import Callable

import yaml

from . import markdown

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]")
TAG_RE = re.compile(r"(?<![\w/])#([A-Za-z][\w/-]*)")
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


OBSIDIAN_INLINE_PATTERNS = [
    (WIKILINK_RE, "wikilink"),
    (TAG_RE, "tag"),
] + markdown.INLINE_PATTERNS


LinkResolver = Callable[[str], str | None]


def split_frontmatter(text: str) -> tuple[dict, str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}, text
    if not isinstance(data, dict):
        return {}, text
    return data, text[m.end():]


def parse(text: str) -> tuple[dict, list[markdown.Block]]:
    fm, body = split_frontmatter(text)
    return fm, markdown.parse_blocks(body)


def render_frontmatter_html(fm: dict) -> str:
    if not fm:
        return ""
    parts = ['<dl class="frontmatter">']
    for key, value in fm.items():
        parts.append(f"<dt>{escape(str(key))}</dt>")
        if isinstance(value, list):
            if key == "tags":
                items = " ".join(
                    f'<span class="tag">#{escape(str(v))}</span>' for v in value
                )
            elif key == "aliases":
                items = " ".join(
                    f'<span class="alias">{escape(str(v))}</span>' for v in value
                )
            else:
                items = escape(", ".join(str(v) for v in value))
            parts.append(f"<dd>{items}</dd>")
        else:
            parts.append(f"<dd>{escape(str(value))}</dd>")
    parts.append("</dl>")
    return "\n".join(parts)


def _html_renderers(link_resolver: LinkResolver) -> dict:
    renderers = dict(markdown.HTML_INLINE)

    def wikilink(g, recur):
        target, alias = g
        text = alias if alias else target
        resolved = link_resolver(target)
        if resolved:
            return f'<a href="/visualize/{escape(resolved, quote=True)}">{escape(text)}</a>'
        return f'<span class="wikilink-broken">{escape(text)}</span>'

    def tag(g, recur):
        return f'<span class="tag">#{escape(g[0])}</span>'

    renderers["wikilink"] = wikilink
    renderers["tag"] = tag
    return renderers


def _text_renderers() -> dict:
    renderers = dict(markdown.TEXT_INLINE)

    def wikilink(g, recur):
        target, alias = g
        return alias if alias else target

    def tag(g, recur):
        return g[0]

    renderers["wikilink"] = wikilink
    renderers["tag"] = tag
    return renderers


def to_html(fm: dict, blocks: list[markdown.Block], link_resolver: LinkResolver) -> str:
    body_html = markdown.to_html(
        blocks,
        inline_patterns=OBSIDIAN_INLINE_PATTERNS,
        inline_renderers=_html_renderers(link_resolver),
    )
    fm_html = render_frontmatter_html(fm)
    if fm_html:
        return fm_html + "\n" + body_html
    return body_html


def to_text(blocks: list[markdown.Block]) -> list[str]:
    return markdown.to_text(
        blocks,
        inline_patterns=OBSIDIAN_INLINE_PATTERNS,
        inline_renderers=_text_renderers(),
    )

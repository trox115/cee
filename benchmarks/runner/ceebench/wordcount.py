from __future__ import annotations

import re
from dataclasses import asdict, dataclass

RULESET = "ceebench-wc/1"

_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?")


@dataclass(frozen=True)
class Options:
    fenced_code: str = "exclude"
    images: str = "exclude"

    def __post_init__(self) -> None:
        if self.fenced_code not in ("exclude", "include"):
            raise ValueError("fenced_code must be 'exclude' or 'include'")
        if self.images not in ("exclude", "include"):
            raise ValueError("images must be 'exclude' or 'include'")


@dataclass(frozen=True)
class Count:
    words: int
    fenced_blocks: int
    fenced_words: int
    images: int
    image_tokens: int


def _strip_fences(text: str) -> tuple[str, int, int]:
    kept: list[str] = []
    removed: list[str] = []
    blocks = 0
    fence: str | None = None
    for line in text.split("\n"):
        if fence is None:
            m = _FENCE_OPEN.match(line)
            if m:
                fence = m.group(1)
                blocks += 1
                removed.append(line)
                continue
            kept.append(line)
        else:
            removed.append(line)
            stripped = line.strip()
            if stripped and set(stripped) == {fence[0]} and len(stripped) >= len(fence):
                fence = None
    return "\n".join(kept), blocks, len(" ".join(removed).split())


def count(text: str, options: Options = Options()) -> Count:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = fenced_words = 0
    if options.fenced_code == "exclude":
        text, blocks, fenced_words = _strip_fences(text)
    images = image_tokens = 0
    if options.images == "exclude":
        matches = list(_IMAGE.finditer(text))
        images = len(matches)
        image_tokens = sum(len(m.group(0).split()) for m in matches)
        text = _IMAGE.sub(" ", text)
    return Count(len(text.split()), blocks, fenced_words, images, image_tokens)


def describe(options: Options = Options()) -> dict:
    return {
        "ruleset": RULESET,
        "options": asdict(options),
        "rules": [
            "Normalize CRLF and CR line endings to LF.",
            "fenced_code=exclude: remove every fenced block (``` or ~~~, 3+ characters, up to 3 leading spaces) including fence lines; an unclosed fence runs to the end of the text.",
            "images=exclude: remove Markdown images ![alt](url) with an optional trailing {attributes} block.",
            "Count tokens with Python str.split(): runs of Unicode whitespace separate tokens.",
            "Inline code, labels, titles, Markdown emphasis markers and URLs are counted as written.",
        ],
    }

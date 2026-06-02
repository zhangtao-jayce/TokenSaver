"""Small local token estimation helpers.

This deliberately avoids model-specific tokenizers in the first open-source
cut. It gives a stable local estimate without network or native dependencies.
"""

from __future__ import annotations

import re

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_WORD_RE = re.compile(r"[A-Za-z0-9_]+|[^\sA-Za-z0-9_]")


def estimate_tokens(text: str | None) -> int:
    """Estimate tokens for mixed English/CJK content.

    Approximation:
    - CJK characters are close to 1 token each for rough budgeting.
    - Latin words/punctuation are estimated from character count.
    """
    if not text:
        return 0

    cjk_count = len(_CJK_RE.findall(text))
    non_cjk = _CJK_RE.sub(" ", text)
    pieces = _WORD_RE.findall(non_cjk)
    latin_chars = sum(len(piece) for piece in pieces)

    # 4 chars/token is a common rough English estimate. Punctuation-heavy text
    # gets a small floor from piece count.
    latin_tokens = max((latin_chars + 3) // 4, len(pieces) // 3)
    return max(1, cjk_count + latin_tokens)


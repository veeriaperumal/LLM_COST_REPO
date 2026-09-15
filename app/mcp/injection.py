# ---------------------------------------------------------------------------
# injection.py — Prompt-injection detection for MCP tool arguments
# ---------------------------------------------------------------------------
# Scans string arguments for common injection patterns before they reach
# the LLM.  Returns True when a suspicious pattern is detected.
# ---------------------------------------------------------------------------

from __future__ import annotations

import re
from typing import Sequence

# Default patterns that indicate prompt-injection attempts.  These are
# checked case-insensitively against every string argument.
_DEFAULT_PATTERNS: list[str] = [
    r"ignore\s+(all\s+)?previous\s+(instructions?|prompts?)",
    r"ignore\s+(all\s+)?above\s+(instructions?|prompts?)",
    r"disregard\s+(all\s+)?(previous|prior|above|earlier)",
    r"you\s+are\s+now\s+",
    r"act\s+as\s+(if\s+)?(you\s+are\s+)?a\s+",
    r"pretend\s+you\s+are\s+",
    r"jailbreak",
    r"</?s>",
    r"\[system\]",
    r"\[assistant\]",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"system\s*:\s*",
    r"assistant\s*:\s*",
    r"override\s+(all\s+)?(safety|instructions?|rules?)",
    r"bypass\s+(all\s+)?(security|filters?|checks?)",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions?)",
    r"what\s+is\s+your\s+(system\s+prompt|instructions?)",
]


def _compile_patterns(extra: Sequence[str] | None = None) -> list[re.Pattern[str]]:
    """Compile default + extra patterns into regex objects."""
    patterns = list(_DEFAULT_PATTERNS)
    if extra:
        patterns.extend(extra)
    return [re.compile(p, re.IGNORECASE) for p in patterns]


# Lazily compiled on first call to keep import fast.
_compiled: list[re.Pattern[str]] | None = None


def check_injection(
    text: str,
    extra_patterns: Sequence[str] | None = None,
) -> bool:
    """Return True if *text* matches a known injection pattern.

    Parameters
    ----------
    text:
        The string argument to scan.
    extra_patterns:
        Optional additional regex patterns (e.g. from Settings).
    """
    global _compiled
    if _compiled is None or extra_patterns:
        _compiled = _compile_patterns(extra_patterns)

    for pattern in _compiled:
        if pattern.search(text):
            return True
    return False

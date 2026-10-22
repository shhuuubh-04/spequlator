"""Text preprocessing utilities for Spequlator."""

import re


def normalize_text(text: str) -> str:
    """Normalize whitespace without removing meaningful code syntax."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    return re.sub(r"\s+", " ", text).strip()
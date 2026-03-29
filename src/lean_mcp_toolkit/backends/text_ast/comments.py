"""Comment and string masking helpers."""

from __future__ import annotations


def mask_comments_and_strings(text: str) -> str:
    """Replace comments/strings with spaces while preserving newlines and length."""

    chars = list(text)
    i = 0
    n = len(chars)
    block_depth = 0
    in_string = False
    escaped = False
    while i < n:
        ch = chars[i]

        if in_string:
            if ch != "\n":
                chars[i] = " "
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if block_depth > 0:
            if i + 1 < n and text[i : i + 2] == "/-":
                chars[i] = " "
                chars[i + 1] = " "
                block_depth += 1
                i += 2
                continue
            if i + 1 < n and text[i : i + 2] == "-/":
                chars[i] = " "
                chars[i + 1] = " "
                block_depth -= 1
                i += 2
                continue
            if ch != "\n":
                chars[i] = " "
            i += 1
            continue

        if i + 1 < n and text[i : i + 2] == "--":
            while i < n and chars[i] != "\n":
                chars[i] = " "
                i += 1
            continue

        if i + 1 < n and text[i : i + 2] == "/-":
            chars[i] = " "
            chars[i + 1] = " "
            block_depth = 1
            i += 2
            continue

        if ch == '"':
            chars[i] = " "
            in_string = True
            escaped = False
            i += 1
            continue

        i += 1

    return "".join(chars)


__all__ = ["mask_comments_and_strings"]

import re
from .models import Block, Token


def tokenize(raw: str):
    """Keep ordered fields, block contexts and exact source spans."""
    blocks = []
    current = None
    for match in re.finditer(r"([^@]*)@", raw):
        part = match.group(1)
        if match.start() == 0:
            continue
        offset = match.start()
        if part and part[0].isupper():
            current = Block(part[0])
            blocks.append(current)
            part = part[1:]
            offset += 1
        if current is not None and part:
            key, value = ("", part) if current.kind == "C" else (part[0], part[1:])
            current.tokens.append(Token(current.kind, key, value, offset, match.end() - 1))
    return blocks

import re

CHECKSUM = re.compile(r"@C(\d+)@$")


def checksum(prefix: str) -> int:
    """BVBS 3.1 p.12: ASCII sum through and including C."""
    return 96 - sum(prefix.encode("ascii")) % 32


def inspect(raw: str):
    match = CHECKSUM.search(raw)
    if not match:
        return None, None
    try:
        expected = checksum(raw[:match.start(1)])
    except UnicodeEncodeError:
        expected = None
    return int(match.group(1)), expected


def repair(raw: str) -> str:
    match = CHECKSUM.search(raw)
    if not match:
        raise ValueError("Ein abschließender Prüfsummenblock @Czahl@ ist erforderlich.")
    value = checksum(raw[:match.start(1)])
    return raw[:match.start(1)] + str(value) + raw[match.end(1):]

from difflib import SequenceMatcher
from collections import Counter
from .parser import source_lines


def merge_line_endings(previous, edited):
    """Restore untouched mixed endings after browser text-area normalization."""
    old = source_lines(previous)
    new = source_lines(edited)
    old_bodies, new_bodies = [l.raw for l in old], [l.raw for l in new]
    counts = Counter(l.ending for l in old if l.ending)
    default = counts.most_common(1)[0][0] if counts else '\r\n'
    endings = [l.ending for l in new]
    for tag,a,b,c,d in SequenceMatcher(a=old_bodies,b=new_bodies,autojunk=False).get_opcodes():
        if tag == 'equal':
            for oi,ni in zip(range(a,b),range(c,d)):
                endings[ni] = old[oi].ending
        elif tag == 'replace' and b-a == d-c:
            for oi,ni in zip(range(a,b),range(c,d)):
                endings[ni] = old[oi].ending
        else:
            for ni in range(c,d):
                endings[ni] = default if new[ni].ending else ''
    # Insertion after a formerly final line requires a separator for that line.
    for i in range(len(endings)-1):
        if not endings[i]:
            endings[i] = default
    return ''.join(l.raw+end for l,end in zip(new,endings))


def encode(text, encoding, bom=b''):
    return bom + text.encode(encoding, errors='strict')

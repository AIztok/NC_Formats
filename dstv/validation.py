from .parser import parse


def export_reasons(part):
    if part.export_ok:
        return []
    reasons = [f'{d.block}, Zeile {d.line}: {d.message}' for d in part.diagnostics]
    if not part.faces and not reasons:
        reasons.append('Keine vollständig unterstützte Geometrie.')
    return reasons


def checked_bytes(document):
    # Validate the actual serialized export, including the chosen encoding.
    data = document.bytes()
    decoded = data[len(document.bom):].decode(document.encoding, errors='strict')
    part = parse(decoded, document.name)
    reasons = export_reasons(part) + document.dependency_reasons()
    if document.bom or not decoded.isascii():
        reasons.append('Geprüfter Standardexport ist auf ASCII ohne BOM beschränkt.')
    if reasons:
        raise ValueError('\n'.join(reasons))
    return data

from decimal import Decimal


def export_reasons(records, text):
    """Conservative, explicitly limited straight-bar consistency check."""
    reasons = []
    if not records:
        return ["Datei enthält keine Datensätze."]
    if any(line and not line.endswith("\r\n") for line in text.splitlines(keepends=True)):
        reasons.append("BVBS-Export benötigt CRLF nach jedem Datensatz.")
    for r in records:
        prefix = f"Datensatz {r.id + 1}: "
        if not r.syntax_ok or r.points is None:
            reasons.append(prefix + "Syntax oder Geometrie nicht vollständig unterstützt.")
            continue
        if [b.kind for b in r.blocks] != ["H", "G", "C"] or any(d.code in {"extension", "required", "record_length"} for d in r.diagnostics):
            reasons.append(prefix + "Zusatzdaten sind fachlich nicht geprüft.")
        if r.expected_checksum is None:
            reasons.append(prefix + "ASCII-Prüfsumme nicht bestätigt.")
        if len(r.points) != 2:
            reasons.append(prefix + "Gebogene Form: Gesamtlänge/Gewicht nicht fachlich geprüft und möglicherweise veraltet.")
            continue
        length = r.elements[0].length
        if r.header.get("l") != length:
            reasons.append(prefix + "Headerlänge stimmt nicht mit dem geraden Schenkel überein.")
        # Nominal mass: density 7850 kg/m³, circular area, pi per decimal precision.
        diameter = Decimal(str(r.header.get("d", 0)))
        expected = Decimal("7850") * Decimal("3.141592653589793") / 4 * diameter**2 * Decimal(str(length)) / Decimal("1000000000")
        actual = Decimal(str(r.header.get("e", 0)))
        if abs(expected - actual) > max(Decimal("0.001"), expected * Decimal("0.005")):
            reasons.append(prefix + "Einzelstabgewicht weicht vom nominalen Gewicht ab (Toleranz 0,5 %, mindestens 0,001 kg).")
    return reasons

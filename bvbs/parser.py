import re
from .models import Record, Diagnostic, StraightSegment, Bend, Arc
from .tokenizer import tokenize
from .checksum import inspect
from .geometry import polyline

NUMBER = re.compile(r"-?\d+(?:\.\d+)?\Z")


def parse(text: str) -> list[Record]:
    records = []
    offset = 0
    for line_no, line in enumerate(text.splitlines(keepends=True), 1):
        raw = line.rstrip("\r\n")
        if raw:
            record = Record(len(records), offset, offset + len(raw), line_no, raw)
            _parse_record(record)
            records.append(record)
        offset += len(line)
    return records


def _parse_record(r):
    def diag(code, message, severity="error", field="", offset=0):
        r.diagnostics.append(Diagnostic(severity, code, message, r.id, field, r.start + offset))

    r.kind = r.raw.split("@", 1)[0]
    if not re.match(r"BF[A-Z0-9]{2}@", r.raw):
        diag("record", "Ungültiger Datensatzanfang; erwartet wird BF2D@ …")
    if len(r.raw) > 1000:
        diag("record_length", "Datensatz überschreitet 1000 Zeichen; Export gesperrt.", "warning")
    if "@@" in r.raw:
        diag("empty_token", "Leeres Token zwischen zwei @-Trennzeichen.")
    if not r.raw.endswith("@"):
        diag("terminator", "Datensatz muss mit @ enden.")
    r.blocks = tokenize(r.raw)
    kinds = [b.kind for b in r.blocks]
    if not kinds or kinds[0] != "H" or kinds[-1] != "C":
        diag("blocks", "Header H muss zuerst, Prüfsumme C zuletzt stehen.")
    if kinds.count("H") != 1 or kinds.count("C") != 1 or kinds.count("G") > 1:
        diag("duplicate_block", "Header/Prüfsumme müssen genau einmal, Geometrie höchstens einmal vorkommen.")
    order = {"H": 0, "G": 1, "A": 1, "M": 2, "X": 3, "Y": 3, "E": 3, "P": 4, "C": 5}
    ranks = [order.get(k, 4) for k in kinds]
    if ranks != sorted(ranks) or ("G" in kinds and "A" in kinds):
        diag("block_order", "Ungültige Blockreihenfolge oder gleichzeitige G- und A-Blöcke.")
    headers = [t for b in r.blocks if b.kind == "H" for t in b.tokens]
    for t in headers:
        if t.key in r.header:
            diag("duplicate_field", f"Headerfeld {t.key} ist mehrfach vorhanden.", field=t.key, offset=t.start)
        r.header[t.key] = t.value
        if t.key in "lnedsat" and t.value:
            if not NUMBER.fullmatch(t.value):
                diag("number", f"Ungültige Zahl im Header {t.key}: {t.value}", field=t.key, offset=t.start)
            else:
                t.typed = float(t.value)
                r.header[t.key] = t.typed
                if t.key in "lndes" and t.typed <= 0:
                    diag("positive", f"Header {t.key} muss positiv sein.")
                if t.key == "n" and not t.typed.is_integer():
                    diag("count", "Stückzahl muss ganzzahlig sein.")
    if r.kind == "BF2D":
        keys = [t.key for t in headers]
        sequence = "jriplnedgsvatc"
        if any(k not in sequence for k in keys):
            diag("extension", "Unbekannte Headerfelder: Export gesperrt.", "warning")
        indices = [sequence.index(k) for k in keys if k in sequence]
        if indices != sorted(indices):
            diag("header_order", "Headerfelder stehen nicht in BVBS-Reihenfolge.")
        for key in "riplnedgsv":
            if key not in keys:
                diag("required", f"Pflichtkennung H.{key} fehlt." + (" Importtoleranz für fehlenden Planindex; Export gesperrt." if key == "i" else ""), "warning" if key == "i" else "error", field=key)
        for key in "plnedg":
            if r.header.get(key) in (None, ""):
                diag("empty", f"Header H.{key} benötigt einen Wert.", field=key)
    if r.header.get("v") not in (None, ""):
        diag("extension", "Das reservierte Headerfeld v muss leer bleiben; Export gesperrt.", "warning")
    r.stored_checksum, r.expected_checksum = inspect(r.raw)
    if r.stored_checksum is None:
        diag("checksum_missing", "Prüfsummenblock fehlt oder ist ungültig.")
    elif r.expected_checksum is None:
        diag("ascii", "BVBS definiert ASCII. Nicht-ASCII-Text bleibt erhalten; Prüfsumme unbestätigt.", "warning")
    elif not r.checksum_ok:
        diag("checksum", f"Prüfsumme gespeichert {r.stored_checksum}, erwartet {r.expected_checksum}.", "warning")
    geometry = [t for b in r.blocks if b.kind == "G" for t in b.tokens]
    special = (r.kind != "BF2D" or any(t.key not in "lw" for t in geometry)
               or any(r.header.get(k) not in (None, "") for k in "tc")
               or any(k not in {"H", "G", "C", "P"} for k in kinds))
    if special or not geometry:
        r.elements = [Arc(t.value) for t in geometry if t.key == "r"]
        diag("unsupported", "Sonderform/Datensatztyp nicht grafisch unterstützt; Rohdaten bleiben erhalten.", "warning")
        return
    if len(geometry) % 2 or any(t.key != ("l" if i % 2 == 0 else "w") for i, t in enumerate(geometry)):
        diag("geometry_order", "Geometrie erwartet vollständige Paare lLänge@wWinkel@.")
        return
    for t in geometry:
        if not NUMBER.fullmatch(t.value):
            diag("geometry_number", f"Ungültiger Geometriewert {t.key}{t.value}.", offset=t.start)
            return
        t.typed = float(t.value)
        if t.key == "l" and t.typed <= 0:
            diag("special_length", "Nichtpositive Schenkellängen werden als Sonderform erhalten.", "warning")
            return
        if t.key == "w" and abs(t.typed) > 180:
            diag("angle", "Biegewinkel muss zwischen -180° und 180° liegen.")
            return
        r.elements.append(StraightSegment(t.typed) if t.key == "l" else Bend(t.typed))
    if geometry[-1].typed != 0:
        diag("geometry_end", "Letzter Schenkel muss mit w0@ abgeschlossen werden.")
    if r.syntax_ok:
        r.points = polyline(r.elements)

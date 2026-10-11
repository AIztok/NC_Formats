from .checksum import repair


def encode(text, encoding, bom=b""):
    return bom + text.encode(encoding, errors="strict")


def replace_record(text, record, replacement):
    # A copied record may include its CRLF delimiter. Visual soft wrapping
    # is not part of the value; only internal hard line breaks are rejected.
    replacement = replacement.strip("\r\n")
    if "\r" in replacement or "\n" in replacement:
        raise ValueError("Im Einzelpositionseditor stehen mehrere Textzeilen. Für mehrere Datensätze bitte „Gesamte Datei“ wählen; einen echten Umbruch innerhalb des Datensatzes entfernen.")
    return text[:record.start] + replacement + text[record.end:]


def repair_document(text, records):
    for record in reversed(records):
        text = replace_record(text, record, repair(record.raw))
    return text

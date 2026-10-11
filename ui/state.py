from dataclasses import dataclass, field
from bvbs.parser import parse
from bvbs.serializer import encode, replace_record


def identity(record):
    return (record.kind, str(record.header.get("r")), str(record.header.get("i")), str(record.header.get("p")))


@dataclass
class Document:
    original_bytes: bytes
    encoding: str
    bom: bytes
    original_text: str
    text: str
    name: str
    revision: int = 0
    comparison: bool = True
    last_valid: dict = field(default_factory=dict)
    drafts: dict = field(default_factory=dict)
    error: str = ""
    records: list = field(default_factory=list)
    original_records: list = field(default_factory=list)
    ui: dict = field(default_factory=dict)

    @classmethod
    def load(cls, data, name, encoding="Automatisch"):
        bom = b"\xef\xbb\xbf" if data.startswith(b"\xef\xbb\xbf") else b""
        payload = data[len(bom):]
        if encoding == "Automatisch":
            try:
                text = payload.decode("utf-8")
                encoding = "utf-8"
            except UnicodeDecodeError:
                encoding = "cp1252"
                text = payload.decode(encoding, errors="strict")
        else:
            if bom and encoding != "utf-8":
                raise ValueError("UTF-8-BOM verlangt UTF-8 als Encoding.")
            text = payload.decode(encoding, errors="strict")
        doc = cls(data, encoding, bom, text, text, name)
        doc.refresh()
        doc.original_records = parse(text)
        return doc

    def refresh(self):
        self.records = parse(self.text)
        for r in self.records:
            if r.points is not None:
                self.last_valid[r.id] = r

    def apply(self, target, value):
        try:
            if target == "file":
                newline = "\r\n" if "\r\n" in self.text else "\n"
                value = value.replace("\r\n", "\n").replace("\n", newline)
                updated = value
                before = [identity(r) for r in self.records]
                after = [identity(r) for r in parse(updated)]
                if updated != self.text and (before != after or len(set(before)) != len(before)):
                    self.comparison = False
                    self.last_valid.clear()
                self.drafts.clear()
            else:
                updated = replace_record(self.text, self.records[target], value)
                self.drafts.pop(target, None)
            if updated != self.text:
                self.text = updated
                self.revision += 1
                self.refresh()
            self.error = "Andere Einzelpositionsentwürfe sind noch nicht übernehmbar." if self.drafts else ""
        except ValueError as exc:
            self.drafts[target] = value
            self.error = str(exc)

    def bytes(self):
        # A rejected multiline single-record draft is still downloadable, without repair.
        text = self.text
        for target, value in sorted(self.drafts.items(), reverse=True):
            r = self.records[target]
            text = text[:r.start] + value + text[r.end:]
        if text == self.original_text:
            return self.original_bytes
        return encode(text, self.encoding, self.bom)

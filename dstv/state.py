from dataclasses import dataclass, field
from uuid import uuid4
from .parser import parse, diagnostic
from .serializer import merge_line_endings, encode

DEPENDENCIES = ['profile','profile_type','height','width','flange_thickness','web_thickness','root_radius']


@dataclass
class Document:
    id: str
    name: str
    original_bytes: bytes
    encoding: str
    bom: bytes
    original_text: str
    text: str
    revision: int = 0
    part: object = None
    original_part: object = None
    last_valid: dict = field(default_factory=dict)
    newline_note: str = ''

    @classmethod
    def load(cls, data, name, encoding='Automatisch'):
        bom = b'\xef\xbb\xbf' if data.startswith(b'\xef\xbb\xbf') else b''
        payload = data[len(bom):]
        if encoding == 'Automatisch':
            try:
                text, encoding = payload.decode('utf-8'), 'utf-8'
            except UnicodeDecodeError:
                text, encoding = payload.decode('cp1252', errors='strict'), 'cp1252'
        else:
            if bom and encoding != 'utf-8':
                raise ValueError('UTF-8-BOM verlangt UTF-8 als Encoding.')
            text = payload.decode(encoding,errors='strict')
        doc = cls(uuid4().hex, name, data, encoding, bom, text, text)
        doc.original_part = parse(text,name)
        doc.refresh()
        return doc

    def dependency_reasons(self):
        before = self.original_part.header.values
        after = self.part.header.values
        changed = [key for key in DEPENDENCIES if before.get(key) != after.get(key)]
        return ['Profilbezeichnung/-abmessungen geändert: Profilzuordnung und abhängige Gewichts-/Oberflächenkennwerte bleiben fachlich ungeklärt.'] if changed else []

    def refresh(self):
        self.part = parse(self.text,self.name)
        if self.part.syntax_ok:
            for code,face in self.part.faces.items():
                if face.supported and face.plausible:
                    self.last_valid[code] = (self.revision,self.part,face)

    def apply(self, value):
        merged = merge_line_endings(self.text,value)
        if merged != self.text:
            old_lines = [l for l in self.text.splitlines(keepends=True) if l.endswith(('\r','\n'))]
            endings = {'\r\n' if l.endswith('\r\n') else '\n' if l.endswith('\n') else '\r' for l in old_lines}
            self.newline_note = 'Gemischte Zeilenenden: unveränderte/zugeordnete Zeilen behalten ihren Abschluss; neu eingefügte Zeilen verwenden den häufigsten Abschluss.' if len(endings)>1 else ''
            self.text = merged
            self.revision += 1
            self.refresh()

    def bytes(self):
        if self.text == self.original_text:
            return self.original_bytes
        return encode(self.text,self.encoding,self.bom)

    def reset(self):
        self.text = self.original_text
        self.revision += 1
        self.last_valid.clear()
        self.newline_note = ''
        self.refresh()

from dataclasses import dataclass, field


@dataclass
class SourceLine:
    number: int
    start: int
    end: int
    raw: str
    ending: str


@dataclass
class Diagnostic:
    severity: str
    code: str
    message: str
    filename: str
    block: str
    line: int
    face: str | None = None


@dataclass
class Header:
    values: dict = field(default_factory=dict)
    sources: dict[str, SourceLine] = field(default_factory=dict)
    raw_lines: list[SourceLine] = field(default_factory=list)


@dataclass
class Element:
    id: str
    block: str
    face: str | None
    lines: list[SourceLine]
    supported: bool = True
    points: list[tuple[float, float]] = field(default_factory=list)
    x: float | None = None
    q: float | None = None
    diameter: float | None = None
    marking: bool = False
    reference: str | None = None
    references: list[str | None] = field(default_factory=list)


@dataclass
class Block:
    id: str
    kind: str
    line: int
    start: int
    end: int
    raw: str
    lines: list[SourceLine] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)


@dataclass
class Face:
    code: str
    name: str
    extent: float
    length: float
    q_sign: int
    view: str
    base: list[tuple[float, float]]
    outers: list[Element] = field(default_factory=list)
    inners: list[Element] = field(default_factory=list)
    holes: list[Element] = field(default_factory=list)
    supported: bool = True
    plausible: bool = True
    derived: bool = True
    partial_display: bool = False


@dataclass
class Part:
    filename: str
    text: str
    recognized: bool = False
    header: Header = field(default_factory=Header)
    blocks: list[Block] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    faces: dict[str, Face] = field(default_factory=dict)

    @property
    def syntax_ok(self):
        return self.recognized and not any(d.severity == 'error' and d.code.startswith('syntax') for d in self.diagnostics)

    @property
    def export_ok(self):
        return self.syntax_ok and bool(self.faces) and not self.diagnostics and all(f.supported and f.plausible for f in self.faces.values())

    @property
    def status(self):
        if not self.recognized:
            return 'Kein unterstütztes DSTV'
        if not self.syntax_ok:
            return 'Textfehler'
        if any(d.severity == 'error' for d in self.diagnostics):
            return 'Geometriefehler'
        if self.diagnostics:
            return 'Eingeschränkte Unterstützung'
        return 'Unterstützte Prüfungen bestanden'

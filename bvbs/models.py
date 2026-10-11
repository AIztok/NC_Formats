from dataclasses import dataclass, field


@dataclass
class Token:
    block: str
    key: str
    value: str
    start: int
    end: int
    typed: float | None = None


@dataclass
class Block:
    kind: str
    tokens: list[Token] = field(default_factory=list)


@dataclass
class Diagnostic:
    severity: str
    code: str
    message: str
    record_id: int
    field: str = ""
    offset: int = 0


@dataclass
class StraightSegment:
    length: float


@dataclass
class Bend:
    angle: float


@dataclass
class Arc:
    raw: str


@dataclass
class Record:
    id: int
    start: int
    end: int
    line: int
    raw: str
    kind: str = ""
    blocks: list[Block] = field(default_factory=list)
    header: dict = field(default_factory=dict)
    elements: list = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    points: list[tuple[float, float]] | None = None
    stored_checksum: int | None = None
    expected_checksum: int | None = None

    @property
    def syntax_ok(self):
        return not any(d.severity == "error" for d in self.diagnostics)

    @property
    def checksum_ok(self):
        return self.expected_checksum is not None and self.stored_checksum == self.expected_checksum

    @property
    def status(self):
        if not self.syntax_ok:
            return "Textfehler"
        if self.points is None:
            return "Nicht unterstützt"
        return "Darstellbar" if self.checksum_ok else "Prüfsummenwarnung"

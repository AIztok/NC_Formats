import re
from math import isfinite
from .models import Part, SourceLine, Block, Header, Element, Diagnostic

FIELDS = ['order', 'drawing', 'phase', 'position', 'material', 'quantity', 'profile', 'profile_type',
          'length', 'height', 'width', 'flange_thickness', 'web_thickness', 'root_radius',
          'weight_per_unit', 'surface_per_unit', 'web_start_cut', 'web_end_cut',
          'flange_start_cut', 'flange_end_cut', 'info1', 'info2', 'info3', 'info4']
NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)\Z')
LEX = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)|[A-Za-z]')
MARKER = re.compile(r'[A-Z][A-Z0-9]\Z')


def source_lines(text):
    result, offset = [], 0
    for i, raw in enumerate(text.splitlines(keepends=True), 1):
        body = raw.rstrip('\r\n')
        result.append(SourceLine(i, offset, offset + len(raw), body, raw[len(body):]))
        offset += len(raw)
    return result


def diagnostic(part, code, message, block='ST', line=1, face=None, severity='error'):
    part.diagnostics.append(Diagnostic(severity, code, message, part.filename, block, line, face))


def numeric(value):
    if not NUMBER.fullmatch(value):
        raise ValueError(f'Ungültige Zahl: {value!r}')
    result = float(value)
    if not isfinite(result):
        raise ValueError('Zahl außerhalb des endlichen Wertebereichs.')
    return result


def lex(body):
    tokens, end = [], 0
    for match in LEX.finditer(body):
        if body[end:match.start()].strip():
            raise ValueError(f'Unbekanntes Zahlenformat/Suffix: {body[end:match.start()]!r}')
        tokens.append(match.group())
        end = match.end()
    if body[end:].strip():
        raise ValueError(f'Unbekannter Zusatz: {body[end:]!r}')
    return tokens


def parse(text, filename='part.nc1'):
    part = Part(filename, text)
    lines = source_lines(text)
    meaningful = [line for line in lines if line.raw.strip() and not line.raw.startswith('**')]
    if not meaningful or meaningful[0].raw != 'ST':
        diagnostic(part, 'syntax_format', 'Kein DSTV-Inhalt mit ST-Header. G-Code und andere NC-Dialekte werden nicht unterstützt.')
        return part
    part.recognized = True
    start = meaningful[0].number - 1
    cursor = start + 1
    header_lines = []
    while cursor < len(lines) and len(header_lines) < 24:
        line = lines[cursor]
        if MARKER.fullmatch(line.raw):
            break
        if not line.raw.startswith('**'):
            header_lines.append(line)
        cursor += 1
    part.header = Header(raw_lines=header_lines)
    if len(header_lines) != 24:
        diagnostic(part, 'syntax_header', f'Header benötigt 24 Datenzeilen (Leerzeilen zählen), vorhanden: {len(header_lines)}.', line=cursor+1)
    for key, line in zip(FIELDS, header_lines):
        part.header.sources[key] = line
        value = line.raw.strip()
        if value and not line.raw.startswith('  '):
            diagnostic(part, 'syntax_columns', 'Headerdaten müssen nach zwei führenden Leerzeichen beginnen.', line=line.number)
        try:
            if key == 'quantity':
                if not re.fullmatch(r'\d+', value) or int(value) < 1:
                    raise ValueError('Stückzahl muss eine positive ganze Zahl sein.')
                value = int(value)
            elif key == 'length':
                items = value.split(',')
                if len(items) > 2:
                    raise ValueError('Länge erwartet Länge oder Länge,Sägelänge.')
                value = numeric(items[0].strip())
                if len(items) == 2:
                    part.header.values['saw_length'] = numeric(items[1].strip())
            elif key in FIELDS[9:20]:
                value = numeric(value)
            elif key in ['position', 'material', 'profile', 'profile_type'] and not value:
                raise ValueError(f'Pflichtwert {key} fehlt.')
            part.header.values[key] = value
        except ValueError as exc:
            diagnostic(part, 'syntax_header_number', str(exc), line=line.number)
    current = None
    ended = False
    while cursor < len(lines):
        line = lines[cursor]
        if MARKER.fullmatch(line.raw):
            if current:
                current.end = line.start
                current.raw = text[current.start:current.end]
            kind = line.raw
            current = Block(f'b{len(part.blocks)}', kind, line.number, line.start, len(text), '')
            part.blocks.append(current)
            if kind == 'EN':
                if ended:
                    diagnostic(part, 'syntax_end', 'Mehrfacher EN-Abschluss.', kind, line.number)
                ended = True
            elif ended:
                diagnostic(part, 'syntax_after_end', 'Block nach EN ist unzulässig.', kind, line.number)
            elif kind == 'ST':
                diagnostic(part, 'syntax_multiple_parts', 'Eine Datei muss genau ein Bauteil enthalten.', kind, line.number)
        elif current:
            current.lines.append(line)
            if ended and line.raw.strip() and not line.raw.startswith('**'):
                diagnostic(part, 'syntax_after_end', 'Daten nach EN sind unzulässig.', current.kind, line.number)
        elif line.raw.strip() and not line.raw.startswith('**'):
            diagnostic(part, 'syntax_block', 'Daten außerhalb eines Blocks.', line=line.number)
        cursor += 1
    if current:
        current.raw = text[current.start:current.end]
    if not ended:
        diagnostic(part, 'syntax_end', 'Abschließender EN-Block fehlt.', 'EN', len(lines))
    for block in part.blocks:
        if block.kind in ('BO', 'AK', 'IK'):
            _read_geometry(part, block)
        elif block.kind != 'EN':
            _unsupported_block(part, block)
    from .geometry import build_faces
    build_faces(part)
    return part


def _unsupported_block(part, block):
    # Known face-specific markings can be isolated; unknown blocks might affect all faces.
    data = [l for l in block.lines if l.raw.strip() and not l.raw.startswith('**')]
    faces = {l.raw.strip()[0] for l in data if l.raw.strip()[0] in 'vhou'} if block.kind in ('PU', 'KO', 'SI') else set()
    for face in faces or {None}:
        diagnostic(part, 'unsupported_block', f'Block {block.kind} wird unverändert erhalten, aber nicht vollständig interpretiert. Betroffene Vorschau ist unvollständig.', block.kind, block.line, face, 'warning')
    part.elements.append(Element(block.id+'-raw', block.kind, next(iter(faces)) if len(faces)==1 else None, data, False))


def _read_geometry(part, block):
    face, reference = None, None
    contour = None
    for line in block.lines:
        if not line.raw.strip() or line.raw.startswith('**'):
            continue
        try:
            if not line.raw.startswith('  '):
                raise ValueError('Geometriedaten benötigen zwei führende Leerzeichen.')
            tokens = lex(line.raw[2:])
            explicit = bool(tokens and tokens[0] in 'vhou')
            if explicit:
                face = tokens.pop(0)
            elif block.kind == 'BO' or face is None:
                raise ValueError('Flächenkennung v/h/o/u fehlt oder ist unbekannt.')
            if len(tokens) < 3:
                raise ValueError('Unvollständige Geometriezeile.')
            x = numeric(tokens.pop(0))
            if tokens and tokens[0] in ('o', 'u', 's'):
                reference = tokens.pop(0)
            q = numeric(tokens.pop(0))
            if block.kind == 'BO':
                code = tokens.pop(0) if tokens and tokens[0].isalpha() else ''
                diameter = numeric(tokens.pop(0))
                depth = numeric(tokens.pop(0)) if tokens and NUMBER.fullmatch(tokens[0]) else 0.0
                element = Element(f'{block.id}-l{line.number}', 'BO', face, [line], x=x, q=q, diameter=diameter, reference=reference)
                if diameter < 0:
                    raise ValueError('Negativer Bohrungsdurchmesser.')
                # Tekla 0-diameter holes are punch marks; standard m explicitly denotes marking.
                element.marking = diameter == 0 and code in ('', 'm') and depth == 0 and not tokens
                element.supported = not tokens and depth == 0 and ((diameter > 0 and code == '') or element.marking)
                if not element.supported:
                    diagnostic(part, 'unsupported_hole', 'Sonderbohrung (Gewinde, Stufe/Senkung, Langloch oder Zusatzwerte) nicht als Standardkreis interpretiert.', 'BO', line.number, face, 'warning')
                block.elements.append(element)
                part.elements.append(element)
            else:
                radius = numeric(tokens.pop(0))
                if contour is None or (contour.points and contour.points[0] == contour.points[-1] and len(contour.points)>1) or (explicit and face != contour.face):
                    contour = Element(f'{block.id}-c{len(block.elements)}', block.kind, face, [])
                    block.elements.append(contour)
                    part.elements.append(contour)
                contour.lines.append(line)
                contour.points.append((x,q))
                contour.references.append(reference)
                if radius != 0 or (tokens and any(t.isalpha() or numeric(t) != 0 for t in tokens)):
                    contour.supported = False
                    diagnostic(part, 'unsupported_contour', 'Konturradius, Ausklinkungswerkzeug oder Schweißnahtvorbereitung nicht unterstützt.', block.kind, line.number, face, 'warning')
                elif len(tokens) not in (0, 2, 4):
                    contour.supported = False
                    diagnostic(part, 'unsupported_contour', 'Nicht bewertbare Konturzusatzwerte.', block.kind, line.number, face, 'warning')
        except (ValueError, IndexError) as exc:
            if contour:
                contour.supported = False
            diagnostic(part, 'syntax_geometry', str(exc), block.kind, line.number, face)

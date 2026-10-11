from math import hypot
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from .models import Face

FACE_NAMES = {'v': 'Vorderseite / Steg', 'h': 'Rückseite / Steg', 'o': 'Oberer Flansch', 'u': 'Unterer Flansch'}
# Rotations of the standard-view diagram (DSTV p.8), with x right in every panel.
# v: -90°, h: +90°, o: 180°, u: 0°. This does not change file coordinates.
Q_SIGN = {'v': 1, 'h': -1, 'o': -1, 'u': 1}
VIEW = {'v': 'Blick auf Vorderseite (−Z)', 'h': 'Blick auf Rückseite (+Z)',
        'o': 'Blick auf oberen Flansch (−Y)', 'u': 'Blick auf unteren Flansch (+Y)'}


def view_point(face, x, q):
    return x, Q_SIGN[face] * q


def signed_area(points):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points, points[1:]))/2


def material_polygon(face):
    outer = unary_union([Polygon(e.points) for e in face.outers]) if face.outers else Polygon(face.base)
    return outer.difference(unary_union([Polygon(e.points) for e in face.inners])) if face.inners else outer


def build_faces(part):
    from .parser import diagnostic
    header = part.header.values
    if not part.syntax_ok:
        return
    kind = header.get('profile_type')
    if kind not in ('I','B'):
        diagnostic(part, 'unsupported_profile', f'Profilfamilie {kind!r} wird nicht grafisch unterstützt.', severity='warning')
        return
    required = ['length','height','web_thickness'] + (['width','flange_thickness'] if kind == 'I' else [])
    if any(not isinstance(header.get(k), (int,float)) or header[k] <= 0 for k in required):
        diagnostic(part, 'geometry_dimensions', 'Länge und benötigte Profilmaße müssen positive Headerwerte sein. Keine Geometrie aus Nennprofilnamen erfunden.')
        return
    if kind == 'I' and (2*header['flange_thickness'] >= header['height'] or header['web_thickness'] >= header['width']):
        diagnostic(part, 'geometry_dimensions', 'Profilabmessungen widersprechen einem I-/H-Querschnitt.')
        return
    if any(header.get(k,0) < 0 for k in ['height','width','flange_thickness','web_thickness','root_radius','weight_per_unit','surface_per_unit']):
        diagnostic(part, 'geometry_dimensions', 'Profilmaße, Radius und Kennwerte dürfen nicht negativ sein.')
        return
    if header.get('saw_length', header['length']) < header['length']:
        diagnostic(part, 'geometry_saw_length', 'Sägelänge ist kürzer als die Bauteillänge.')
    codes = ['v'] if kind == 'B' else ['v','h','o','u']
    length = header['length']
    for code in codes:
        extent = header['height'] if code in 'vh' else header['width']
        name = 'Blechfläche' if kind == 'B' else FACE_NAMES[code]
        base = [(0,0),(length,0),(length,extent),(0,extent),(0,0)]
        part.faces[code] = Face(code, name, extent, length, Q_SIGN[code], VIEW[code], base)
    for element in part.elements:
        if element.face not in part.faces:
            if element.block in ('BO','AK','IK'):
                diagnostic(part, 'unsupported_face', f'Fläche {element.face!r} ist für diese Profilteilmenge nicht unterstützt.', element.block, element.lines[0].number if element.lines else 1, element.face, 'warning')
            continue
        face = part.faces[element.face]
        if not element.supported:
            face.supported = False
        if element.block == 'BO':
            face.holes.append(element)
        elif element.block in ('AK','IK'):
            (face.outers if element.block == 'AK' else face.inners).append(element)
            if element.block == 'AK':
                face.derived = False
    # Unsafe geometry cannot be silently omitted on an otherwise complete-looking view.
    for diag in part.diagnostics:
        if diag.code.startswith('unsupported') or diag.code.startswith('syntax_geometry'):
            for face in part.faces.values():
                if diag.face is None or diag.face == face.code or diag.code == 'unsupported_face':
                    face.supported = False
    for face in part.faces.values():
        relevant = [d for d in part.diagnostics if d.code.startswith('unsupported') and (d.face is None or d.face == face.code or d.code == 'unsupported_face')]
        face.partial_display = bool(relevant) and all(d.code == 'unsupported_block' and d.block in ('PU','KO','SI') and d.face == face.code for d in relevant)
    cuts = any(header.get(key,0) != 0 for key in ['web_start_cut','web_end_cut','flange_start_cut','flange_end_cut'])
    if cuts:
        diagnostic(part, 'unsupported_skew', 'Schräge Header-Schnittangaben werden nicht ausgewertet; keine sichere Rechteck-Endkontur.', severity='warning')
        for face in part.faces.values():
            face.supported = False
            face.partial_display = False
    for face in part.faces.values():
        if not face.supported and not face.partial_display:
            continue
        def fail(code, message, element=None):
            face.plausible = False
            diagnostic(part, 'geometry_'+code, message, element.block if element else 'ST',
                       element.lines[0].number if element else part.header.sources['length'].number, face.code)
        envelope = box(0,0,face.length,face.extent)
        for element in face.outers+face.inners:
            pts = element.points
            if len(pts) < 4 or pts[0] != pts[-1] or len(set(pts[:-1])) != len(pts)-1:
                fail('closure', 'Kontur muss geschlossen sein; Zwischenpunkte dürfen sich nicht wiederholen.', element)
                continue
            polygon = Polygon(pts)
            if not polygon.is_valid or polygon.area <= 0:
                fail('contour', 'Selbstschneidende oder flächenlose Kontur.', element)
                continue
            area = signed_area(pts)
            if (element.block == 'AK' and area <= 0) or (element.block == 'IK' and area >= 0):
                fail('orientation', 'AK muss gegen den Uhrzeigersinn, IK im Uhrzeigersinn verlaufen (Dateikoordinaten x/q).', element)
            if not envelope.buffer(1e-7).covers(polygon):
                fail('bounds', 'Kontur überschreitet Länge/Flächenmaß im Header; Koordinaten werden nicht skaliert.', element)
        if not face.plausible:
            continue
        outer = unary_union([Polygon(e.points) for e in face.outers]) if face.outers else Polygon(face.base)
        if outer.geom_type != 'Polygon':
            fail('disconnected', 'Mehrere Außenkonturen ergeben keine zusammenhängende Bauteilfläche.')
        for i,e in enumerate(face.inners):
            inner = Polygon(e.points)
            if not outer.contains(inner) or outer.boundary.intersects(inner):
                fail('inside', 'Innenausschnitt muss vollständig innerhalb der Außenfläche liegen.', e)
            if any(inner.intersects(Polygon(other.points)) for other in face.inners[:i]):
                fail('overlap', 'Innenausschnitte überlappen oder berühren sich.', e)
        if not face.plausible:
            continue
        material = material_polygon(face)
        for i,e in enumerate(face.holes):
            point = Point(e.x,e.q)
            if not material.covers(point) or (not e.marking and material.boundary.distance(point) < e.diameter/2 - 1e-7):
                fail('hole_bounds', 'Bohrung/Ankörnung liegt außerhalb der Materialfläche oder schneidet eine Öffnung/Kante.', e)
            if kind == 'I' and face.code in 'vh' and not e.marking:
                tf = header['flange_thickness']
                if e.q-e.diameter/2 < tf or e.q+e.diameter/2 > face.extent-tf:
                    fail('web_hole', 'Stegbohrung liegt im Bereich der Flanschdicke; keine eindeutig ebene Stegbearbeitung.', e)
            if not e.marking:
                for other in face.holes[:i]:
                    if not other.marking and hypot(e.x-other.x,e.q-other.q) < (e.diameter+other.diameter)/2-1e-7:
                        fail('hole_overlap', 'Standardbohrungen überlappen.', e)

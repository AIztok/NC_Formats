from dataclasses import dataclass, field
from math import cos, sin, radians, atan2, tan, hypot, isfinite
from .models import StraightSegment, Bend


def polyline(elements):
    points = [(0.0, 0.0)]
    heading = 0.0
    for element in elements:
        if isinstance(element, StraightSegment):
            x, y = points[-1]
            points.append((x + element.length * cos(radians(heading)),
                           y + element.length * sin(radians(heading))))
        elif isinstance(element, Bend):
            heading += element.angle
        else:
            raise ValueError("Nicht unterstütztes Geometrieelement")
    return points


@dataclass
class DisplayBend:
    index: int
    angle: float
    center: tuple[float, float]
    middle: tuple[float, float]
    samples: list[tuple[float, float]]
    inner_radius: float
    axis_radius: float


@dataclass
class RadiusPreview:
    points: list[tuple[float, float]]
    bends: list[DisplayBend] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def radius_preview(record):
    """Fillet the schematic measure polygon, without changing BVBS dimensions.

    This constructs circular display bends, not a verified conversion of
    outside dimensions to manufacturing centerline dimensions.
    Never shrink a specified radius to make it fit.
    """
    points = record.points
    result = RadiusPreview(list(points or []))
    if not points or len(points) < 3:
        return result
    diameter, roller = record.header.get("d"), record.header.get("s")
    if not isinstance(diameter, (int, float)) or not isinstance(roller, (int, float)) or not all(isfinite(v) and v > 0 for v in (diameter, roller)):
        result.warnings.append("Biegeradien nicht gezeichnet: gültiger Stab- und Biegerollendurchmesser d/s erforderlich.")
        return result
    inner, radius = roller / 2, (roller + diameter) / 2
    trims = [0.0] * len(points)
    for corner in range(1, len(points) - 1):
        angle = record.elements[2 * (corner - 1) + 1].angle
        if abs(angle) >= 180 - 1e-9:
            result.warnings.append("180°-Haken benötigen eine eigene Außenmaßkonstruktion; die Ansicht bleibt als Maßpolygon erhalten. Radiuswerte werden unten angezeigt.")
            return result
        trims[corner] = radius * tan(radians(abs(angle)) / 2)
    for i, (a, b) in enumerate(zip(points, points[1:])):
        length = hypot(b[0] - a[0], b[1] - a[1])
        if not isfinite(length) or trims[i] + trims[i+1] > length + 1e-8:
            result.warnings.append(f"Biegeradius passt am Schenkel {i+1} nicht in das schematische Maßpolygon. Keine automatische Verkleinerung; Polygon bleibt erhalten.")
            return result
    path = [points[0]]
    for corner in range(1, len(points) - 1):
        a, p, b = points[corner-1:corner+2]
        angle = record.elements[2 * (corner - 1) + 1].angle
        if abs(angle) < 1e-9:
            path.append(p)
            continue
        length = hypot(p[0]-a[0], p[1]-a[1])
        u = ((p[0]-a[0])/length, (p[1]-a[1])/length)
        tangent = (p[0]-u[0]*trims[corner], p[1]-u[1]*trims[corner])
        sign = 1 if angle > 0 else -1
        center = (tangent[0]-sign*u[1]*radius, tangent[1]+sign*u[0]*radius)
        start = atan2(tangent[1]-center[1], tangent[0]-center[0])
        count = max(12, int(abs(angle) / 4))
        samples = [(center[0]+radius*cos(start+radians(angle)*j/count),
                    center[1]+radius*sin(start+radians(angle)*j/count)) for j in range(count+1)]
        middle = (center[0]+radius*cos(start+radians(angle)/2), center[1]+radius*sin(start+radians(angle)/2))
        result.bends.append(DisplayBend(corner, angle, center, middle, samples, inner, radius))
        path.extend(samples)
    path.append(points[-1])
    result.points = path
    return result


def radius_rows(record):
    """Read radius information even where the display fillet is unsupported."""
    diameter, roller = record.header.get("d"), record.header.get("s")
    if not isinstance(diameter, (int, float)) or not isinstance(roller, (int, float)) or not all(isfinite(v) and v > 0 for v in (diameter, roller)):
        return []
    return [{"Biegung nach Schenkel": i//2 + 1, "Winkel [°]": element.angle,
             "Biegerolle Ø [mm]": roller, "Innenradius [mm]": roller/2,
             "Mittellinienradius [mm]": (roller+diameter)/2}
            for i, element in enumerate(record.elements) if isinstance(element, Bend) and element.angle != 0]

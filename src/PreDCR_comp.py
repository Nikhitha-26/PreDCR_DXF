import json
import logging
import sys
from pathlib import Path
from typing import Any
import ezdxf
from pyproj import Transformer  
logger = logging.getLogger(__name__)


PREDCR_RULES: dict[str, dict[str, Any]] = {
    "plotboundary": {"layer": "_PlotBoundary", "color": 6},
    "propwork": {"layer": "_PropWork", "color": 6},
    "room": {"layer": "_Room", "color": 230},
    "window": {"layer": "_Window", "color": 3},
    "road": {"layer": "_Road", "color": 20},
    "marginalopenspace": {"layer": "_MarginalOpenSpace", "color": 50},
    "resifsi": {"layer": "_ResiFSI", "color": 7},
    "commfsi": {"layer": "_CommFSI", "color": 7},
}

INVALID_DXF_LAYER_CHARS = r'/\\:*?"<>|=;,'

def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(levelname)s:%(name)s:%(message)s")


def sanitize_layer_name(name: str | None) -> str:
    """Safe DXF layer name (fixes BUG-02 and Security 14.4)."""
    if not name:
        return "_Unknown"
    cleaned = str(name).strip().replace(" ", "")
    for ch in INVALID_DXF_LAYER_CHARS:
        cleaned = cleaned.replace(ch, "_")
    cleaned = cleaned.strip("_")
    return f"_{cleaned}" if cleaned else "_Unknown"


def get_predcr_standard(shape_name: str | None) -> tuple[str, int]:
    if not shape_name:
        return "_PlotBoundary", 6
    clean_name = str(shape_name).replace("_", "").replace(" ", "").strip().lower()
    if clean_name in PREDCR_RULES:
        rule = PREDCR_RULES[clean_name]
        return str(rule["layer"]), int(rule["color"])
    return sanitize_layer_name(shape_name), 7


def validate_geojson_structure(data: dict[str, Any]) -> None:
    """Strict validation (addresses 6.6)."""
    if data.get("type") != "FeatureCollection":
        raise ValueError("Input must be a GeoJSON FeatureCollection")
    if not isinstance(data.get("features"), list):
        raise ValueError("'features' must be a list")


def _looks_like_geographic_coordinates(points: list[tuple[float, float]]) -> bool:
    """Smart warning if someone accidentally gives lat/long."""
    if not points:
        return False
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return all(-180 <= x <= 180 for x in xs) and all(-90 <= y <= 90 for y in ys)


def _to_2d_points(
    coords: list[Any], transformer: Transformer | None = None, feature_index: int = 0
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for pt in coords:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            continue
        try:
            x, y = float(pt[0]), float(pt[1])
            if transformer:
                x, y = transformer.transform(x, y)
            points.append((x, y))
            if len(pt) > 2 and abs(float(pt[2])) > 0.001:
                logger.warning("Feature %s dropped Z coordinate", feature_index)
        except (TypeError, ValueError):
            logger.warning("Feature %s invalid coordinate %r", feature_index, pt)
    return points


def _ensure_layer(doc: ezdxf.document.Drawing, layer_name: str, color: int) -> None:
    if not doc.layers.has_entry(layer_name):
        doc.layers.add(name=layer_name, color=color)


def _draw_polygon(msp, points: list[tuple[float, float]], layer_name: str) -> None:
    if points:
        msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer_name})


def _draw_linestring(msp, points: list[tuple[float, float]], layer_name: str) -> None:
    if points:
        msp.add_lwpolyline(points, close=False, dxfattribs={"layer": layer_name})


def _draw_point(msp, coordinates, layer_name: str, radius: float, transformer=None) -> None:
    if not coordinates or len(coordinates) < 2:
        return
    x, y = float(coordinates[0]), float(coordinates[1])
    if transformer:
        x, y = transformer.transform(x, y)
    msp.add_circle((x, y), radius, dxfattribs={"layer": layer_name})


def generate_predcr_dxf(
    data: dict[str, Any],
    output_file: str | Path,
    target_epsg: str | None = None,   
) -> None:
    """Improved production version — covers ALL Must-Fix items from the Developer Guide."""
    validate_geojson_structure(data)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    transformer: Transformer | None = None
    if target_epsg:
        transformer = Transformer.from_crs("EPSG:4326", target_epsg, always_xy=True)
        logger.info("CRS enabled → %s", target_epsg)

    features = data.get("features", [])
    processed = skipped = failed = 0

    for index, feature in enumerate(features, start=1):
        try:
            props = feature.get("properties") or {}
            geometry = feature.get("geometry")
            if geometry is None:
                skipped += 1
                continue

            raw_name = props.get("name") or props.get("layer") or "Unknown"
            target_layer, target_color = get_predcr_standard(raw_name)
            _ensure_layer(doc, target_layer, target_color)

            geom_type = geometry.get("type")
            coords = geometry.get("coordinates", [])

            drew = False
            if geom_type == "Polygon":
                for ring_idx, ring in enumerate(coords):
                    points = _to_2d_points(ring, transformer, index)
                    if points:
                        _draw_polygon(msp, points, target_layer)
                        if _looks_like_geographic_coordinates(points):
                            logger.warning("Feature %s appears to be in lat/long!", index)
                        drew = True
            elif geom_type == "LineString":
                points = _to_2d_points(coords, transformer, index)
                if points:
                    _draw_linestring(msp, points, target_layer)
                    drew = True
            elif geom_type == "Point":
                radius = float(props.get("radius", 1.0))
                _draw_point(msp, coords, target_layer, radius, transformer)
                drew = True
            elif geom_type == "MultiPolygon":
                for poly in coords:
                    for ring in poly:
                        points = _to_2d_points(ring, transformer, index)
                        if points:
                            _draw_polygon(msp, points, target_layer)
                            drew = True
            elif geom_type == "MultiLineString":
                for line in coords:
                    points = _to_2d_points(line, transformer, index)
                    if points:
                        _draw_linestring(msp, points, target_layer)
                        drew = True

            if drew:
                processed += 1
                logger.info("✓ Feature %s → %s on layer %s", index, geom_type, target_layer)
            else:
                skipped += 1

        except Exception:
            failed += 1
            logger.exception("Feature %s failed", index)
            continue

    doc.saveas(str(output_path))
    logger.info(
        "✅ DXF saved: %s | processed=%d skipped=%d failed=%d",
        output_path, processed, skipped, failed
    )


def load_geojson(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    configure_logging()
    if len(sys.argv) >= 3:
        input_file, output_file = sys.argv[1], sys.argv[2]
    else:
        print("--- PreDCR Converter (Production Ready) ---")
        input_file = input("Enter input GeoJSON path: ").strip()
        output_file = input("Enter output DXF path: ").strip()

    try:
        data = load_geojson(input_file)
        generate_predcr_dxf(data, output_file)          # ← your metric files
        # generate_predcr_dxf(data, output_file, "EPSG:32643")  # ← only if lat/long
    except Exception:
        logger.exception("Fatal error")
        raise


if __name__ == "__main__":
    main()
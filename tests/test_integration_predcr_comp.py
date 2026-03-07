"""
Integration tests for PreDCR_comp.py — generate_predcr_dxf()

Each test calls generate_predcr_dxf() with a fixture GeoJSON, writes the DXF
to a pytest tmp_path directory, then reads the result back with ezdxf.readfile()
to assert structural correctness.

Key conventions:
    - All file writes go to tmp_path (never to data/)
    - TC-I09 is intentionally marked xfail — it documents a known bug:
      features with "properties": null crash with AttributeError
"""
import ezdxf
import pytest

from PreDCR_comp import generate_predcr_dxf


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_and_read(data, tmp_path, filename="output.dxf"):
    """Write DXF from data dict, return (doc, msp, entity_list)."""
    out = tmp_path / filename
    generate_predcr_dxf(data, str(out))
    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()
    entities = list(msp)
    return doc, msp, entities


def layer_color(doc, layer_name):
    """Return the ACI color index of a named layer."""
    return doc.layers.get(layer_name).dxf.color


# ---------------------------------------------------------------------------
# TC-I01  Minimal happy path — single PlotBoundary polygon
# ---------------------------------------------------------------------------

class TestSinglePlotBoundary:
    def test_entity_count(self, tc01_data, tmp_path):
        """TC-I01a | 1 feature → exactly 1 entity in modelspace."""
        _, _, entities = run_and_read(tc01_data, tmp_path)
        assert len(entities) == 1

    def test_layer_exists(self, tc01_data, tmp_path):
        """TC-I01b | Layer _PlotBoundary must be created in DXF."""
        doc, _, _ = run_and_read(tc01_data, tmp_path)
        assert doc.layers.has_entry("_PlotBoundary")

    def test_layer_color_is_magenta(self, tc01_data, tmp_path):
        """TC-I01c | PreDCR mandates _PlotBoundary = color 6 (Magenta)."""
        doc, _, _ = run_and_read(tc01_data, tmp_path)
        assert layer_color(doc, "_PlotBoundary") == 6

    def test_entity_is_lwpolyline(self, tc01_data, tmp_path):
        """TC-I01d | Polygon GeoJSON → LWPOLYLINE entity in DXF."""
        _, _, entities = run_and_read(tc01_data, tmp_path)
        assert entities[0].dxftype() == "LWPOLYLINE"


# ---------------------------------------------------------------------------
# TC-I02  Full floor plan — multi-layer, mixed entity types
# ---------------------------------------------------------------------------

class TestFullFloorPlan:
    def test_entity_count(self, tc02_data, tmp_path):
        """TC-I02a | 10 features (6 polygons + 4 linestrings) → 10 entities."""
        _, _, entities = run_and_read(tc02_data, tmp_path)
        assert len(entities) == 10

    def test_all_predcr_layers_created(self, tc02_data, tmp_path):
        """TC-I02b | _PlotBoundary, _PropWork, _Room, _Window all created."""
        doc, _, _ = run_and_read(tc02_data, tmp_path)
        for name in ("_PlotBoundary", "_PropWork", "_Room", "_Window"):
            assert doc.layers.has_entry(name), f"Layer {name!r} not found in DXF"

    def test_room_layer_color(self, tc02_data, tmp_path):
        """TC-I02c | PreDCR mandates _Room = color 230."""
        doc, _, _ = run_and_read(tc02_data, tmp_path)
        assert layer_color(doc, "_Room") == 230

    def test_window_layer_color(self, tc02_data, tmp_path):
        """TC-I02d | PreDCR mandates _Window = color 3 (Green)."""
        doc, _, _ = run_and_read(tc02_data, tmp_path)
        assert layer_color(doc, "_Window") == 3

    def test_room_layer_created_exactly_once(self, tc02_data, tmp_path):
        """TC-I02e | 4 Room features share ONE layer, not 4 duplicate layers."""
        doc, _, _ = run_and_read(tc02_data, tmp_path)
        room_layers = [lyr for lyr in doc.layers if lyr.dxf.name == "_Room"]
        assert len(room_layers) == 1

    def test_window_entities_are_open_polylines(self, tc02_data, tmp_path):
        """TC-I02f | LineString windows must produce OPEN (non-closed) LWPOLYLINEs."""
        _, msp, _ = run_and_read(tc02_data, tmp_path)
        window_entities = msp.query('LWPOLYLINE[layer=="_Window"]')
        assert len(window_entities) == 4
        for ent in window_entities:
            assert not ent.closed, "Window polyline should be open, not closed"


# ---------------------------------------------------------------------------
# TC-I03  Unknown layers — names not in PREDCR_RULES
# ---------------------------------------------------------------------------

class TestUnknownLayers:
    def test_unknown_layers_created_with_underscore_prefix(self, tc03_data, tmp_path):
        """TC-I03a | Unknown names get '_' prefix → _Parking, _SwimmingPool, _OpenTerrace."""
        doc, _, _ = run_and_read(tc03_data, tmp_path)
        for name in ("_Parking", "_SwimmingPool", "_OpenTerrace"):
            assert doc.layers.has_entry(name), f"Expected layer {name!r} not found"

    def test_unknown_layers_all_have_color_7(self, tc03_data, tmp_path):
        """TC-I03b | Unknown layers must fall back to color 7 (white/default)."""
        doc, _, _ = run_and_read(tc03_data, tmp_path)
        for name in ("_Parking", "_SwimmingPool", "_OpenTerrace"):
            assert layer_color(doc, name) == 7

    def test_entity_count_matches_features(self, tc03_data, tmp_path):
        """TC-I03c | 3 unknown features → 3 entities drawn."""
        _, _, entities = run_and_read(tc03_data, tmp_path)
        assert len(entities) == 3


# ---------------------------------------------------------------------------
# TC-I04  Mixed geometry — Polygon, LineString, Point in one file
# ---------------------------------------------------------------------------

class TestMixedGeometry:
    def test_total_entity_count(self, tc04_data, tmp_path):
        """TC-I04a | 3 features (Polygon, LineString, Point) → 3 entities."""
        _, _, entities = run_and_read(tc04_data, tmp_path)
        assert len(entities) == 3

    def test_point_becomes_circle(self, tc04_data, tmp_path):
        """TC-I04b | Point geometry → CIRCLE entity in DXF."""
        _, _, entities = run_and_read(tc04_data, tmp_path)
        circles = [e for e in entities if e.dxftype() == "CIRCLE"]
        assert len(circles) == 1

    def test_linestring_is_open_polyline(self, tc04_data, tmp_path):
        """TC-I04c | LineString → open LWPOLYLINE (closed=False)."""
        _, msp, _ = run_and_read(tc04_data, tmp_path)
        window_polys = msp.query('LWPOLYLINE[layer=="_Window"]')
        assert len(window_polys) == 1
        assert not window_polys[0].closed

    def test_polygon_is_closed_polyline(self, tc04_data, tmp_path):
        """TC-I04d | Polygon geometry → closed LWPOLYLINE (closed=True)."""
        _, msp, _ = run_and_read(tc04_data, tmp_path)
        road_polys = msp.query('LWPOLYLINE[layer=="_Road"]')
        assert len(road_polys) == 1
        assert road_polys[0].closed


# ---------------------------------------------------------------------------
# TC-I05  Real-world GPS coordinates (Mumbai Bandra plot)
# ---------------------------------------------------------------------------

class TestGpsCoordinates:
    def test_no_exception_on_gps_input(self, tc05_data, tmp_path):
        """TC-I05a | GPS lat/lng coordinates must not raise any exception."""
        run_and_read(tc05_data, tmp_path)  # must not raise

    def test_output_file_is_valid_dxf(self, tc05_data, tmp_path):
        """TC-I05b | Output is a valid, re-openable DXF file."""
        out = tmp_path / "gps_output.dxf"
        generate_predcr_dxf(tc05_data, str(out))
        doc = ezdxf.readfile(str(out))
        assert doc is not None

    def test_coordinates_passed_through_unmodified(self, tc05_data, tmp_path):
        """TC-I05c | GPS coords stored as-is (no CRS reprojection performed)."""
        _, msp, _ = run_and_read(tc05_data, tmp_path)
        plot_polys = msp.query('LWPOLYLINE[layer=="_PlotBoundary"]')
        assert len(plot_polys) >= 1
        first_vertex_x = list(plot_polys[0].vertices())[0][0]
        # GPS longitude for Mumbai ≈ 72.87° — must not be projected to metres
        assert pytest.approx(first_vertex_x, abs=0.001) == 72.87


# ---------------------------------------------------------------------------
# TC-I06  Empty FeatureCollection
# ---------------------------------------------------------------------------

class TestEmptyFeatureCollection:
    def test_zero_entities_in_modelspace(self, tc06_data, tmp_path):
        """TC-I06a | Empty features list → modelspace has 0 entities."""
        _, _, entities = run_and_read(tc06_data, tmp_path)
        assert len(entities) == 0

    def test_output_dxf_is_still_valid(self, tc06_data, tmp_path):
        """TC-I06b | Even an empty input produces a valid DXF structure."""
        out = tmp_path / "empty.dxf"
        generate_predcr_dxf(tc06_data, str(out))
        assert out.exists()
        doc = ezdxf.readfile(str(out))
        assert doc is not None


# ---------------------------------------------------------------------------
# TC-I07  Edge case — null geometry (EDGE-1 from tc07)
# ---------------------------------------------------------------------------

class TestNullGeometry:
    def test_null_geometry_feature_silently_skipped(self, tmp_path):
        """TC-I07 | Feature with geometry:null is skipped without crashing."""
        data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "_PlotBoundary"},
                    "geometry": None
                }
            ]
        }
        _, _, entities = run_and_read(data, tmp_path)
        assert len(entities) == 0


# ---------------------------------------------------------------------------
# TC-I08  Edge case — 'layer' property used when 'name' is absent (EDGE-3)
# ---------------------------------------------------------------------------

class TestLayerPropertyFallback:
    def test_layer_key_used_when_name_absent(self, tmp_path):
        """TC-I08 | Feature with only 'layer' property (no 'name') → correct layer."""
        data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"layer": "_Window"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[2, 0], [6, 0]]
                    }
                }
            ]
        }
        doc, msp, entities = run_and_read(data, tmp_path)
        assert len(entities) == 1
        assert doc.layers.has_entry("_Window")
        assert layer_color(doc, "_Window") == 3


# ---------------------------------------------------------------------------
# TC-I09  KNOWN BUG — 'properties': null crashes with AttributeError
#         Marked xfail: documents the bug without blocking the suite.
#         Fix: add `if props is None: props = {}` after line 65 in PreDCR_comp.py
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason="Known bug: 'properties': null causes AttributeError on props.get() — "
           "fix by guarding: if props is None: props = {}"
)
class TestNullPropertiesBug:
    def test_null_properties_crashes(self, tmp_path):
        """TC-I09 | Feature with properties:null → currently raises AttributeError."""
        data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": None,
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]]
                    }
                }
            ]
        }
        # This call SHOULD succeed after the bug is fixed.
        # Until fixed, it raises AttributeError — hence xfail(strict=True).
        run_and_read(data, tmp_path)


# ---------------------------------------------------------------------------
# TC-I10  Edge case — 'name' wins over 'layer' when both conflict (EDGE-4)
# ---------------------------------------------------------------------------

class TestNameBeatsLayer:
    def test_name_property_takes_precedence_over_layer(self, tmp_path):
        """TC-I10 | name='_Road', layer='_PlotBoundary' → entity on _Road layer."""
        data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "_Road", "layer": "_PlotBoundary"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, -8], [20, -8], [20, 0], [0, 0], [0, -8]]]
                    }
                }
            ]
        }
        doc, msp, entities = run_and_read(data, tmp_path)
        assert len(entities) == 1
        assert entities[0].dxf.layer == "_Road"
        assert layer_color(doc, "_Road") == 20
        # _PlotBoundary should NOT have been created (name won, layer ignored)
        assert not doc.layers.has_entry("_PlotBoundary")


# ---------------------------------------------------------------------------
# TC-I11  Edge case — MultiPolygon silently skipped (tc08)
# ---------------------------------------------------------------------------

class TestMultiPolygonSkipped:
    def test_multipolygon_silently_ignored(self, tc08_data, tmp_path):
        """TC-I11 | MultiPolygon geometry → skipped; only valid Polygon drawn."""
        _, _, entities = run_and_read(tc08_data, tmp_path)
        # tc08 has 1 valid Polygon + 1 MultiPolygon → only 1 entity
        assert len(entities) == 1

    def test_valid_polygon_in_same_file_still_drawn(self, tc08_data, tmp_path):
        """TC-I11b | Non-MultiPolygon feature in file still renders correctly."""
        doc, _, entities = run_and_read(tc08_data, tmp_path)
        assert doc.layers.has_entry("_PlotBoundary")


# ---------------------------------------------------------------------------
# TC-I12  Edge case — Polygon with interior ring (donut hole), only outer drawn
# ---------------------------------------------------------------------------

class TestPolygonWithHole:
    def test_only_outer_ring_used(self, tmp_path):
        """TC-I12 | Polygon with hole → LWPOLYLINE uses outer ring vertices only."""
        outer = [[0, 0], [20, 0], [20, 20], [0, 20], [0, 0]]
        inner = [[5, 5], [15, 5], [15, 15], [5, 15], [5, 5]]
        data = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"name": "_PropWork"},
                "geometry": {"type": "Polygon", "coordinates": [outer, inner]}
            }]
        }
        _, msp, entities = run_and_read(data, tmp_path)
        assert len(entities) == 1
        # Outer ring has 5 vertices (incl. closing); LWPOLYLINE stores close flag separately
        poly = entities[0]
        assert poly.dxftype() == "LWPOLYLINE"
        assert len(list(poly.vertices())) == 5  # outer ring: 5 pts (4 corners + 1 repeat)


# ---------------------------------------------------------------------------
# TC-I13  Round-trip validity — every fixture produces a re-openable DXF
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture_name", [
    "tc01_single_plot.geojson",
    "tc02_full_floor_plan.geojson",
    "tc03_unknown_layers.geojson",
    "tc04_mixed_geometry.geojson",
    "tc05_gps_mumbai.geojson",
    "tc06_empty_collection.geojson",
    "tc08_multipolygon.geojson",
])
def test_dxf_round_trip_valid(fixture_name, fixtures_dir, tmp_path):
    """TC-I13 | Every valid fixture produces a DXF that ezdxf can re-open."""
    import json
    with open(fixtures_dir / fixture_name) as f:
        data = json.load(f)
    out = tmp_path / "round_trip.dxf"
    generate_predcr_dxf(data, str(out))
    assert out.exists(), "DXF file was not created"
    doc = ezdxf.readfile(str(out))
    assert doc is not None, "ezdxf could not parse the output DXF"

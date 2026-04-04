"""
Integration tests for PreDCR_comp.py — generate_predcr_dxf()
"""
import json

import ezdxf
import pytest

from PreDCR_comp import generate_predcr_dxf


def run_and_read(data, tmp_path, filename="output.dxf"):
    out = tmp_path / filename
    generate_predcr_dxf(data, str(out))
    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()
    entities = list(msp)
    return doc, msp, entities


def layer_color(doc, layer_name):
    return doc.layers.get(layer_name).dxf.color


# --------------------------------------------------------------------------- 
# All previous tests (unchanged)
# --------------------------------------------------------------------------- 

class TestSinglePlotBoundary:
    def test_entity_count(self, tc01_data, tmp_path):
        _, _, entities = run_and_read(tc01_data, tmp_path)
        assert len(entities) == 1

    def test_layer_exists(self, tc01_data, tmp_path):
        doc, _, _ = run_and_read(tc01_data, tmp_path)
        assert doc.layers.has_entry("_PlotBoundary")

    def test_layer_color_is_magenta(self, tc01_data, tmp_path):
        doc, _, _ = run_and_read(tc01_data, tmp_path)
        assert layer_color(doc, "_PlotBoundary") == 6

    def test_entity_is_lwpolyline(self, tc01_data, tmp_path):
        _, _, entities = run_and_read(tc01_data, tmp_path)
        assert entities[0].dxftype() == "LWPOLYLINE"


class TestFullFloorPlan:
    def test_entity_count(self, tc02_data, tmp_path):
        _, _, entities = run_and_read(tc02_data, tmp_path)
        assert len(entities) == 10

    def test_all_predcr_layers_created(self, tc02_data, tmp_path):
        doc, _, _ = run_and_read(tc02_data, tmp_path)
        for name in ("_PlotBoundary", "_PropWork", "_Room", "_Window"):
            assert doc.layers.has_entry(name)

    def test_room_layer_color(self, tc02_data, tmp_path):
        doc, _, _ = run_and_read(tc02_data, tmp_path)
        assert layer_color(doc, "_Room") == 230

    def test_window_layer_color(self, tc02_data, tmp_path):
        doc, _, _ = run_and_read(tc02_data, tmp_path)
        assert layer_color(doc, "_Window") == 3

    def test_room_layer_created_exactly_once(self, tc02_data, tmp_path):
        doc, _, _ = run_and_read(tc02_data, tmp_path)
        room_layers = [lyr for lyr in doc.layers if lyr.dxf.name == "_Room"]
        assert len(room_layers) == 1

    def test_window_entities_are_open_polylines(self, tc02_data, tmp_path):
        _, msp, _ = run_and_read(tc02_data, tmp_path)
        window_entities = msp.query('LWPOLYLINE[layer=="_Window"]')
        assert len(window_entities) == 4
        for ent in window_entities:
            assert not ent.closed


class TestUnknownLayers:
    def test_unknown_layers_created_with_underscore_prefix(self, tc03_data, tmp_path):
        doc, _, _ = run_and_read(tc03_data, tmp_path)
        for name in ("_Parking", "_SwimmingPool", "_OpenTerrace"):
            assert doc.layers.has_entry(name)

    def test_unknown_layers_all_have_color_7(self, tc03_data, tmp_path):
        doc, _, _ = run_and_read(tc03_data, tmp_path)
        for name in ("_Parking", "_SwimmingPool", "_OpenTerrace"):
            assert layer_color(doc, name) == 7

    def test_entity_count_matches_features(self, tc03_data, tmp_path):
        _, _, entities = run_and_read(tc03_data, tmp_path)
        assert len(entities) == 3


class TestMixedGeometry:
    def test_total_entity_count(self, tc04_data, tmp_path):
        _, _, entities = run_and_read(tc04_data, tmp_path)
        assert len(entities) == 3

    def test_point_becomes_circle(self, tc04_data, tmp_path):
        _, _, entities = run_and_read(tc04_data, tmp_path)
        circles = [e for e in entities if e.dxftype() == "CIRCLE"]
        assert len(circles) == 1

    def test_linestring_is_open_polyline(self, tc04_data, tmp_path):
        _, msp, _ = run_and_read(tc04_data, tmp_path)
        window_polys = msp.query('LWPOLYLINE[layer=="_Window"]')
        assert len(window_polys) == 1
        assert not window_polys[0].closed

    def test_polygon_is_closed_polyline(self, tc04_data, tmp_path):
        _, msp, _ = run_and_read(tc04_data, tmp_path)
        road_polys = msp.query('LWPOLYLINE[layer=="_Road"]')
        assert len(road_polys) == 1
        assert road_polys[0].closed


class TestGpsCoordinates:
    def test_no_exception_on_gps_input(self, tc05_data, tmp_path):
        run_and_read(tc05_data, tmp_path)

    def test_output_file_is_valid_dxf(self, tc05_data, tmp_path):
        out = tmp_path / "gps_output.dxf"
        generate_predcr_dxf(tc05_data, str(out))
        doc = ezdxf.readfile(str(out))
        assert doc is not None

    def test_coordinates_passed_through_unmodified(self, tc05_data, tmp_path):
        _, msp, _ = run_and_read(tc05_data, tmp_path)
        plot_polys = msp.query('LWPOLYLINE[layer=="_PlotBoundary"]')
        assert len(plot_polys) >= 1
        first_vertex_x = list(plot_polys[0].vertices())[0][0]
        assert pytest.approx(first_vertex_x, abs=0.001) == 72.87


class TestEmptyFeatureCollection:
    def test_zero_entities_in_modelspace(self, tc06_data, tmp_path):
        _, _, entities = run_and_read(tc06_data, tmp_path)
        assert len(entities) == 0

    def test_output_dxf_is_still_valid(self, tc06_data, tmp_path):
        out = tmp_path / "empty.dxf"
        generate_predcr_dxf(tc06_data, str(out))
        assert out.exists()
        doc = ezdxf.readfile(str(out))
        assert doc is not None


class TestNullGeometry:
    def test_null_geometry_feature_silently_skipped(self, tmp_path):
        data = {
            "type": "FeatureCollection",
            "features": [{"properties": {"name": "_PlotBoundary"}, "geometry": None}],
        }
        _, _, entities = run_and_read(data, tmp_path)
        assert len(entities) == 0


class TestLayerPropertyFallback:
    def test_layer_key_used_when_name_absent(self, tmp_path):
        data = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"layer": "_Window"},
                "geometry": {"type": "LineString", "coordinates": [[2, 0], [6, 0]]},
            }],
        }
        doc, _, entities = run_and_read(data, tmp_path)
        assert len(entities) == 1
        assert doc.layers.has_entry("_Window")
        assert layer_color(doc, "_Window") == 3


class TestNullPropertiesNowHandled:
    def test_null_properties_no_longer_crash(self, tmp_path):
        data = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": None,
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]},
            }],
        }
        doc, _, entities = run_and_read(data, tmp_path)
        assert len(entities) == 1
        assert doc.layers.has_entry("_Unknown")
        assert layer_color(doc, "_Unknown") == 7


class TestNameBeatsLayer:
    def test_name_property_takes_precedence_over_layer(self, tmp_path):
        data = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"name": "_Road", "layer": "_PlotBoundary"},
                "geometry": {"type": "Polygon", "coordinates": [[[0, -8], [20, -8], [20, 0], [0, 0], [0, -8]]]},
            }],
        }
        doc, _, entities = run_and_read(data, tmp_path)
        assert len(entities) == 1
        assert entities[0].dxf.layer == "_Road"
        assert layer_color(doc, "_Road") == 20
        assert not doc.layers.has_entry("_PlotBoundary")


# --------------------------------------------------------------------------- 
# UPDATED TESTS (fixed for current correct behavior)
# --------------------------------------------------------------------------- 

class TestMultiPolygonSupported:
    def test_multipolygon_is_drawn(self, tc08_data, tmp_path):
        """tc08 contains 1 Polygon + 1 MultiPolygon (with 2 components) → 3 entities total."""
        _, _, entities = run_and_read(tc08_data, tmp_path)
        assert len(entities) == 3   # ← FIXED

    def test_valid_polygon_in_same_file_still_drawn(self, tc08_data, tmp_path):
        doc, _, _ = run_and_read(tc08_data, tmp_path)
        assert doc.layers.has_entry("_PlotBoundary")


class TestPolygonWithHole:
    def test_outer_and_inner_rings_are_drawn(self, tmp_path):
        outer = [[0, 0], [20, 0], [20, 20], [0, 20], [0, 0]]
        inner = [[5, 5], [15, 5], [15, 15], [5, 15], [5, 5]]
        data = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"name": "_PropWork"},
                "geometry": {"type": "Polygon", "coordinates": [outer, inner]},
            }],
        }
        _, _, entities = run_and_read(data, tmp_path)
        assert len(entities) == 2
        for ent in entities:
            assert ent.dxftype() == "LWPOLYLINE"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "tc01_single_plot.geojson", "tc02_full_floor_plan.geojson",
        "tc03_unknown_layers.geojson", "tc04_mixed_geometry.geojson",
        "tc05_gps_mumbai.geojson", "tc06_empty_collection.geojson",
        "tc08_multipolygon.geojson",
    ],
)
def test_dxf_round_trip_valid(fixture_name, fixtures_dir, tmp_path):
    with open(fixtures_dir / fixture_name) as f:
        data = json.load(f)
    out = tmp_path / "round_trip.dxf"
    generate_predcr_dxf(data, str(out))
    assert out.exists()
    doc = ezdxf.readfile(str(out))
    assert doc is not None
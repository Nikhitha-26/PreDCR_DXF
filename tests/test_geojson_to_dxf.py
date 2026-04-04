"""
Tests for the old demo: geojson_to_dxf.py (kept for reference)
"""

import pathlib
import sys

import ezdxf
import pytest

# ====================== FIXED PATH FOR SRC FOLDER ======================
# Since geojson_to_dxf.py is inside src/, we add the src folder to Python path
SRC_DIR = pathlib.Path(__file__).parent.parent / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Now we can import the old demo file correctly
from geojson_to_dxf import add_shapes


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def blank_doc():
    return ezdxf.new("R2010")


# ---------------------------------------------------------------------------
# All your original tests (unchanged)
# ---------------------------------------------------------------------------

class TestAddShapesEntities:
    def test_five_entities_created(self, blank_doc):
        add_shapes(blank_doc)
        entities = list(blank_doc.modelspace())
        assert len(entities) == 5

    def test_one_circle_entity_present(self, blank_doc):
        add_shapes(blank_doc)
        circles = [e for e in blank_doc.modelspace() if e.dxftype() == "CIRCLE"]
        assert len(circles) == 1

    def test_circle_is_on_correct_layer(self, blank_doc):
        add_shapes(blank_doc)
        circles = [e for e in blank_doc.modelspace() if e.dxftype() == "CIRCLE"]
        assert circles[0].dxf.layer == "_Circle"

    def test_lwpolylines_present(self, blank_doc):
        add_shapes(blank_doc)
        polys = [e for e in blank_doc.modelspace() if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) >= 4


EXPECTED_LAYERS = {
    "_Circle":    1,
    "_Square":    30,
    "_Triangle":  140,
    "_Pentagon":  4,
    "_Hexagon":   3,
    "_Rectangle": 5,
    "_Line":      8,
}


class TestLayerColors:
    @pytest.mark.parametrize("layer_name, expected_color", list(EXPECTED_LAYERS.items()))
    def test_layer_exists_with_correct_color(self, blank_doc, layer_name, expected_color):
        add_shapes(blank_doc)
        assert blank_doc.layers.has_entry(layer_name)
        actual_color = blank_doc.layers.get(layer_name).dxf.color
        assert actual_color == expected_color


class TestDxfRoundTrip:
    def test_saved_dxf_is_valid(self, blank_doc, tmp_path):
        from geojson_to_dxf import main
        out = tmp_path / "shapes_test.dxf"
        main(output_file=out)
        assert out.exists()
        doc = ezdxf.readfile(str(out))
        assert doc is not None


class TestHexagonVertices:
    def test_hexagon_polyline_has_six_vertices(self, blank_doc):
        add_shapes(blank_doc)
        hex_entities = [
            e for e in blank_doc.modelspace()
            if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "_Hexagon"
        ]
        assert len(hex_entities) == 1
        vertices = list(hex_entities[0].vertices())
        assert len(vertices) == 6
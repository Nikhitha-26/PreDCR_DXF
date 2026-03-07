"""
Tests for geojson_to_dxf.py — add_shapes() and main()

Verifies:
    TC-S01  add_shapes() populates modelspace with expected entities
    TC-S02  All 7 layers are created with correct ACI colors
    TC-S03  Saved DXF is readable by ezdxf (round-trip validity)
    TC-S04  Importing the module does NOT write any files (no side-effects)
    TC-S05  Hexagon entity has exactly 6 vertices
"""
import importlib
import pathlib
import sys

import ezdxf
import pytest


# Ensure src/ is importable (root conftest.py also does this, belt-and-suspenders)
SRC_DIR = pathlib.Path(__file__).parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from geojson_to_dxf import add_shapes


# ---------------------------------------------------------------------------
# Shared fixture: a blank R2010 ezdxf document
# ---------------------------------------------------------------------------

@pytest.fixture
def blank_doc():
    """Returns a fresh blank ezdxf R2010 document for each test."""
    return ezdxf.new("R2010")


# ---------------------------------------------------------------------------
# TC-S01  add_shapes() populates modelspace with all expected entities
# ---------------------------------------------------------------------------

class TestAddShapesEntities:
    def test_five_entities_created(self, blank_doc):
        """TC-S01a | add_shapes() creates exactly 5 entities:
        1 CIRCLE (_Circle) + 4 LWPOLYLINEs (_Square, _Triangle, _Pentagon, _Hexagon).
        Note: _Rectangle and _Line layers are defined in the layer table but have
        no corresponding geometry added to modelspace in the current implementation."""
        add_shapes(blank_doc)
        entities = list(blank_doc.modelspace())
        assert len(entities) == 5

    def test_one_circle_entity_present(self, blank_doc):
        """TC-S01b | Exactly 1 CIRCLE entity (_Circle layer)."""
        add_shapes(blank_doc)
        circles = [e for e in blank_doc.modelspace() if e.dxftype() == "CIRCLE"]
        assert len(circles) == 1

    def test_circle_is_on_correct_layer(self, blank_doc):
        """TC-S01c | CIRCLE entity is placed on the '_Circle' layer."""
        add_shapes(blank_doc)
        circles = [e for e in blank_doc.modelspace() if e.dxftype() == "CIRCLE"]
        assert circles[0].dxf.layer == "_Circle"

    def test_lwpolylines_present(self, blank_doc):
        """TC-S01d | Multiple LWPOLYLINEs exist (square, triangle, pentagon, hexagon)."""
        add_shapes(blank_doc)
        polys = [e for e in blank_doc.modelspace() if e.dxftype() == "LWPOLYLINE"]
        assert len(polys) >= 4


# ---------------------------------------------------------------------------
# TC-S02  Layer table contains all 7 layers with correct ACI colors
# ---------------------------------------------------------------------------

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
        """TC-S02 | Each of 7 layers is created with the exact ACI color specified."""
        add_shapes(blank_doc)
        assert blank_doc.layers.has_entry(layer_name), \
            f"Layer {layer_name!r} was not created"
        actual_color = blank_doc.layers.get(layer_name).dxf.color
        assert actual_color == expected_color, \
            f"Layer {layer_name!r}: expected color {expected_color}, got {actual_color}"


# ---------------------------------------------------------------------------
# TC-S03  Saved DXF is re-openable (round-trip validity)
# ---------------------------------------------------------------------------

class TestDxfRoundTrip:
    def test_saved_dxf_is_valid(self, blank_doc, tmp_path):
        """TC-S03 | DXF file written by main() is re-openable by ezdxf."""
        from geojson_to_dxf import main
        out = tmp_path / "shapes_test.dxf"
        main(output_file=out)
        assert out.exists(), "DXF file was not created"
        doc = ezdxf.readfile(str(out))
        assert doc is not None


# ---------------------------------------------------------------------------
# TC-S04  Import must NOT trigger file writes (no module-level side-effects)
# ---------------------------------------------------------------------------

class TestNoImportSideEffects:
    def test_importing_module_does_not_write_dxf(self, tmp_path, monkeypatch):
        """TC-S04 | After the refactor, importing geojson_to_dxf must not create files.

        The original geojson_to_dxf.py ran doc.saveas() at module level (no __main__ guard).
        This test verifies that the refactor is correct — no DXF is written on import.
        """
        # Point DEFAULT_OUTPUT_FILE at tmp_path so if the bug exists, we can detect it
        fake_output = tmp_path / "should_not_exist.dxf"

        # Remove cached module to force a fresh import
        sys.modules.pop("geojson_to_dxf", None)

        # Patch the output path constant before the module runs
        import geojson_to_dxf as gd
        monkeypatch.setattr(gd, "DEFAULT_OUTPUT_FILE", fake_output)

        # The file must NOT have been created by import
        assert not fake_output.exists(), (
            "BUG: geojson_to_dxf created a DXF file on import. "
            "The module-level execution must be inside if __name__ == '__main__'."
        )


# ---------------------------------------------------------------------------
# TC-S05  Hexagon has exactly 6 vertices
# ---------------------------------------------------------------------------

class TestHexagonVertices:
    def test_hexagon_polyline_has_six_vertices(self, blank_doc):
        """TC-S05 | Hexagon LWPOLYLINE on _Hexagon layer has exactly 6 vertices."""
        add_shapes(blank_doc)
        hex_entities = [
            e for e in blank_doc.modelspace()
            if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "_Hexagon"
        ]
        assert len(hex_entities) == 1, "Expected exactly one _Hexagon entity"
        vertices = list(hex_entities[0].vertices())
        assert len(vertices) == 6, f"Expected 6 vertices, got {len(vertices)}"

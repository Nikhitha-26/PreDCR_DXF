"""
Unit tests for PreDCR_comp.py

Tests all pure-logic functions in isolation — no file I/O, no DXF output.

Groups:
    A  — get_predcr_standard(): name normalisation + rulebook mapping
    B  — get_points(): geometry coordinate extraction
    C  — load_geojson(): file loading + error handling
"""
import json
import pathlib
import tempfile

import pytest

from PreDCR_comp import get_predcr_standard, get_points, load_geojson


# ---------------------------------------------------------------------------
# GROUP A — get_predcr_standard
# ---------------------------------------------------------------------------

class TestGetPredcrStandard:
    """TC-U01 through TC-U10: name normalisation and rulebook lookup."""

    # --- Known PreDCR types ---

    def test_predefined_plot_boundary_exact(self):
        """TC-U01 | '_PlotBoundary' (exact prefixed name) → layer _PlotBoundary, color 6."""
        layer, color = get_predcr_standard("_PlotBoundary")
        assert layer == "_PlotBoundary"
        assert color == 6

    def test_predefined_plot_boundary_lowercase(self):
        """TC-U02 | 'plotboundary' (no underscore, lowercase) → same result."""
        layer, color = get_predcr_standard("plotboundary")
        assert layer == "_PlotBoundary"
        assert color == 6

    def test_predefined_road_uppercase(self):
        """TC-U03 | 'ROAD' (all-caps) → _Road, color 20."""
        layer, color = get_predcr_standard("ROAD")
        assert layer == "_Road"
        assert color == 20

    def test_predefined_road_trailing_whitespace(self):
        """TC-U04 | '_Road ' (trailing space) → _Road, color 20."""
        layer, color = get_predcr_standard("_Road ")
        assert layer == "_Road"
        assert color == 20

    def test_marginal_open_space_with_spaces(self):
        """TC-U05 | 'Marginal Open Space' (multi-word) → _MarginalOpenSpace, color 50."""
        layer, color = get_predcr_standard("Marginal Open Space")
        assert layer == "_MarginalOpenSpace"
        assert color == 50

    @pytest.mark.parametrize("raw_name, expected_layer, expected_color", [
        ("_PlotBoundary",      "_PlotBoundary",      6),
        ("_PropWork",          "_PropWork",           6),
        ("_Room",              "_Room",               230),
        ("_Window",            "_Window",             3),
        ("_Road",              "_Road",               20),
        ("_MarginalOpenSpace", "_MarginalOpenSpace",  50),
        ("_ResiFSI",           "_ResiFSI",            7),
        ("_CommFSI",           "_CommFSI",            7),
    ])
    def test_all_predcr_rules_exact_names(self, raw_name, expected_layer, expected_color):
        """TC-U06 | All 8 PREDCR_RULES entries return correct (layer, color) pairs."""
        layer, color = get_predcr_standard(raw_name)
        assert layer == expected_layer
        assert color == expected_color

    # --- Fallback / None / empty ---

    def test_none_returns_plot_boundary_fallback(self):
        """TC-U07 | None → fallback (_PlotBoundary, 6)."""
        layer, color = get_predcr_standard(None)
        assert layer == "_PlotBoundary"
        assert color == 6

    def test_empty_string_returns_plot_boundary_fallback(self):
        """TC-U08 | '' → fallback (_PlotBoundary, 6)."""
        layer, color = get_predcr_standard("")
        assert layer == "_PlotBoundary"
        assert color == 6

    # --- Unknown names: passthrough with underscore prefix ---

    def test_unknown_single_word_gets_underscore_prefix(self):
        """TC-U09 | 'Parking' (unknown) → _Parking, color 7."""
        layer, color = get_predcr_standard("Parking")
        assert layer == "_Parking"
        assert color == 7

    def test_unknown_multi_word_spaces_removed(self):
        """TC-U10 | 'Open Terrace' (unknown, two words) → _OpenTerrace, color 7."""
        layer, color = get_predcr_standard("Open Terrace")
        assert layer == "_OpenTerrace"
        assert color == 7


# ---------------------------------------------------------------------------
# GROUP B — get_points
# ---------------------------------------------------------------------------

class TestGetPoints:
    """TC-U11 through TC-U18: coordinate extraction from GeoJSON geometry dicts."""

    def _polygon(self, rings):
        return {"type": "Polygon", "coordinates": rings}

    def _linestring(self, coords):
        return {"type": "LineString", "coordinates": coords}

    def test_closed_polygon_returns_all_vertices(self):
        """TC-U11 | Closed Polygon (first == last) → all vertices as 2D tuples."""
        ring = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
        pts = get_points(self._polygon([ring]))
        assert pts == [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]

    def test_unclosed_polygon_prints_warning(self, capsys):
        """TC-U12 | Unclosed Polygon (first ≠ last) → Warning printed to stdout."""
        ring = [[0, 0], [10, 0], [10, 10], [0, 10]]  # missing closing vertex
        pts = get_points(self._polygon([ring]))
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert pts is not None  # still returns points despite warning

    def test_linestring_returns_2d_tuples(self):
        """TC-U13 | LineString → list of 2D tuples in original order."""
        pts = get_points(self._linestring([[4, 2], [8, 2]]))
        assert pts == [(4, 2), (8, 2)]

    def test_point_geometry_returns_none(self):
        """TC-U14 | Point geometry → None (unsupported for polyline drawing)."""
        geom = {"type": "Point", "coordinates": [15, 20]}
        assert get_points(geom) is None

    def test_none_geometry_returns_none(self):
        """TC-U15 | None geometry → None (guard against missing geometry)."""
        assert get_points(None) is None

    def test_polygon_empty_coordinates_returns_none(self):
        """TC-U16 | Polygon with empty coordinates list → None."""
        geom = {"type": "Polygon", "coordinates": []}
        assert get_points(geom) is None

    def test_polygon_with_interior_ring_uses_only_outer(self):
        """TC-U17 | Polygon with hole (2 rings) → only outer ring extracted."""
        outer = [[0, 0], [20, 0], [20, 20], [0, 20], [0, 0]]
        inner = [[5, 5], [15, 5], [15, 15], [5, 15], [5, 5]]
        pts = get_points(self._polygon([outer, inner]))
        assert pts == [(p[0], p[1]) for p in outer]
        assert len(pts) == 5  # inner ring not included

    def test_3d_coordinates_z_dropped_silently(self):
        """TC-U18 | 3D coords [lon, lat, elev] → Z silently dropped, no exception."""
        ring = [[72.87, 19.07, 14.0], [72.88, 19.07, 14.5], [72.88, 19.08, 15.0],
                [72.87, 19.08, 14.8], [72.87, 19.07, 14.0]]
        pts = get_points(self._polygon([ring]))
        assert pts is not None
        # Every returned point must be a 2-element tuple (no z)
        for pt in pts:
            assert len(pt) == 2, f"Expected 2D point, got {pt}"
        assert pts[0] == (72.87, 19.07)


# ---------------------------------------------------------------------------
# GROUP C — load_geojson
# ---------------------------------------------------------------------------

class TestLoadGeojson:
    """TC-U19 through TC-U21: file I/O and JSON parsing."""

    def test_valid_file_returns_dict(self, fixtures_dir):
        """TC-U19 | Valid GeoJSON file → returns Python dict with 'type' key."""
        result = load_geojson(fixtures_dir / "tc01_single_plot.geojson")
        assert isinstance(result, dict)
        assert result["type"] == "FeatureCollection"

    def test_nonexistent_file_raises_file_not_found(self, tmp_path):
        """TC-U20 | Non-existent path → raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_geojson(tmp_path / "ghost_file.geojson")

    def test_invalid_json_raises_json_decode_error(self, tmp_path):
        """TC-U21 | File with invalid JSON → raises json.JSONDecodeError."""
        bad_file = tmp_path / "bad.geojson"
        bad_file.write_text("{ this is not valid json }")
        with pytest.raises(json.JSONDecodeError):
            load_geojson(bad_file)

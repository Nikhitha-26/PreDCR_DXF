"""
Unit tests for PreDCR_comp.py

Tests all pure-logic functions in isolation — no file I/O, no DXF output.

Groups:
    A  — get_predcr_standard(): name normalisation + rulebook mapping
    B  — _to_2d_points(): coordinate extraction / cleanup
    C  — load_geojson(): file loading + error handling
"""
import json

import pytest

from PreDCR_comp import get_predcr_standard, load_geojson, _to_2d_points


class TestGetPredcrStandard:
    def test_predefined_plot_boundary_exact(self):
        layer, color = get_predcr_standard("_PlotBoundary")
        assert layer == "_PlotBoundary"
        assert color == 6

    def test_predefined_plot_boundary_lowercase(self):
        layer, color = get_predcr_standard("plotboundary")
        assert layer == "_PlotBoundary"
        assert color == 6

    def test_predefined_road_uppercase(self):
        layer, color = get_predcr_standard("ROAD")
        assert layer == "_Road"
        assert color == 20

    def test_predefined_road_trailing_whitespace(self):
        layer, color = get_predcr_standard("_Road ")
        assert layer == "_Road"
        assert color == 20

    def test_marginal_open_space_with_spaces(self):
        layer, color = get_predcr_standard("Marginal Open Space")
        assert layer == "_MarginalOpenSpace"
        assert color == 50

    @pytest.mark.parametrize(
        "raw_name, expected_layer, expected_color",
        [
            ("_PlotBoundary", "_PlotBoundary", 6),
            ("_PropWork", "_PropWork", 6),
            ("_Room", "_Room", 230),
            ("_Window", "_Window", 3),
            ("_Road", "_Road", 20),
            ("_MarginalOpenSpace", "_MarginalOpenSpace", 50),
            ("_ResiFSI", "_ResiFSI", 7),
            ("_CommFSI", "_CommFSI", 7),
        ],
    )
    def test_all_predcr_rules_exact_names(self, raw_name, expected_layer, expected_color):
        layer, color = get_predcr_standard(raw_name)
        assert layer == expected_layer
        assert color == expected_color

    def test_none_returns_plot_boundary_fallback(self):
        layer, color = get_predcr_standard(None)
        assert layer == "_PlotBoundary"
        assert color == 6

    def test_empty_string_returns_plot_boundary_fallback(self):
        layer, color = get_predcr_standard("")
        assert layer == "_PlotBoundary"
        assert color == 6

    def test_unknown_single_word_gets_underscore_prefix(self):
        layer, color = get_predcr_standard("Parking")
        assert layer == "_Parking"
        assert color == 7

    def test_unknown_multi_word_spaces_removed(self):
        layer, color = get_predcr_standard("Open Terrace")
        assert layer == "_OpenTerrace"
        assert color == 7

    def test_unknown_prefixed_name_does_not_double_prefix(self):
        layer, color = get_predcr_standard("_Parking")
        assert layer == "_Parking"
        assert color == 7

    def test_unknown_invalid_chars_are_sanitized(self):
        layer, color = get_predcr_standard("Road / Main")
        assert layer == "_Road_Main"
        assert color == 7


class TestTo2DPoints:
    def test_coordinate_list_returns_all_vertices(self):
        ring = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
        pts = _to_2d_points(ring)
        assert pts == [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]

    def test_linestring_coords_return_2d_tuples(self):
        pts = _to_2d_points([[4, 2], [8, 2]])
        assert pts == [(4, 2), (8, 2)]

    def test_none_input_raises_type_error(self):
        with pytest.raises(TypeError):
            _to_2d_points(None)

    def test_empty_coordinates_returns_empty_list(self):
        assert _to_2d_points([]) == []

    def test_invalid_short_coordinate_is_skipped(self):
        pts = _to_2d_points([[1, 2], [3], [4, 5]])
        assert pts == [(1, 2), (4, 5)]

    def test_non_numeric_coordinate_is_skipped(self):
        pts = _to_2d_points([[1, 2], ["x", 4], [5, 6]])
        assert pts == [(1, 2), (5, 6)]

    def test_3d_coordinates_z_dropped(self):
        ring = [
            [72.87, 19.07, 14.0],
            [72.88, 19.07, 14.5],
            [72.88, 19.08, 15.0],
            [72.87, 19.08, 14.8],
            [72.87, 19.07, 14.0],
        ]
        pts = _to_2d_points(ring)
        assert pts is not None
        for pt in pts:
            assert len(pt) == 2
        assert pts[0] == (72.87, 19.07)


class TestLoadGeojson:
    def test_valid_file_returns_dict(self, fixtures_dir):
        result = load_geojson(fixtures_dir / "tc01_single_plot.geojson")
        assert isinstance(result, dict)
        assert result["type"] == "FeatureCollection"

    def test_nonexistent_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_geojson(tmp_path / "ghost_file.geojson")

    def test_invalid_json_raises_json_decode_error(self, tmp_path):
        bad_file = tmp_path / "bad.geojson"
        bad_file.write_text("{ this is not valid json }")
        with pytest.raises(json.JSONDecodeError):
            load_geojson(bad_file)
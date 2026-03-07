"""Shared pytest fixtures for the PreDCR DXF test suite."""
import json
import pathlib
import pytest

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    """Returns the absolute path to the tests/fixtures/ directory."""
    return FIXTURES_DIR


def load_fixture(filename):
    """Helper: load a GeoJSON fixture by filename and return parsed dict."""
    with open(FIXTURES_DIR / filename) as f:
        return json.load(f)


@pytest.fixture
def tc01_data():
    return load_fixture("tc01_single_plot.geojson")


@pytest.fixture
def tc02_data():
    return load_fixture("tc02_full_floor_plan.geojson")


@pytest.fixture
def tc03_data():
    return load_fixture("tc03_unknown_layers.geojson")


@pytest.fixture
def tc04_data():
    return load_fixture("tc04_mixed_geometry.geojson")


@pytest.fixture
def tc05_data():
    return load_fixture("tc05_gps_mumbai.geojson")


@pytest.fixture
def tc06_data():
    return load_fixture("tc06_empty_collection.geojson")


@pytest.fixture
def tc07_data():
    return load_fixture("tc07_edge_cases.geojson")


@pytest.fixture
def tc08_data():
    return load_fixture("tc08_multipolygon.geojson")

"""Root conftest.py — adds src/ to sys.path so test modules can import PreDCR_comp and geojson_to_dxf."""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

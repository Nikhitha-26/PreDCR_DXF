# PreDCR GeoJSON-to-CAD Automation

**A Proof of Concept** that automatically converts web-based GeoJSON spatial data into **PreDCR-compliant AutoCAD DXF** drawings for municipal approval.

In urban planning and architecture, building plans must follow strict Pre-Development Control Regulation (PreDCR) guidelines for layer names, color codes, and geometry. This suite eliminates manual redrawing by converting GeoJSON features (plot boundaries, rooms, roads, windows, etc.) directly into correctly layered, color-coded DXF files ready for automated regulatory validation.

---

## Repository Structure
## Repository Structure

```text
PreDCR/
│
├── src/                         # Core Python Processing Scripts
│   ├── PreDCR_comp.py           # Strict Compliance Engine
│   └── geojson_to_dxf.py        # Flexible Translation Engine
│
├── data/                        # Test & Validation Payloads
│   ├── floor.geojson            # 2-BHK floor plan with rooms/windows
│   ├── site.geojson             # Plot boundary + road layout
│   ├── shapes.geojson           # Geometry stress-test cases
│   ├── output.dxf               # Sample PreDCR output
│   └── shapes_test.dxf          # Flexible engine test output
│
├── requirements.txt             # Project dependencies
└── README.md                    # Project documentation
```

## Technical Implementation

### A. Strict Compliance Engine (`PreDCR_comp.py`)
Designed for regulatory workflows. A rule-based system enforces municipal standards:

- **Mandatory Layer Routing** – Automatically maps features to official PreDCR layers (`_PlotBoundary`, `_PropWork`, `_Room`, `_Road`, `_Window`, etc.)
- **Standardized Coloring** – Enforces exact AutoCAD Color Index (ACI) values (e.g., Magenta 6 for boundaries, Color 20 for roads)
- **Smart String Normalization** – `" ROAD "`, `"_road"`, `"Road"` → all resolve to `_Road`

### B. Flexible Translation Engine (`geojson_to_dxf.py`)
For general drafting where strict PreDCR rules are not required. Respects properties defined in the GeoJSON:

- Reads `layer` and `color` from feature properties when available
- Auto-creates layers + assigns colors if missing
- Perfect for rapid prototyping and GIS-to-CAD workflows

---

## Geometry Mapping

| GeoJSON Feature | CAD Entity              | PreDCR Usage                          |
|-----------------|-------------------------|---------------------------------------|
| Polygon         | LWPOLYLINE (Closed)     | Plots, Rooms, Building Footprints     |
| LineString      | LWPOLYLINE (Open)       | Roads, Windows, Compound Walls        |
| Point           | CIRCLE                  | Trees, Columns, Reference Points      |

---

## Technical Evaluation & Limitations

- **ezdxf Learning Curve**: Moderate. Requires understanding LWPOLYLINE vs legacy POLYLINE, Modelspace/Paperspace, and entity attributes.
- **Curved Boundaries**: GeoJSON only supports straight segments. Curved boundaries must be approximated as multi-segment LineStrings/Polygons (faithfully recreated, but not converted to native CAD arcs).

---

## Backend API Integration (FastAPI Ready)

The core function accepts a Python dictionary directly — perfect for FastAPI:

```python
def generate_predcr_dxf(data: dict, output_file: str) -> None:
    """
    Generates a PreDCR-compliant DXF file from a GeoJSON dictionary.
    
    :param data: Parsed GeoJSON FeatureCollection (Python dict)
    :param output_file: Destination DXF path (or use BytesIO for HTTP response)
    """
```
## Getting Started

### Prerequisites
```bash
pip install -r requirements.txt 
# or
pip install ezdxf
```
### Running the Scripts

### PreDCR-compliant conversion
```bash
python src/PreDCR_comp.py data/floor.geojson data/floor.dxf
```
### Flexible/generic conversion
```bash
python src/geojson_to_dxf.py
```
---

## Future Roadmap

Automated area validation against minimum habitable standards
Web dashboard (upload GeoJSON → instant compliant DXF download)
Automatic hatching for layers like _MarginalOpenSpace and _Road


### Conclusion
This suite bridges the gap between modern web GIS tools and legacy municipal CAD requirements. It saves hours of manual drafting, reduces errors, and prepares spatial data for fully automated approval workflows.

import json
import ezdxf
import sys

# --- THE PREDCR RULEBOOK ---
# Maps the shape's name to the mandatory PreDCR layer and color.
PREDCR_RULES = {
    "plotboundary": {"layer": "_PlotBoundary", "color": 6},   # Magenta
    "propwork": {"layer": "_PropWork", "color": 6},           # Magenta
    "room": {"layer": "_Room", "color": 230},                 # Color 230
    "window": {"layer": "_Window", "color": 3},               # Green
    "road": {"layer": "_Road", "color": 20},                  # Color 20
    "marginalopenspace": {"layer": "_MarginalOpenSpace", "color": 50}, # Color 50
    "resifsi": {"layer": "_ResiFSI", "color": 7},
    "commfsi": {"layer": "_CommFSI", "color": 7}
}

def get_predcr_standard(shape_name):
    """Matches a shape name to the strict PreDCR standard."""
    if not shape_name:
        return "_PlotBoundary", 6  # Fallback to PlotBoundary if unnamed

    # Clean the name (e.g., "_Road", "road", "Road " all become "road")
    clean_name = shape_name.replace("_", "").replace(" ", "").lower()
    
    if clean_name in PREDCR_RULES:
        rule = PREDCR_RULES[clean_name]
        return rule["layer"], rule["color"]
    else:
        # If it's an unknown shape, keep its name but force standard color 7
        return f"_{shape_name.strip().replace(' ', '')}", 7

def load_geojson(path):
    with open(path, "r") as file:
        return json.load(file)

def get_points(geometry):
    if geometry is None:
        return None
        
    coords = geometry.get("coordinates", [])
    if not coords:
        return None

    geom_type = geometry.get("type")
    
    if geom_type == "Polygon":
        outer_ring = coords[0]
        if outer_ring[0] != outer_ring[-1]:
            print("Warning: found an unclosed polygon!")
        return [(pt[0], pt[1]) for pt in outer_ring]
        
    elif geom_type == "LineString":
        return [(pt[0], pt[1]) for pt in coords]
        
    return None

def generate_predcr_dxf(data, output_file):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    features = data.get("features", [])
    
    for feature in features:
        props = feature.get("properties", {})
        geometry = feature.get("geometry")
        
        if geometry is None:
            continue

        # 1. Look at what the GeoJSON claims this shape is
        raw_name = props.get("name") or props.get("layer") or "Unknown"
        
        # 2. THE SMART SORTER: Force it into the PreDCR standard
        target_layer, target_color = get_predcr_standard(raw_name)

        # Create the compliant layer exactly once
        if not doc.layers.has_entry(target_layer):
            doc.layers.add(name=target_layer, color=target_color)
            
        geom_type = geometry.get("type")

        # 3. Draw the geometry on the required layer
        if geom_type == "Polygon":
            points = get_points(geometry)
            if points:
                msp.add_lwpolyline(points, close=True, dxfattribs={"layer": target_layer})
                print(f"Added {raw_name} to layer {target_layer} (color {target_color})")

        elif geom_type == "LineString":
            points = get_points(geometry)
            if points:
                msp.add_lwpolyline(points, close=False, dxfattribs={"layer": target_layer})
                print(f"Added {raw_name} to layer {target_layer} (color {target_color})")

        elif geom_type == "Point":
            center = geometry.get("coordinates")
            msp.add_circle((center[0], center[1]), 1.0, dxfattribs={"layer": target_layer})
            print(f"Added {raw_name} to layer {target_layer} (color {target_color})")

    doc.saveas(output_file)
    print(f"\nDone! DXF saved to {output_file}")

def main():
    if len(sys.argv) >= 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    else:
        print("--- PreDCR Converter ---")
        input_file = input("Enter input GeoJSON path: ").strip()
        output_file = input("Enter output DXF path: ").strip()

    try:
        data = load_geojson(input_file)
        generate_predcr_dxf(data, output_file)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
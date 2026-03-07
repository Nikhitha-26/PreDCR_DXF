import math
import pathlib
import ezdxf

DEFAULT_OUTPUT_FILE = pathlib.Path(__file__).parent.parent / "data" / "shapes_test.dxf"


def add_shapes(doc):
    msp = doc.modelspace()

    layers = {
        "_Circle":    1,
        "_Square":    30,
        "_Triangle":  140,
        "_Pentagon":  4,
        "_Hexagon":   3,
        "_Rectangle": 5,
        "_Line":      8,
    }

    for name, color in layers.items():
        doc.layers.add(name=name, color=color)

    msp.add_circle(center=(0, 0), radius=0.5, dxfattribs={'layer': '_Circle'})

    sq = [(1.0, -1.0), (2.0, -1.0), (2.0,  0.0), (1.0,  0.0)]
    msp.add_lwpolyline(sq, close=True, dxfattribs={'layer': '_Square'})

    tri = [(3.5, -0.8), (4.5, -0.8), (4.0,  0.6)]
    msp.add_lwpolyline(tri, close=True, dxfattribs={'layer': '_Triangle'})

    pent = [(5.2, 0.0), (5.7, 0.4), (5.6, 1.0), (5.0, 1.0), (4.9, 0.4)]
    msp.add_lwpolyline(pent, close=True, dxfattribs={'layer': '_Pentagon'})

    hex_points = []
    cx, cy, r = 7.0, 0.0, 0.6
    for i in range(6):
        a = i * 60 * math.pi / 180
        hex_points.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    msp.add_lwpolyline(hex_points, close=True, dxfattribs={'layer': '_Hexagon'})

    print("Added shapes")


def main(output_file=None):
    if output_file is None:
        output_file = DEFAULT_OUTPUT_FILE
    doc = ezdxf.new("R2010")
    add_shapes(doc)
    doc.saveas(str(output_file))
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
"""Build the project page data (docs/data.js) straight from the CAD model.

Runs the export, re-checks the mesh, runs the test suite, projects hidden-line
drawing views with build123d and packs everything into one JS file that
docs/index.html reads. Re-run after changing any parameter:

    uv run python make_site.py
"""

import base64
import inspect
import json
import time
from datetime import date
from pathlib import Path

import numpy as np
import pytest
import trimesh
from build123d import CenterOf, GeomType

import bracket as b

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"

# name: (camera position, camera up). Coordinates come back in mm on the view plane.
VIEWS = {
    "front": ((0, -200, 0), (0, 0, 1)),     # looking along +Y: X right, Z up
    "top": ((0, 0, 200), (0, 1, 0)),        # looking down -Z: X right, Y up
    "right": ((200, 0, 0), (0, 0, 1)),      # looking along -X: Y across, Z up
    "iso": ((200, -200, 150), (0, 0, 1)),
}


def sample_edge(edge):
    """Polyline [x0, y0, x1, y1, ...] for one projected 2D edge."""
    if edge.geom_type == GeomType.LINE:
        n = 2
    else:
        n = max(12, int(edge.length / 0.4))
    pts = [edge.position_at(t) for t in np.linspace(0, 1, n)]
    return [round(v, 3) for p in pts for v in (p.X, p.Y)]


def project_views(part):
    views = {}
    for name, (origin, up) in VIEWS.items():
        visible, hidden = part.project_to_viewport(origin, viewport_up=up, look_at=(0, 0, 0))
        xs, ys = [], []
        vis = [sample_edge(e) for e in visible]
        hid = [sample_edge(e) for e in hidden]
        for line in vis + hid:
            xs += line[0::2]
            ys += line[1::2]
        views[name] = {
            "visible": vis,
            "hidden": hid,
            "bbox": [min(xs), min(ys), max(xs), max(ys)],
        }
    return views


def pack_mesh(mesh):
    """Indexed mesh as base64 typed arrays (float32 positions, uint32 indices)."""
    verts = np.asarray(mesh.vertices, dtype=np.float32)
    faces = np.asarray(mesh.faces, dtype=np.uint32)
    return {
        "positions": base64.b64encode(verts.tobytes()).decode(),
        "indices": base64.b64encode(faces.tobytes()).decode(),
        "triangles": int(len(faces)),
        "vertices": int(len(verts)),
    }


class Collector:
    """Minimal pytest plugin that records each test's outcome."""

    def __init__(self):
        self.results = []

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
            self.results.append({
                "name": report.nodeid.split("::")[-1],
                "outcome": report.outcome,
                "ms": round(report.duration * 1000, 1),
            })


def run_tests():
    collector = Collector()
    pytest.main(["-q", "-p", "no:cacheprovider", str(ROOT / "tests")], plugins=[collector])
    return collector.results


def parameter_block():
    """The parameter lines from bracket.py, as written in the source."""
    lines = (ROOT / "bracket.py").read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("# Parameters"))
    end = next(i for i in range(start, len(lines)) if not lines[i].strip())
    return "\n".join(lines[start:end])


def main():
    t0 = time.perf_counter()
    b.main()                                   # writes exports/bracket.step + .stl
    part = b.build_bracket()
    mesh = trimesh.load(b.EXPORTS / "bracket.stl")
    com = part.center(CenterOf.MASS)

    data = {
        "generated": date.today().isoformat(),
        "params": {
            "LEG": b.LEG, "WIDTH": b.WIDTH, "T": b.T, "HOLE_D": b.HOLE_D,
            "HOLE_POS": b.HOLE_POS, "FILLET_R": b.FILLET_R,
        },
        "results": {
            "volume_hand": b.analytic_volume(),
            "volume_brep": part.volume,
            "volume_stl": float(mesh.volume),
            "area_brep": part.area,
            "watertight": bool(mesh.is_watertight),
            "euler": int(mesh.euler_number),
            "extents": [float(v) for v in mesh.extents],
            "center_of_mass": [com.X, com.Y, com.Z],
            "faces_brep": len(part.faces()),
            "edges_brep": len(part.edges()),
        },
        "files": {
            name: (b.EXPORTS / name).stat().st_size for name in ("bracket.step", "bracket.stl")
        },
        "tests": run_tests(),
        "views": project_views(part),
        "mesh": pack_mesh(mesh),
        "code": {
            "params": parameter_block(),
            "build": inspect.getsource(b.build_bracket),
        },
    }

    DOCS.mkdir(exist_ok=True)
    out = DOCS / "data.js"
    out.write_text("window.BRACKET = " + json.dumps(data, separators=(",", ":")) + ";\n")
    passed = sum(t["outcome"] == "passed" for t in data["tests"])
    print(f"Tests        : {passed}/{len(data['tests'])} passed")
    print(f"Wrote {out} ({out.stat().st_size / 1024:.0f} kB) in {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()

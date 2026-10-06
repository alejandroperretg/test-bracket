# test-bracket

Parametric L-bracket in build123d: two 40 mm legs, 30 mm wide, 4 mm wall, one Ø5.5 mm (M5 clearance) hole per leg, 8 mm inner fillet.

```
uv run python bracket.py
```

Exports `exports/bracket.step` (CAD) and `exports/bracket.stl` (printing), then reloads the STL with trimesh to check volume and watertightness.

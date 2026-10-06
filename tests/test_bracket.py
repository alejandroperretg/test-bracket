"""Geometry checks: the CAD model and the exported mesh must match the hand calculation."""

import pytest
import trimesh
from build123d import export_stl

import bracket as b


@pytest.fixture(scope="module")
def part():
    return b.build_bracket()


@pytest.fixture(scope="module")
def mesh(part, tmp_path_factory):
    path = tmp_path_factory.mktemp("stl") / "bracket.stl"
    export_stl(part, str(path))
    return trimesh.load(path)


def test_brep_volume_matches_hand_calc(part):
    assert part.volume == pytest.approx(b.analytic_volume(), rel=1e-6)


def test_stl_volume_close_to_brep(part, mesh):
    assert mesh.volume == pytest.approx(part.volume, rel=1e-3)


def test_stl_is_watertight(mesh):
    assert mesh.is_watertight


def test_two_through_holes(mesh):
    # Euler characteristic V - E + F = 2 - 2g; genus g = number of through-holes
    assert mesh.euler_number == 2 - 2 * 2


def test_bounding_box(part):
    size = part.bounding_box().size
    assert (size.X, size.Y, size.Z) == pytest.approx((b.LEG, b.WIDTH, b.LEG))

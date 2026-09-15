import numpy as np
import pytest

from adit.analysis.sasa import RADII_SETS, radii_for, sasa, summary_lines as sasa_lines
from adit.analysis.voronoi import summary_lines as vor_lines, voronoi


def _sc(a=3.0, rep=3):
    pts = np.array([[i, j, k] for i in range(rep) for j in range(rep) for k in range(rep)], dtype=float) * a
    return pts, np.eye(3) * (a * rep)


def test_simple_cubic_voronoi_volume_is_the_cell_per_atom():
    pos, cell = _sc()
    res = voronoi(pos, cell)
    assert np.isfinite(res.volume).all()
    assert np.allclose(res.volume, 27.0, atol=1e-8)      # a^3
    assert np.all(res.faces == 6)
    assert res.volume.sum() == pytest.approx(np.linalg.det(cell), rel=1e-10)


def test_fcc_voronoi_has_twelve_faces():
    a = 4.0
    base = np.array([[0, 0, 0], [0, .5, .5], [.5, 0, .5], [.5, .5, 0]]) * a
    pos = np.vstack([base + np.array([i, j, k]) * a for i in range(2) for j in range(2) for k in range(2)])
    cell = np.eye(3) * (2 * a)
    res = voronoi(pos, cell, face_area_threshold_ang2=1e-6)
    assert np.all(res.faces == 12)
    assert res.volume.sum() == pytest.approx(np.linalg.det(cell), rel=1e-10)
    assert any("Voronoi" in line for line in vor_lines(res, np.linalg.det(cell)))


def test_voronoi_needs_enough_atoms():
    with pytest.raises(ValueError, match="4 原子以上"):
        voronoi(np.zeros((3, 3)))


def test_sasa_of_one_atom_is_the_sphere_area():
    r, probe = 1.7, 1.4
    res = sasa([[0.0, 0.0, 0.0]], [r], probe, n_points=4000)
    assert res.total_ang2 == pytest.approx(4 * np.pi * (r + probe) ** 2, rel=1e-12)


def test_two_overlapping_atoms_lose_area():
    r, probe = 1.7, 1.4
    alone = sasa([[0.0, 0.0, 0.0]], [r], probe, n_points=2000).total_ang2
    pair = sasa([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], [r, r], probe, n_points=2000)
    assert pair.total_ang2 < 2 * alone
    assert pair.per_atom_ang2[0] == pytest.approx(pair.per_atom_ang2[1], rel=5e-3)


def test_a_buried_atom_has_no_area():
    res = sasa([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], [5.0, 0.5], 0.0, n_points=500)
    assert res.per_atom_ang2[1] == 0.0


def test_radii_table_says_where_it_comes_from():
    assert "Bondi" in RADII_SETS["bondi"][0]
    assert np.allclose(radii_for(["O", "H", "H"], "bondi"), [1.52, 1.20, 1.20])
    with pytest.raises(ValueError, match="表にない元素"):
        radii_for(["Uuo"], "bondi")
    with pytest.raises(ValueError, match="半径の表"):
        radii_for(["O"], "made_up")


def test_sasa_errors_and_summary():
    with pytest.raises(ValueError, match="半径"):
        sasa([[0.0, 0.0, 0.0]], [1.0, 2.0])
    with pytest.raises(ValueError, match="プローブ半径"):
        sasa([[0.0, 0.0, 0.0]], [1.0], -1.0)
    res = sasa([[0.0, 0.0, 0.0]], [1.5], 1.4, n_points=100, radii_source="Bondi")
    assert any("Bondi" in line for line in sasa_lines(res))

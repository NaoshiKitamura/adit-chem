import numpy as np
import pytest

from adit.analysis.displacement import displacements, local_strain, summary_lines


def _fcc(a=4.0, rep=3):
    base = np.array([[0, 0, 0], [0, .5, .5], [.5, 0, .5], [.5, .5, 0]]) * a
    pts = [base + np.array([i, j, k]) * a for i in range(rep) for j in range(rep) for k in range(rep)]
    return np.vstack(pts), np.eye(3) * (a * rep)


def test_uniform_stretch_gives_the_expected_strain():
    pos, cell = _fcc()
    lam = 1.02
    F_true = np.diag([lam, 1.0, 1.0])
    new = pos @ F_true.T
    ls = local_strain(pos, new, cutoff_ang=3.0, cell=cell, cell_current=cell @ F_true.T)
    ok = ls.neighbors >= 3
    assert ok.all()
    expected = 0.5 * (lam ** 2 - 1.0)
    assert np.allclose(ls.strain[:, 0, 0], expected, atol=1e-8)
    assert np.allclose(ls.strain[:, 1, 1], 0.0, atol=1e-8)
    assert np.allclose(ls.residual, 0.0, atol=1e-8)


def test_simple_shear_is_shear_not_volume():
    pos, cell = _fcc()
    gamma = 0.01
    F_true = np.array([[1.0, gamma, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    ls = local_strain(pos, pos @ F_true.T, cutoff_ang=3.0, cell=cell, cell_current=cell @ F_true.T)
    assert ls.shear.max() > 0
    assert abs(ls.volumetric).max() == pytest.approx(gamma ** 2 / 6.0, rel=1e-6)


def test_no_deformation_gives_zero():
    pos, cell = _fcc()
    ls = local_strain(pos, pos.copy(), cutoff_ang=3.0, cell=cell)
    assert np.allclose(ls.strain, 0.0, atol=1e-10)
    assert np.allclose(ls.shear, 0.0, atol=1e-10)


def test_displacement_uses_the_minimum_image():
    cell = np.eye(3) * 10.0
    a = np.array([[0.1, 0.0, 0.0]])
    b = np.array([[9.9, 0.0, 0.0]])
    assert np.allclose(displacements(a, b, cell), [[-0.2, 0.0, 0.0]])
    assert np.allclose(displacements(a, b), [[9.8, 0.0, 0.0]])


def test_errors():
    pos, cell = _fcc(rep=2)
    with pytest.raises(ValueError, match="原子数が違います"):
        displacements(pos, pos[:-1])
    with pytest.raises(ValueError, match="カットオフ"):
        local_strain(pos, pos, 0.0, cell)


def test_summary_mentions_the_correspondence():
    pos, cell = _fcc(rep=2)
    u = displacements(pos, pos * 1.01)
    lines = summary_lines(u, local_strain(pos, pos * 1.01, 3.0, cell))
    assert any("対応" in line for line in lines)

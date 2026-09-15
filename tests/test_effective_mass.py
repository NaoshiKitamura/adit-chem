import numpy as np
import pytest

from adit.analysis.effective_mass import HBAR_SQ_OVER_ME_EV_ANG2, at_band_edges, effective_mass, summary_lines


def test_free_electron_gives_unit_mass():
    k = np.linspace(-0.5, 0.5, 101)
    e = (HBAR_SQ_OVER_ME_EV_ANG2 / 2.0) * k ** 2       # E = hbar^2 k^2 / (2 m_e)
    res = effective_mass(k, e[:, None], 0, 50, 5)
    assert res.m_over_me == pytest.approx(1.0, rel=1e-10)
    assert res.r_squared == pytest.approx(1.0, abs=1e-12)


def test_heavier_band_gives_larger_mass():
    k = np.linspace(-0.5, 0.5, 101)
    e = (HBAR_SQ_OVER_ME_EV_ANG2 / (2.0 * 3.5)) * k ** 2
    assert effective_mass(k, e[:, None], 0, 50, 7).m_over_me == pytest.approx(3.5, rel=1e-10)


def test_hole_mass_is_negative_for_a_downward_band():
    k = np.linspace(-0.5, 0.5, 101)
    e = -(HBAR_SQ_OVER_ME_EV_ANG2 / 2.0) * k ** 2
    assert effective_mass(k, e[:, None], 0, 50, 5, "hole").m_over_me == pytest.approx(-1.0, rel=1e-10)


def test_band_edges_finds_both_carriers():
    k = np.linspace(0.0, 1.0, 51)
    x = k - 0.5
    valence = -1.0 - (HBAR_SQ_OVER_ME_EV_ANG2 / 2.0) * x ** 2
    conduction = 1.0 + (HBAR_SQ_OVER_ME_EV_ANG2 / (2 * 0.2)) * x ** 2
    e = np.column_stack([valence, conduction])
    masses = at_band_edges(k, e, fermi_ev=0.0)
    kinds = {m.kind: m for m in masses}
    assert kinds["hole"].m_over_me == pytest.approx(-1.0, rel=1e-9)
    assert kinds["electron"].m_over_me == pytest.approx(0.2, rel=1e-9)
    assert any("m*/m_e" in line for line in summary_lines(masses))


def test_metal_returns_nothing():
    k = np.linspace(0, 1, 21)
    e = np.column_stack([k, k + 0.1])
    assert at_band_edges(k, e, fermi_ev=0.5) == []


def test_refuses_a_window_that_crosses_a_path_break():
    k = np.array([0.0, 0.1, 0.2, 0.2, 0.3, 0.4])
    e = (k ** 2)[:, None]
    with pytest.raises(ValueError, match="単調"):
        effective_mass(k, e, 0, 2, 5)


def test_refuses_when_there_is_no_room():
    k = np.linspace(0, 1, 5)
    with pytest.raises(ValueError, match="点が取れません"):
        effective_mass(k, (k ** 2)[:, None], 0, 0, 5)

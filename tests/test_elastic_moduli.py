
import numpy as np
import pytest

from adit.analysis.elastic_moduli import ElasticModuliError, from_cij, summary_lines


def cubic(c11: float, c12: float, c44: float) -> np.ndarray:
    c = np.zeros((6, 6))
    c[0, 0] = c[1, 1] = c[2, 2] = c11
    c[0, 1] = c[1, 0] = c[0, 2] = c[2, 0] = c[1, 2] = c[2, 1] = c12
    c[3, 3] = c[4, 4] = c[5, 5] = c44
    return c


def test_diamond_matches_the_textbook_values():
    m = from_cij(cubic(1079.0, 124.0, 578.0))
    assert m.k_hill == pytest.approx(442, abs=2)
    assert m.g_hill == pytest.approx(535, abs=5)
    assert m.young == pytest.approx(1140, rel=0.01)
    assert 0.0 < m.poisson < 0.1
    assert m.stable is True


def test_bulk_modulus_of_a_cubic_crystal_has_the_closed_form():
    c11, c12 = 300.0, 100.0
    m = from_cij(cubic(c11, c12, 90.0))
    expected = (c11 + 2 * c12) / 3
    assert m.k_voigt == pytest.approx(expected) and m.k_reuss == pytest.approx(expected)
    assert m.k_hill == pytest.approx(expected)


def test_voigt_and_reuss_bound_the_hill_average():
    rng = np.random.default_rng(0)
    c = cubic(250.0, 120.0, 80.0) + rng.normal(0, 2.0, size=(6, 6))
    m = from_cij(0.5 * (c + c.T))
    assert min(m.g_voigt, m.g_reuss) <= m.g_hill <= max(m.g_voigt, m.g_reuss)
    assert min(m.k_voigt, m.k_reuss) <= m.k_hill <= max(m.k_voigt, m.k_reuss)


def test_unstable_matrix_is_reported_as_a_fact_not_a_verdict():
    m = from_cij(cubic(100.0, 200.0, 50.0))
    assert m.stable is False
    lines = summary_lines(m)
    assert any("Born" in line or "安定条件" in line for line in lines)
    assert not any("悪い" in line or "bad" in line for line in lines)


def test_bad_input_is_refused():
    with pytest.raises(ElasticModuliError, match="6×6|6x6"):
        from_cij(np.zeros((3, 3)))
    with pytest.raises(ElasticModuliError, match="数でない|non-finite"):
        from_cij(np.full((6, 6), np.nan))
    with pytest.raises(ElasticModuliError, match="逆行列|singular"):
        from_cij(np.zeros((6, 6)))


def test_gap_details_finds_the_k_points():
    from adit.analysis.bands import gap_details

    valence = np.array([-0.1, -0.5, -0.8, -0.6, -0.3])
    conduction = np.array([2.0, 1.5, 1.2, 0.9, 1.8])
    e = np.column_stack([valence, conduction])
    got = gap_details(e, fermi_ev=0.0, kpts_frac=np.zeros((5, 3)), labels={0: "G", 3: "X"})
    assert got["gap_ev"] == pytest.approx(1.0)          # 0.9 − (−0.1)
    assert got["vbm_kpoint_index"] == 0 and got["cbm_kpoint_index"] == 3
    assert got["vbm_label"] == "G" and got["cbm_label"] == "X"
    assert got["direct"] is False
    assert got["direct_gap_ev"] == pytest.approx(1.5)
    assert got["direct_gap_kpoint_index"] == 3


def test_gap_details_marks_a_direct_gap():
    from adit.analysis.bands import gap_details

    e = np.column_stack([np.array([-0.2, -0.9, -1.1]), np.array([1.0, 2.0, 2.5])])
    got = gap_details(e, fermi_ev=0.0)
    assert got["direct"] is True and got["gap_ev"] == pytest.approx(1.2)


def test_gap_details_returns_none_for_a_metal():
    from adit.analysis.bands import gap_details

    e = np.column_stack([np.array([-1.0, -1.0]), np.array([-0.5, -0.5])])
    assert gap_details(e, fermi_ev=0.0) is None
    assert gap_details(e, fermi_ev=None) is None

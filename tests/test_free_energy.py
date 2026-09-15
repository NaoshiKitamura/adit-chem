import numpy as np
import pytest

from adit.analysis.free_energy import UNITS, free_energy_surface, read_colvar, summary_lines


def test_harmonic_distribution_returns_the_parabola():
    rng = np.random.default_rng(0)
    T, k = 300.0, 2.0          # A(x) = k x^2 / 2 [kJ/mol]
    kt = UNITS["kJ/mol"] * T
    sigma = np.sqrt(kt / k)
    x = rng.normal(0.0, sigma, 400000)
    fes = free_energy_surface(x, T, bins=40, ranges=(-3 * sigma, 3 * sigma))
    c = fes.centers[0]
    keep = np.isfinite(fes.free_energy) & (np.abs(c) < 2 * sigma)
    fit = np.polyfit(c[keep], fes.free_energy[keep], 2)
    assert 2 * fit[0] == pytest.approx(k, rel=0.05)      # 2a = k


def test_minimum_is_zero_and_empty_bins_are_infinite():
    x = np.concatenate([np.zeros(100), np.full(100, 5.0)])
    fes = free_energy_surface(x, 300.0, bins=10, ranges=(0.0, 5.0))
    assert fes.free_energy[np.isfinite(fes.free_energy)].min() == 0.0
    assert np.isinf(fes.free_energy).any()


def test_two_dimensional_surface():
    rng = np.random.default_rng(1)
    v = rng.normal(size=(20000, 2))
    fes = free_energy_surface(v, 300.0, bins=20)
    assert fes.free_energy.shape == (20, 20)
    assert len(fes.centers) == 2
    assert any("2 次元" in line for line in summary_lines(fes))


def test_weights_change_the_surface():
    x = np.concatenate([np.zeros(100), np.ones(100)])
    plain = free_energy_surface(x, 300.0, bins=2, ranges=(-0.5, 1.5))
    weighted = free_energy_surface(x, 300.0, bins=2, ranges=(-0.5, 1.5),
                                   weights=np.concatenate([np.ones(100), np.full(100, 3.0)]))
    assert plain.free_energy[1] == pytest.approx(0.0)
    assert weighted.free_energy[0] > 0.0


def test_errors():
    with pytest.raises(ValueError, match="単位"):
        free_energy_surface([1.0, 2.0], 300.0, unit="hartree")
    with pytest.raises(ValueError, match="温度"):
        free_energy_surface([1.0, 2.0], 0.0)
    with pytest.raises(ValueError, match="重み"):
        free_energy_surface([1.0, 2.0], 300.0, weights=[1.0])


def test_reads_a_plumed_colvar(tmp_path):
    p = tmp_path / "COLVAR"
    p.write_text("#! FIELDS time d1 d2\n0.0 1.0 2.0\n1.0 1.5 2.5\n", encoding="utf-8")
    names, data = read_colvar(p)
    assert names == ["time", "d1", "d2"]
    assert data.shape == (2, 3)
    with pytest.raises(ValueError, match="数値の行"):
        (tmp_path / "empty").write_text("#! FIELDS a\n", encoding="utf-8")
        read_colvar(tmp_path / "empty")


def test_two_dimensional_distribution_integrates_to_one():
    from adit.analysis.free_energy import distribution_2d

    rng = np.random.default_rng(3)
    d = distribution_2d(rng.normal(size=5000), rng.normal(size=5000), bins=25)
    dx = d.x_centers[1] - d.x_centers[0]
    dy = d.y_centers[1] - d.y_centers[0]
    assert (d.density * dx * dy).sum() == pytest.approx(1.0, rel=1e-10)
    assert d.counts.sum() == 5000


def test_two_dimensional_distribution_checks_lengths():
    from adit.analysis.free_energy import distribution_2d

    with pytest.raises(ValueError, match="長さが違います"):
        distribution_2d([1.0, 2.0], [1.0])

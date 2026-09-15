from pathlib import Path

import numpy as np
import pytest

from adit.analysis.optical import Optical, read_epsilon, summary_lines

DATA = Path(__file__).parent / "data"


def test_reads_the_real_epsilon_output():
    op = read_epsilon(DATA, "si")
    assert op.energy_ev.size == op.eps1.shape[0] == op.eps2.shape[0]
    assert op.eps1.shape[1] == 3
    assert op.energy_ev[0] == pytest.approx(0.0)
    assert np.allclose(op.eps1[:, 0], op.eps1[:, 2], rtol=0, atol=1e-3)


def test_eels_matches_the_value_quantum_espresso_wrote():
    op = read_epsilon(DATA, "si")
    ref = np.loadtxt(DATA / "eels_si.dat", comments="#")
    assert np.allclose(op.eels(), ref[:, 1:4], rtol=1e-6, atol=1e-9)


def test_refractive_index_reproduces_the_dielectric_function():
    op = read_epsilon(DATA, "si")
    n, k = op.refractive_index(), op.extinction()
    assert np.allclose(n ** 2 - k ** 2, op.eps1, rtol=1e-8, atol=1e-8)
    assert np.allclose(2 * n * k, op.eps2, rtol=1e-6, atol=1e-8)


def test_absorption_of_a_known_medium():
    e = np.array([1.0])
    op = Optical(e, np.zeros((1, 3)), np.full((1, 3), 2.0))
    assert op.refractive_index()[0, 0] == pytest.approx(1.0)
    expected = 2.0 * (1.0 / 6.582119569e-16) / 2.99792458e10
    assert op.absorption_cm()[0, 0] == pytest.approx(expected, rel=1e-12)
    assert op.reflectivity()[0, 0] == pytest.approx(1.0 / 5.0)     # ((0)^2+1)/((2)^2+1)


def test_transparent_medium_has_no_absorption():
    op = Optical(np.array([2.0]), np.full((1, 3), 4.0), np.zeros((1, 3)))
    assert op.absorption_cm()[0, 0] == pytest.approx(0.0)
    assert op.refractive_index()[0, 0] == pytest.approx(2.0)
    assert op.reflectivity()[0, 0] == pytest.approx((1 / 3) ** 2)
    assert op.eels()[0, 0] == pytest.approx(0.0)


def test_missing_files_say_what_to_run(tmp_path):
    with pytest.raises(FileNotFoundError, match="epsilon.x"):
        read_epsilon(tmp_path)


def test_summary_mentions_the_static_value():
    lines = summary_lines(read_epsilon(DATA, "si"))
    assert any("静的誘電率" in line for line in lines)

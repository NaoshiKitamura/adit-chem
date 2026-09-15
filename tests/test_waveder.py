from pathlib import Path

import numpy as np
import pytest

from adit.analysis.waveder import EDEPS, Waveder, dielectric_imag, read_waveder

DATA = Path(__file__).parent / "data" / "WAVEDER.gz"


def test_reads_the_real_binary():
    wd = read_waveder(DATA)
    assert wd.cder.shape == (36, 8, 56, 1, 3)
    assert wd.cder.dtype == np.complex64
    assert np.isfinite(wd.cder).all()
    assert wd.n_bands == 36 and wd.n_kpoints == 56


def test_matches_pymatgen_when_it_is_installed():
    outputs = pytest.importorskip("pymatgen.io.vasp.outputs")
    import gzip
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        plain = Path(tmp) / "WAVEDER"
        plain.write_bytes(gzip.decompress(DATA.read_bytes()))
        ref = outputs.Waveder.from_binary(plain)
    assert np.array_equal(read_waveder(DATA).cder, ref.cder)


def test_rejects_a_file_that_is_not_a_waveder(tmp_path):
    bad = tmp_path / "WAVEDER"
    bad.write_bytes(b"not a fortran record at all")
    with pytest.raises(ValueError):
        read_waveder(bad)


def _two_band_case():
    cder = np.zeros((2, 2, 1, 1, 3), dtype=complex)
    cder[0, 1, 0, 0, 0] = 0.5
    return Waveder(cder), np.array([[0.0, 2.0]]), np.array([[1.0, 0.0]]), np.array([1.0])


def test_two_band_case_has_the_expected_area_and_position():
    wd, e, f, w = _two_band_case()
    grid = np.linspace(0, 6, 1201)
    eps2 = dielectric_imag(wd, e, f, w, volume_ang3=100.0, grid_ev=grid, broadening_ev=0.05)
    peak = int(np.argmax(eps2[:, 0]))
    assert grid[peak] == pytest.approx(2.0, abs=0.01)
    assert eps2[:, 1].max() == 0.0 and eps2[:, 2].max() == 0.0
    area = np.trapezoid(eps2[:, 0], grid)
    assert area == pytest.approx(EDEPS * np.pi / 100.0 * 2 * 0.25, rel=1e-6)


def test_rejects_inconsistent_input():
    wd, e, f, w = _two_band_case()
    grid = np.linspace(0, 6, 61)
    with pytest.raises(ValueError, match="形が違います"):
        dielectric_imag(wd, e, f[:, :1], w, 100.0, grid, 0.1)
    with pytest.raises(ValueError, match="重み"):
        dielectric_imag(wd, e, f, np.array([1.0, 1.0]), 100.0, grid, 0.1)
    with pytest.raises(ValueError, match="広がりの幅"):
        dielectric_imag(wd, e, f, w, 100.0, grid, 0.0)


import numpy as np
import pytest
from ase.geometry import find_mic

from adit.analysis.compute import _mic_step

SKEWED = np.array([[0.0033743628045296977, 8.872103423712332, 0.0038395273475024215],
                   [7.67521516765734, 0.003709218851103653, 21.742332658408166],
                   [4.420643375647734, 0.06666271499818877, -0.03841208653729757]])
CUBIC = np.diag([12.0, 11.0, 13.0])


@pytest.mark.parametrize("cell", [CUBIC, SKEWED])
def test_minimum_image_matches_ase(cell):
    rng = np.random.default_rng(20260913)
    steps = (rng.random((300, 3)) - 0.5) @ cell * 1.5
    ours = _mic_step(steps, cell)
    theirs, _ = find_mic(steps, cell, pbc=True)
    assert np.allclose(np.linalg.norm(ours, axis=1), np.linalg.norm(theirs, axis=1), atol=1e-9)


def test_naive_rounding_would_be_wrong_on_the_skewed_cell():
    rng = np.random.default_rng(1)
    steps = (rng.random((300, 3)) - 0.5) @ SKEWED
    frac = np.linalg.solve(SKEWED.T, steps.T).T
    naive = np.linalg.norm((frac - np.round(frac)) @ SKEWED, axis=1)
    ours = np.linalg.norm(_mic_step(steps, SKEWED), axis=1)
    assert (naive > ours + 1e-6).sum() > 30
    assert np.all(ours <= naive + 1e-9)

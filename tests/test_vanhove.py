
import numpy as np
import pytest

from adit.analysis.vanhove import (VanHoveError, cell_half_width, default_taus, fit_gaussian_d, mic, notes,
                                    van_hove_self)

CELL = np.diag([12.0, 11.0, 13.0])
SKEWED = np.array([[0.0033743628045296977, 8.872103423712332, 0.0038395273475024215],
                   [7.67521516765734, 0.003709218851103653, 21.742332658408166],
                   [4.420643375647734, 0.06666271499818877, -0.03841208653729757]])


def random_walk(frames=200, natoms=30, d_true=2.0e-4, dt=10.0, cell=CELL, seed=0):
    rng = np.random.default_rng(seed)
    start = rng.random((natoms, 3)) @ cell
    steps = rng.normal(0.0, np.sqrt(2 * d_true * dt), size=(frames - 1, natoms, 3))
    return np.concatenate([start[None, :, :], start[None, :, :] + np.cumsum(steps, axis=0)], axis=0)


def wrap(pos, cell):
    frac = np.linalg.solve(np.asarray(cell).T, pos.reshape(-1, 3).T).T % 1.0
    return (frac @ cell).reshape(pos.shape)


def test_recovers_a_known_diffusion_coefficient():
    pos = random_walk()
    res = van_hove_self(wrap(pos, CELL), CELL, [1, 2, 5, 10], dt_fs=10.0)
    assert np.allclose(res.d_direct, 2.0e-4, rtol=0.15)
    assert np.allclose(res.d_fit, res.d_direct, rtol=0.2)
    assert np.all(np.abs(res.alpha2) < 0.2)


def test_fit_and_moment_agree_for_a_gaussian():
    rng = np.random.default_rng(3)
    d_true, tau = 1.0e-4, 500.0
    r = np.linalg.norm(rng.normal(0.0, np.sqrt(2 * d_true * tau), size=(20000, 3)), axis=1)
    counts, edges = np.histogram(r, bins="fd")
    centers = (edges[:-1] + edges[1:]) / 2
    fitted = fit_gaussian_d(centers, counts, tau, 1e-4)
    direct = float((r ** 2).mean() / (6 * tau))
    assert fitted == pytest.approx(direct, rel=0.05)
    assert fitted == pytest.approx(d_true, rel=0.05)


def test_minimum_image_truncation_is_reported():
    small = np.diag([6.0, 6.0, 6.0])
    pos = random_walk(frames=200, natoms=20, d_true=2.0e-3, cell=small)
    res = van_hove_self(wrap(pos, small), small, [1, 5, 20, 80], dt_fs=10.0)
    assert res.half_width_A == pytest.approx(3.0)
    assert res.truncated_from is not None and res.near_cap_fraction > 0.01
    assert any("頭打ち" in n or "biased low" in n for n in notes(res))
    free = van_hove_self(pos, small, [80], dt_fs=10.0, displacement="unwrapped")
    capped = van_hove_self(wrap(pos, small), small, [80], dt_fs=10.0, displacement="mic")
    assert free.d_direct[0] > capped.d_direct[0] * 1.2


def test_skewed_cell_uses_27_images():
    rng = np.random.default_rng(5)
    steps = (rng.random((200, 3)) - 0.5) @ SKEWED
    ours = np.linalg.norm(mic(steps, SKEWED), axis=1)
    frac = np.linalg.solve(SKEWED.T, steps.T).T
    naive = np.linalg.norm((frac - np.round(frac)) @ SKEWED, axis=1)
    assert np.all(ours <= naive + 1e-9) and (naive > ours + 1e-6).sum() > 10
    assert cell_half_width(SKEWED) == pytest.approx(2.09, abs=0.05)


def test_chunking_does_not_change_the_answer():
    pos = wrap(random_walk(frames=120, natoms=10), CELL)
    whole = van_hove_self(pos, CELL, [3, 7], dt_fs=10.0, chunk_bytes=64 * 2 ** 20)
    small = van_hove_self(pos, CELL, [3, 7], dt_fs=10.0, chunk_bytes=1024)
    assert np.allclose(whole.d_direct, small.d_direct, rtol=1e-12)
    assert np.allclose(whole.alpha2, small.alpha2, rtol=1e-12)


def test_default_taus_stay_in_the_first_half():
    taus = default_taus(1000, count=50)
    assert taus[0] >= 1 and taus[-1] <= 500 and len(taus) == 50


def test_bad_input_is_refused():
    with pytest.raises(VanHoveError, match="フレーム|frames"):
        van_hove_self(np.zeros((1, 5, 3)), CELL, [1], dt_fs=10.0)
    with pytest.raises(VanHoveError, match="mic|unwrapped"):
        van_hove_self(np.zeros((5, 5, 3)), CELL, [1], dt_fs=10.0, displacement="x")
    with pytest.raises(VanHoveError, match="遅れ時間|lag"):
        van_hove_self(np.zeros((5, 5, 3)), CELL, [99], dt_fs=10.0)


def test_per_atom_d_matches_the_average():
    from adit.analysis.compute import msd_fft, msd_per_atom, diffusion_fit, fit_range_fs

    pos = random_walk(frames=200, natoms=30, seed=7)
    rel = pos - pos[0]
    each = msd_per_atom(rel, dt_fs=10.0, dim=3)
    values = [v for v in each["d_cm2_s"] if v is not None]
    assert len(values) == 30
    t = np.arange(len(rel), dtype=float) * 10.0
    whole = diffusion_fit(t, msd_fft(rel), fit_range_fs(t, None), 3)
    assert np.mean(values) == pytest.approx(whole, rel=0.15)
    single = [float(((rel[-1, a] - rel[0, a]) ** 2).sum() / (6 * t[-1]) * 1e-1) for a in range(30)]
    assert np.std(values) / np.mean(values) < np.std(single) / np.mean(single)


def test_per_atom_chunking_does_not_change_the_answer():
    from adit.analysis.compute import msd_per_atom

    pos = random_walk(frames=120, natoms=12, seed=11)
    rel = pos - pos[0]
    a = msd_per_atom(rel, dt_fs=10.0, dim=3)
    b = msd_per_atom(rel, dt_fs=10.0, dim=3, chunk_bytes=4096)
    assert np.allclose(a["msd_A2"], b["msd_A2"], rtol=1e-10, atol=1e-12)

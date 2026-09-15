import numpy as np
import pytest

from adit.analysis.frames_pca import kmeans, pca, summary_lines


def _one_mode(n_frames=60, n_atoms=5, amp=0.5):
    base = np.array([[0.0, 0.0, 0.0], [3.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 3.0], [3.0, 3.0, 0.0]])[:n_atoms]
    t = np.linspace(0, 1, n_frames)
    frames = np.repeat(base[None, :, :], n_frames, axis=0).copy()
    frames[:, 0, 0] += amp * np.sin(2 * np.pi * t)
    return frames


def test_one_mode_is_captured_by_the_first_component():
    res = pca(_one_mode(), n_components=3, align=False)
    assert res.explained[0] > 0.99
    assert res.explained.sum() == pytest.approx(1.0, abs=0.01)
    assert res.projections.shape == (60, 3)


def test_alignment_removes_a_rigid_rotation():
    frames = _one_mode(amp=0.0)
    angle = np.linspace(0, 1.0, frames.shape[0])
    rotated = frames.copy()
    for i, a in enumerate(angle):
        r = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
        rotated[i] = frames[i] @ r.T
    without = pca(rotated, n_components=2, align=False)
    with_align = pca(rotated, n_components=2, align=True)
    assert with_align.variance[0] < without.variance[0] * 1e-6


def test_kmeans_finds_two_given_groups():
    pts = np.vstack([np.zeros((20, 2)), np.full((30, 2), 10.0)])
    cl = kmeans(pts, 2, seed=1)
    assert sorted(cl.sizes.tolist()) == [20, 30]
    assert cl.inertia == pytest.approx(0.0, abs=1e-12)
    assert set(cl.representative.tolist()) <= set(range(50))


def test_kmeans_checks_its_input():
    with pytest.raises(ValueError, match="群の数"):
        kmeans(np.zeros((4, 2)), 5)
    with pytest.raises(ValueError, match="points"):
        kmeans(np.zeros(4), 2)


def test_pca_checks_its_input():
    with pytest.raises(ValueError, match="coords"):
        pca(np.zeros((3, 4)))
    with pytest.raises(ValueError, match="3 フレーム以上"):
        pca(np.zeros((2, 5, 3)))


def test_summary_says_the_group_count_is_the_users():
    res = pca(_one_mode(), n_components=2, align=False)
    cl = kmeans(res.projections, 2, seed=0)
    lines = summary_lines(res, cl)
    assert any("寄与率" in line for line in lines)
    assert any("利用者が決めた値" in line for line in lines)

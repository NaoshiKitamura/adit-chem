
import numpy as np
import pytest
from ase import Atoms
from ase.build import bulk, molecule

from adit.analysis.geometry_series import radius_of_gyration
from adit.analysis.hbond import HydrogenBondError, count_frame, count_series, criteria_note
from adit.analysis.local_order import (LocalOrderError, angle_distribution, centrosymmetry, clusters, coordination,
                                        steinhardt, structure_factor)
from adit.analysis.volumetric import DensityGrid, VolumetricError, difference, macroscopic_average


def test_fcc_coordination_is_twelve():
    fcc = bulk("Cu", "fcc", a=3.61, cubic=True) * (2, 2, 2)
    got = coordination(fcc, 3.0)
    assert got["mean"] == pytest.approx(12.0)
    assert "既定値を持ちません" in got["note"] or "no default" in got["note"]


def test_centrosymmetry_is_zero_for_a_perfect_lattice():
    fcc = bulk("Cu", "fcc", a=3.61, cubic=True) * (2, 2, 2)
    values = centrosymmetry(fcc, 12)["centrosymmetry_A2"]
    assert max(values) == pytest.approx(0.0, abs=1e-8)
    moved = fcc.copy(); moved.positions[0] += [0.4, 0.0, 0.0]
    assert max(centrosymmetry(moved, 12)["centrosymmetry_A2"]) > 0.1


def test_steinhardt_matches_the_published_fcc_values():
    fcc = bulk("Cu", "fcc", a=3.61, cubic=True) * (2, 2, 2)
    got = steinhardt(fcc, 3.0)
    assert got["q4"][0] == pytest.approx(0.1909, abs=0.001)
    assert got["q6"][0] == pytest.approx(0.5745, abs=0.001)
    assert "判定していません" in got["note"] or "does not say" in got["note"]


def test_clusters_count_connected_groups():
    far = Atoms("H4", positions=[[0, 0, 0], [0.8, 0, 0], [10, 0, 0], [10.8, 0, 0]])
    got = clusters(far, 1.2)
    assert got["n_clusters"] == 2 and got["sizes"] == [2, 2]
    assert clusters(far, 20.0)["n_clusters"] == 1


def test_angle_distribution_peaks_at_the_real_angle():
    w = molecule("H2O")
    got = angle_distribution([w], center="O", cutoff=1.2)
    peak = got["angle_deg"][int(np.argmax(got["counts"]))]
    assert peak == pytest.approx(w.get_angle(1, 0, 2), abs=2.0)
    assert got["n_angles"] == 1
    with pytest.raises(LocalOrderError, match="カットオフ|cutoff"):
        angle_distribution([w], center="O", cutoff=0.0)


def test_structure_factor_of_an_ideal_gas_is_one():
    r = np.linspace(0.05, 12.0, 240)
    got = structure_factor(r, np.ones_like(r), 0.03)
    assert np.allclose(got["s_q"], 1.0, atol=1e-9)


def test_structure_factor_peaks_at_two_pi_over_the_spacing():
    r = np.linspace(0.02, 20.0, 800)
    d = 2.8
    g = 1.0 + np.exp(-r / 6.0) * np.sin(2 * np.pi * (r - d) / d) / (r / d) * 0.6
    got = structure_factor(r, g, 0.033, q=np.linspace(0.5, 8.0, 300))
    peak = got["q_1_A"][int(np.argmax(got["s_q"]))]
    assert peak == pytest.approx(2 * np.pi / d, abs=0.1)
    assert got["reliable_above_q"] == pytest.approx(2 * np.pi / 20.0, rel=0.02)


def water_pair():
    return Atoms("OH2OH2", positions=[[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0],
                                      [2.80, 0, 0], [3.10, 0.9, 0.3], [3.10, -0.5, -0.8]])


def test_hydrogen_bond_is_counted_with_the_given_criteria():
    got = count_frame(water_pair(), 3.2, 140.0)
    assert got["count"] == 1
    pair = got["pairs"][0]
    assert pair["distance_A"] == pytest.approx(2.8, abs=0.01) and pair["angle_deg"] == pytest.approx(180.0, abs=1.0)


def test_criteria_are_required_and_known_values_are_only_shown():
    with pytest.raises(HydrogenBondError, match="距離|distance"):
        count_frame(water_pair(), 0.0, 150.0)
    with pytest.raises(HydrogenBondError, match="角度|angle"):
        count_frame(water_pair(), 3.0, 0.0)
    note = criteria_note()
    assert "GROMACS" in note and "VMD" in note and "cpptraj" in note
    assert "既定値を持ちません" in note or "no default" in note


def test_tighter_distance_removes_the_bond():
    assert count_frame(water_pair(), 2.5, 140.0)["count"] == 0
    series = count_series([water_pair(), water_pair()], 3.2, 140.0)
    assert series["counts"] == [1, 1] and series["mean"] == pytest.approx(1.0)


def test_radius_of_gyration_of_a_spherical_shell():
    rng = np.random.default_rng(0)
    v = rng.normal(size=(200, 3)); v /= np.linalg.norm(v, axis=1)[:, None]
    shell = Atoms("C200", positions=v * 5.0)
    got = radius_of_gyration([shell])
    assert got["rg_A"][0] == pytest.approx(5.0, rel=0.02)
    assert len(got["principal_A"][0]) == 3


class _FakeGrid:
    def __init__(self, values, atoms):
        self.values, self.atoms = np.asarray(values, dtype=float), atoms


def test_difference_checks_the_grid_and_cell():
    si = bulk("Si", cubic=True)
    a = _FakeGrid(np.ones((4, 4, 4)) * 3, si)
    b = _FakeGrid(np.ones((4, 4, 4)), si)
    assert np.allclose(difference([a, b, b], [1, -1, -1]), 1.0)
    other = si.copy(); other.set_cell(si.cell * 1.1, scale_atoms=True)
    with pytest.raises(VolumetricError, match="セル|cells"):
        difference([a, _FakeGrid(np.ones((4, 4, 4)), other)], [1, -1])
    with pytest.raises(VolumetricError, match="分割|shapes"):
        difference([a, _FakeGrid(np.ones((3, 3, 3)), si)], [1, -1])


def test_macroscopic_average_flattens_one_period():
    x = np.linspace(0, 10, 501)
    v = np.abs(((x / 2.0) % 1.0) - 0.5)
    avg = macroscopic_average(x, v, 2.0)
    assert float(np.std(avg[50:-50])) < 1e-6
    with pytest.raises(VolumetricError, match="周期|period"):
        macroscopic_average(x, v, 0.0)


def test_density_grid_conserves_the_atom_count(tmp_path):
    si = bulk("Si", cubic=True)
    grid = DensityGrid((16, 16, 16))
    for _ in range(3):
        grid.add(si)
    got = grid.result()
    assert float(got["values"].sum() * got["voxel_A3"]) == pytest.approx(len(si))
    path = grid.write_cube(tmp_path / "density.cube")
    from adit.analysis.volumetric import read_grid
    assert read_grid(path).values.shape == (16, 16, 16)

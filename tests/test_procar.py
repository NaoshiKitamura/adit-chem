from pathlib import Path

import numpy as np
import pytest

from adit.analysis.procar import read_procar, summary_lines

DATA = Path(__file__).parent / "data"
SIMPLE = DATA / "PROCAR.simple"
PHASE = DATA / "PROCAR.new_format_5.4.4.gz"


def test_reads_the_simple_format():
    pc = read_procar(SIMPLE)
    assert pc.projections.shape == (2, 10, 10, 3, 3)
    assert pc.orbitals == ["s", "p", "d"]
    assert pc.weights.sum() == pytest.approx(1.0, abs=1e-6)
    assert pc.projections[0, 0, 0, 0, 0] == pytest.approx(0.025)
    assert pc.total()[0, 0] == pytest.approx(0.795, abs=1e-3)
    assert pc.energies_ev[0, 0, 0] == pytest.approx(-14.51487969)


def test_reads_the_lm_plus_phase_format_and_skips_the_phase():
    pc = read_procar(PHASE)
    assert pc.projections.shape == (2, 13, 20, 4, 9)
    assert pc.orbitals[0] == "s" and len(pc.orbitals) == 9
    assert np.all(pc.projections >= -1e-9)


def test_sums_by_ion_and_orbital():
    pc = read_procar(SIMPLE)
    total = sum(pc.by_ion(i) for i in (1, 2, 3))
    assert np.allclose(total, pc.total())
    assert np.allclose(pc.by_orbital("s") + pc.by_orbital("p") + pc.by_orbital("d"), pc.total())


def test_bad_selection_is_an_error():
    pc = read_procar(SIMPLE)
    with pytest.raises(ValueError, match="範囲の外"):
        pc.by_ion(99)
    with pytest.raises(ValueError, match="軌道"):
        pc.by_orbital("f")


def test_matches_pymatgen_when_it_is_installed():
    pmg = pytest.importorskip("pymatgen.io.vasp.outputs")
    from pymatgen.electronic_structure.core import Spin

    for path in (SIMPLE, PHASE):
        mine, ref = read_procar(path), pmg.Procar(path)
        assert np.allclose(mine.projections[0], np.array(ref.data[Spin.up]), atol=1e-6)
        assert np.allclose(mine.projections[1], np.array(ref.data[Spin.down]), atol=1e-6)
        assert np.allclose(mine.energies_ev[0], np.array(ref.eigenvalues[Spin.up]), atol=1e-6)
        assert np.allclose(mine.kpoints_frac, np.array(ref.kpoints), atol=1e-5)


def test_summary_and_missing_header(tmp_path):
    assert any("PROCAR" in line for line in summary_lines(read_procar(SIMPLE)))
    bad = tmp_path / "PROCAR"
    bad.write_text("nothing\n", encoding="utf-8")
    with pytest.raises(ValueError, match="見出し"):
        read_procar(bad)

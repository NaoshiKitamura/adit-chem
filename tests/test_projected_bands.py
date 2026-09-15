from pathlib import Path

import numpy as np
import pytest

from adit.analysis.projected_bands import find_filproj, read_filproj, summary_lines

DATA = Path(__file__).parent / "data" / "si.proj.projwfc_up"


def test_reads_the_real_projwfc_file():
    pb = read_filproj(DATA)
    assert (pb.n_kpoints, pb.n_bands) == (25, 8)
    assert len(pb.projections) == 8
    assert {p.element for p in pb.projections} == {"Si"}
    assert sorted({p.l for p in pb.projections}) == [0, 1]


def test_weights_are_between_zero_and_one_and_sum_below_one():
    pb = read_filproj(DATA)
    total = pb.total()
    assert total.shape == (25, 8)
    assert np.all(total >= 0.0) and np.all(total <= 1.0 + 1e-6)
    assert total[:, :4].mean() > 0.9


def test_sums_by_atom_and_element_agree():
    pb = read_filproj(DATA)
    both = pb.by_atom(1) + pb.by_atom(2)
    assert np.allclose(both, pb.by_element("Si"))
    assert np.allclose(pb.by_angular_momentum(0) + pb.by_angular_momentum(1), pb.total())


def test_missing_selection_is_an_error():
    pb = read_filproj(DATA)
    with pytest.raises(ValueError, match="元素"):
        pb.by_element("O")


def test_find_and_summary(tmp_path):
    (tmp_path / "si.proj.projwfc_up").write_bytes(DATA.read_bytes())
    found = find_filproj(tmp_path)
    assert found is not None
    lines = summary_lines(read_filproj(found))
    assert any("Si" in line for line in lines)


def test_rejects_a_file_without_the_header(tmp_path):
    bad = tmp_path / "x.projwfc_up"
    bad.write_text("1 2 3\n4 5 6\n", encoding="utf-8")
    with pytest.raises(ValueError, match="見出し"):
        read_filproj(bad)

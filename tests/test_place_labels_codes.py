
import pytest

from adit.validate_types import PLACE_LABELS, ValidationError

CODE_FIELDS = [
    # CP2K
    "method.xc", "method.basis_file", "method.potential_file", "method.basis", "method.potential", "method.dispersion",
    "method.cutoff_ry", "method.rel_cutoff_ry", "method.eps_scf", "method.max_scf", "method.uks", "method.poisson_solver",
    "method.isolated_box_ang", "method.extra_sections",
    # LAMMPS
    "method.units", "method.atom_style", "method.data_file", "method.type_elements", "method.pair_style", "method.pair_coeff",
    "method.potential_files", "method.style_commands", "method.extra_commands", "method.seed",
    # GROMACS
    "method.topology_file", "method.structure_file", "method.coulombtype", "method.rcoulomb_nm", "method.rvdw_nm", "method.constraints",
    "method.pcoupl", "method.compressibility_per_bar", "method.define", "method.checkpoint_file", "method.gen_seed", "method.extra_mdp",
]


def test_code_fields_use_screen_labels():
    from adit.gui.help import HELP

    missing = [loc for loc in CODE_FIELDS if loc not in PLACE_LABELS]
    assert not missing, missing
    not_on_screen = [(loc, PLACE_LABELS[loc][0]) for loc in CODE_FIELDS if PLACE_LABELS[loc][0] not in HELP]
    assert not not_on_screen, not_on_screen


def test_code_fields_english_matches_i18n():
    pytest.importorskip("PySide6")
    from adit.gui.i18n import _EN

    wrong = [(loc, PLACE_LABELS[loc][1], _EN.get(PLACE_LABELS[loc][0])) for loc in CODE_FIELDS
             if _EN.get(PLACE_LABELS[loc][0]) != PLACE_LABELS[loc][1]]
    assert not wrong, wrong


def test_error_head_is_the_label_not_the_internal_name():
    from adit import lang

    lang.set_language("ja")
    assert str(ValidationError("method.pair_style", "x")) == "pair_style: x"
    assert str(ValidationError("method.rcoulomb_nm", "x")).startswith("カットオフ [nm]: ")
    assert str(ValidationError("method.potential", "x")).startswith("元素ごとの基底と擬ポテンシャル: ")
    lang.set_language("en")
    try:
        assert str(ValidationError("method.xc", "x")) == "Functional: x"
    finally:
        lang.set_language("ja")

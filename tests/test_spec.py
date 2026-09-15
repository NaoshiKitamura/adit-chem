import json

import numpy as np
import pytest
from ase.build import molecule
from pydantic import ValidationError as PydanticError

from adit.spec import HARTREE_PER_BOHR_IN_EV_PER_ANG, AtomsData, CalculationSpec, DftbMethod, Structure
from tests.conftest import water_spec


def test_json_roundtrip():
    spec = water_spec()
    text = spec.to_json()
    back = CalculationSpec.from_json(text)
    assert back == spec
    assert json.loads(text)["method"]["code"] == "dftbplus"


def test_save_load(tmp_path):
    spec = water_spec()
    p = tmp_path / "spec.json"
    spec.save(p)
    assert CalculationSpec.load(p) == spec


def test_ase_roundtrip():
    atoms = molecule("CH4")
    atoms.set_cell([10, 10, 10])
    atoms.pbc = (True, False, True)
    data = AtomsData.from_ase(atoms)
    back = data.to_ase()
    assert back.get_chemical_symbols() == atoms.get_chemical_symbols()
    assert np.allclose(back.get_positions(), atoms.get_positions())
    assert np.allclose(np.asarray(back.cell), np.asarray(atoms.cell))
    assert tuple(back.pbc) == (True, False, True)


def test_elements_in_order_without_duplicates():
    assert water_spec().elements == ["O", "H"]


def test_defaults_match_dftbplus_manual():
    m = DftbMethod(sk_set="x")
    assert m.scc is True and m.scc_tolerance == 1e-5 and m.max_scc_iterations == 100
    assert abs(water_spec().task.force_tolerance_ev_per_ang - 1e-4 * HARTREE_PER_BOHR_IN_EV_PER_ANG) < 1e-12  # 1e-4 Hartree/Bohr


def test_mismatched_lengths_rejected():
    with pytest.raises(PydanticError):
        AtomsData(symbols=["O", "H"], positions=[(0, 0, 0)])


def test_unknown_code_rejected():
    with pytest.raises(PydanticError):
        DftbMethod(code="vasp", sk_set="x")


def test_unknown_source_rejected():
    with pytest.raises(PydanticError):
        Structure(source="magic", source_ref="", atoms=AtomsData(symbols=["H"], positions=[(0, 0, 0)]))

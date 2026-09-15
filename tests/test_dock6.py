"""DOCK6 input packaging; no receptor or scoring settings are inferred.

Sources: https://dock.compbio.ucsf.edu/DOCK_6/dock6_manual.htm
https://dock.compbio.ucsf.edu/DOCK_6/tutorials/ligand_sampling_dock/ligand_sampling_dock.html
"""

import json

import pytest

from adit.dock6 import Dock6Error, package_dock6
from adit.convert import main as convert_main


def _inputs(tmp_path, *, grid_bmp=True):
    root = tmp_path / "source"
    root.mkdir()
    names = ["lig.mol2", "site.sph", "grid.nrg", "vdw.defn"]
    if grid_bmp:
        names.append("grid.bmp")
    for name in names:
        (root / name).write_text(name + "\n", encoding="utf-8")
    (root / "dock.in").write_text(
        "conformer_search_type rigid\nligand_atom_file lig.mol2\norient_ligand yes\n"
        "receptor_site_file site.sph\ngrid_score_primary yes\n"
        "grid_score_grid_prefix grid\nvdw_defn_file vdw.defn\n", encoding="utf-8")
    return root


def test_dock6_package_preserves_input_and_stages_dependencies(tmp_path):
    root = _inputs(tmp_path)
    dst = package_dock6(root / "dock.in", tmp_path / "ready")
    assert (dst / "dock.in").read_bytes() == (root / "dock.in").read_bytes()
    assert {p.name for p in dst.iterdir()} >= {"lig.mol2", "site.sph", "grid.nrg", "grid.bmp", "vdw.defn", "run.sh", "README.txt"}
    assert "dock6 -i dock.in -o dock.out" in (dst / "run.sh").read_text(encoding="utf-8")
    assert set(json.loads((dst / "input_sha256.json").read_text(encoding="utf-8"))) == {
        "dock.in", "lig.mol2", "site.sph", "grid.nrg", "grid.bmp", "vdw.defn"}
    assert "ADIT は投入しません" in (dst / "README.txt").read_text(encoding="utf-8")


def test_dock6_package_rejects_missing_grid_and_external_paths_before_writing(tmp_path):
    root = _inputs(tmp_path, grid_bmp=False)
    out = tmp_path / "ready"
    with pytest.raises(Dock6Error, match="grid.bmp"):
        package_dock6(root / "dock.in", out)
    assert not out.exists()
    text = (root / "dock.in").read_text(encoding="utf-8").replace("lig.mol2", "../lig.mol2")
    (root / "dock.in").write_text(text, encoding="utf-8")
    with pytest.raises(Dock6Error, match="相対パス|relative"):
        package_dock6(root / "dock.in", out)
    assert not out.exists()


def test_dock6_package_does_not_overwrite(tmp_path):
    root = _inputs(tmp_path)
    out = package_dock6(root / "dock.in", tmp_path / "ready")
    before = (out / "dock.in").read_bytes()
    with pytest.raises(Dock6Error, match="上書きしません|not overwritten"):
        package_dock6(root / "dock.in", out)
    assert (out / "dock.in").read_bytes() == before


def test_dock6_cli_packages_without_running_the_code(tmp_path):
    root = _inputs(tmp_path)
    assert convert_main(["dock6", str(root / "dock.in"), str(tmp_path / "ready")]) == 0
    assert (tmp_path / "ready" / "run.sh").is_file()
    assert not (tmp_path / "ready" / "dock.out").exists()

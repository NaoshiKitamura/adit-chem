import json
import re
from pathlib import Path

import pytest
from ase.build import bulk, molecule

from adit.web.structure3d import BOND_FACTOR, MAX_BOND_ATOMS, scene_from_atoms, summary_line

JS = Path(__file__).resolve().parents[1] / "src" / "adit" / "web" / "static" / "viewer3d.js"


def test_water_scene_matches_the_desktop_rules():
    scene = scene_from_atoms(molecule("H2O"))
    assert scene.n_atoms == 3
    assert scene.bonds == [[0, 1], [0, 2]]
    assert scene.colors[0] == "#ff0d0d" and scene.colors[1] == "#ffffff"
    assert scene.radii[0] == pytest.approx(0.66, abs=0.01)
    assert scene.cell_lines == []
    for axis in range(3):
        assert abs(sum(p[axis] for p in scene.positions)) < 1e-3


def test_periodic_cell_gets_twelve_edges():
    scene = scene_from_atoms(bulk("Si", "diamond", a=5.43, cubic=True))
    assert len(scene.cell_lines) == 12
    assert scene.n_atoms == 8
    assert scene.scale > 4.0


def test_bond_rule_is_the_same_factor_as_the_desktop():
    from ase import Atoms
    from ase.data import covalent_radii

    limit = (covalent_radii[1] * 2) * BOND_FACTOR
    close = scene_from_atoms(Atoms("H2", positions=[[0, 0, 0], [limit * 0.9, 0, 0]]))
    far = scene_from_atoms(Atoms("H2", positions=[[0, 0, 0], [limit * 1.1, 0, 0]]))
    assert close.bonds == [[0, 1]] and far.bonds == []


def test_too_many_atoms_says_so_instead_of_freezing_the_browser():
    from ase import Atoms

    n = MAX_BOND_ATOMS + 1
    atoms = Atoms("H" * n, positions=[[i * 3.0, 0, 0] for i in range(n)])
    scene = scene_from_atoms(atoms)
    assert scene.truncated_bonds and scene.bonds == []
    assert "結合" in summary_line(scene, False) or "bonds" in summary_line(scene, False)


def test_json_is_safe_to_put_inside_a_script_tag():
    scene = scene_from_atoms(molecule("H2O"))
    text = scene.to_json()
    assert "<" not in text
    assert json.loads(text)["n_atoms"] == 3


def test_the_viewer_loads_nothing_from_the_outside():
    js = JS.read_text(encoding="utf-8")
    assert "http://" not in js and "https://" not in js
    assert "import" not in js and "require(" not in js
    assert "getContext" in js and "ADIT_SCENE" in js


def test_the_page_shows_the_viewer_and_says_what_happens_without_javascript(tmp_path):
    from adit.config import default_config
    from adit.web.server import WebApp

    repo = Path(__file__).resolve().parents[1]
    app = WebApp(default_config(sk_root=str(repo / "slakos")), tmp_path / "cluster.toml")
    status, err = app.preview({"source": "preset", "preset": "H2O", "code": "dftbplus",
                               "task_type": "single_point", "sk_set": "mio-1-1",
                               "output_dir": str(tmp_path / "out")})
    if err:
        pytest.skip(f"この環境では構造を組み立てられない: {err}")
    scene_json, note, periodic = app.scene()
    assert json.loads(scene_json)["n_atoms"] == 3
    assert "原子 3 個" in note or "3 atoms" in note
    assert periodic is False
    html = (repo / "src" / "adit" / "web" / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'id="adit3d"' in html and "noscript" in html
    assert "JavaScript" in html
    assert "scene_json | safe" in html


def test_no_scene_before_a_structure_is_built(tmp_path):
    from adit.config import default_config
    from adit.web.server import WebApp

    app = WebApp(default_config(sk_root=""), tmp_path / "cluster.toml")
    assert app.scene() == ("", "", False)

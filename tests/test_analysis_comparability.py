from pathlib import Path
from types import SimpleNamespace

from ase import Atoms

from adit.analysis.comparability import audit_run_dirs
from adit.analysis.readers import RunData


def _spec(code="espresso", task="molecular_dynamics"):
    atoms = Atoms(("Si", "O"), positions=[(0, 0, 0), (1, 1, 1)], cell=[5, 5, 5], pbc=True)
    return SimpleNamespace(method=SimpleNamespace(code=code), task=SimpleNamespace(type=task),
                           structure=SimpleNamespace(atoms=SimpleNamespace(to_ase=lambda: atoms.copy())))


def _run(path, code="espresso", symbols=("Si", "Si"), pbc=(True, True, True), cell=None, nframes=3, dt=2.0, energies=None):
    if cell is None:
        cell = [(5.0, 0.0, 0.0), (0.0, 5.0, 0.0), (0.0, 0.0, 5.0)]
    frames = []
    for k in range(nframes):
        atoms = Atoms(symbols, positions=[(0.0, 0.0, 0.0), (1.0 + 0.01 * k, 1.0, 1.0)][: len(symbols)], cell=cell, pbc=pbc)
        frames.append(atoms)
    if energies is None:
        energies = [-10.0 + 0.01 * k for k in range(nframes)]
    return RunData(
        code=code,
        run_dir=Path(path),
        frames=frames,
        energies_ev=energies,
        temperatures_k=[300.0] * nframes,
        times_fs=[dt * k for k in range(nframes)],
        frame_dt_fs=dt,
        frame_source="native.out",
    )


def test_audit_matching_runs(monkeypatch, tmp_path):
    dirs = [tmp_path / "qe", tmp_path / "cp2k"]
    runs = {dirs[0]: _run(dirs[0], code="espresso"), dirs[1]: _run(dirs[1], code="cp2k")}
    specs = {dirs[0]: _spec("espresso"), dirs[1]: _spec("cp2k")}

    monkeypatch.setattr("adit.analysis.comparability.load_project", lambda p: specs[Path(p)])
    monkeypatch.setattr("adit.analysis.comparability.load_run", lambda p: runs[Path(p)])

    audit = audit_run_dirs(dirs, labels=["qe", "cp2k"])

    assert audit.comparable
    assert audit.to_dict()["runs"][0]["units"] == {"time": "fs", "length": "angstrom", "energy": "eV per simulated system"}
    assert "化学的に比べてよいか" in audit.summary_text()


def test_duplicate_directory_basenames_get_distinct_labels(monkeypatch, tmp_path):
    dirs = [tmp_path / "a" / "run", tmp_path / "b" / "run"]
    runs = {p: _run(p) for p in dirs}
    monkeypatch.setattr("adit.analysis.comparability.load_project", lambda p: _spec())
    monkeypatch.setattr("adit.analysis.comparability.load_run", lambda p: runs[Path(p)])
    audit = audit_run_dirs(dirs)
    assert [run.label for run in audit.runs] == ["run#1", "run#2"]
    assert audit.comparable


def test_periodic_same_element_swap_is_not_silently_called_identical(monkeypatch, tmp_path):
    dirs = [tmp_path / "a", tmp_path / "b"]
    runs = {p: _run(p) for p in dirs}
    swapped = runs[dirs[1]].frames[0]
    swapped.positions[:] = swapped.positions[::-1]
    monkeypatch.setattr("adit.analysis.comparability.load_project", lambda p: _spec())
    monkeypatch.setattr("adit.analysis.comparability.load_run", lambda p: runs[Path(p)])
    audit = audit_run_dirs(dirs)
    assert "atoms.initial_positions" in {issue.category for issue in audit.issues}
    assert not audit.comparable


def test_audit_blocks_atom_order_and_pbc_mismatch(monkeypatch, tmp_path):
    dirs = [tmp_path / "a", tmp_path / "b", tmp_path / "c"]
    runs = {
        dirs[0]: _run(dirs[0], symbols=("Si", "O")),
        dirs[1]: _run(dirs[1], symbols=("O", "Si")),
        dirs[2]: _run(dirs[2], symbols=("Si", "O"), pbc=(False, False, False)),
    }

    monkeypatch.setattr("adit.analysis.comparability.load_project", lambda p: _spec(runs[Path(p)].code))
    monkeypatch.setattr("adit.analysis.comparability.load_run", lambda p: runs[Path(p)])

    audit = audit_run_dirs(dirs, labels=["ref", "order", "pbc"])
    cats = {i.category for i in audit.issues}

    assert not audit.comparable
    assert "atoms.order" in cats
    assert "pbc.mismatch" in cats


def test_audit_blocks_short_md_without_dt_or_energy(monkeypatch, tmp_path):
    d = tmp_path / "short"
    run = _run(d, nframes=1, dt=2.0, energies=[])
    run.frame_dt_fs = None

    monkeypatch.setattr("adit.analysis.comparability.load_project", lambda p: _spec("espresso"))
    monkeypatch.setattr("adit.analysis.comparability.load_run", lambda p: run)

    audit = audit_run_dirs([d], labels=["short"])
    cats = {i.category for i in audit.issues}

    assert not audit.comparable
    assert {"trajectory.too_short", "trajectory.dt_missing"} <= cats
    assert "energy.missing" not in cats


def test_energy_audit_does_not_require_trajectory_or_atom_order(monkeypatch, tmp_path):
    dirs = [tmp_path / "a", tmp_path / "b"]
    a = _run(dirs[0], symbols=("Si", "O"), nframes=0, dt=2.0, energies=[-10.0])
    b = _run(dirs[1], symbols=("O", "Si"), nframes=2, dt=5.0, energies=[-9.0])
    a.frames = []
    a.frame_dt_fs = None
    runs = {dirs[0]: a, dirs[1]: b}

    monkeypatch.setattr("adit.analysis.comparability.load_project", lambda p: _spec(runs[Path(p)].code, task="single_point"))
    monkeypatch.setattr("adit.analysis.comparability.load_run", lambda p: runs[Path(p)])

    audit = audit_run_dirs(dirs, labels=["a", "b"], require_md=False)
    cats = {i.category for i in audit.issues}

    assert audit.comparable
    assert audit.to_dict()["mode"] == "energy"
    assert not {"trajectory.missing", "trajectory.frame_count", "trajectory.frame_dt", "atoms.order"} & cats


def test_energy_audit_requires_whole_system_energy(monkeypatch, tmp_path):
    d = tmp_path / "empty_energy"
    run = _run(d, nframes=0, energies=[])
    run.frames = []

    monkeypatch.setattr("adit.analysis.comparability.load_project", lambda p: _spec("espresso", task="single_point"))
    monkeypatch.setattr("adit.analysis.comparability.load_run", lambda p: run)

    audit = audit_run_dirs([d], labels=["empty"], require_md=False)

    assert not audit.comparable
    assert "energy.missing" in {i.category for i in audit.issues}


def test_energy_audit_rejects_different_composition(monkeypatch, tmp_path):
    dirs = [tmp_path / "a", tmp_path / "b"]
    runs = {dirs[0]: _run(dirs[0], symbols=("Si", "O")),
            dirs[1]: _run(dirs[1], symbols=("Si", "Si"))}
    monkeypatch.setattr("adit.analysis.comparability.load_project", lambda p: _spec())
    monkeypatch.setattr("adit.analysis.comparability.load_run", lambda p: runs[Path(p)])
    audit = audit_run_dirs(dirs, require_md=False)
    assert not audit.comparable
    assert "atoms.composition" in {issue.category for issue in audit.issues}


def test_energy_audit_flags_unverified_definition_across_codes(monkeypatch, tmp_path):
    dirs = [tmp_path / "qe", tmp_path / "vasp"]
    runs = {dirs[0]: _run(dirs[0], code="espresso"), dirs[1]: _run(dirs[1], code="vasp")}
    monkeypatch.setattr("adit.analysis.comparability.load_project", lambda p: _spec(runs[Path(p)].code))
    monkeypatch.setattr("adit.analysis.comparability.load_run", lambda p: runs[Path(p)])
    audit = audit_run_dirs(dirs, require_md=False)
    assert not audit.comparable
    assert "energy.definition_unverified" in {issue.category for issue in audit.issues}


def test_audit_blocks_per_atom_energy(monkeypatch, tmp_path):
    d = tmp_path / "mlip"
    run = _run(d, code="mlip")
    run.notes.append("the md.log values are per atom (Etot/N) and are listed as they are")

    monkeypatch.setattr("adit.analysis.comparability.load_project", lambda p: _spec("mlip"))
    monkeypatch.setattr("adit.analysis.comparability.load_run", lambda p: run)

    audit = audit_run_dirs([d], labels=["mlip"], require_md=False)

    assert not audit.comparable
    assert "energy.per_atom" in {i.category for i in audit.issues}


def test_audit_reports_english_messages(monkeypatch, tmp_path):
    from adit import lang

    d = tmp_path / "sp"
    monkeypatch.setattr(lang, "LANGUAGE", "en")
    monkeypatch.setattr("adit.analysis.comparability.load_project", lambda p: _spec("espresso", task="single_point"))
    monkeypatch.setattr("adit.analysis.comparability.load_run", lambda p: _run(d, nframes=1))

    audit = audit_run_dirs([d], labels=["sp"])
    text = audit.summary_text()

    assert "cross-code check" in text
    assert "MSD comparison was requested" in text
    assert "chemical comparability is not judged" in text

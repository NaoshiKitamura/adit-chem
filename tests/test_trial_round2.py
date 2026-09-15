
from pathlib import Path

import numpy as np
import pytest

from adit.errors import AditError, AditValueError
from adit.spec import CalculationSpec


def test_every_adit_exception_descends_from_adit_error():
    from adit.analysis.transport import TransportError
    from adit.analysis.trajectory import TrajectoryTooLarge
    from adit.analysis.volumetric import VolumetricError
    from adit.analysis.xrd import XrdError
    from adit.codes.base import GenerationError
    from adit.project import OutputNotEmpty
    from adit.scan import ScanError
    from adit.structure import StructureError
    from adit.templates import TemplateError

    for cls in (TransportError, TrajectoryTooLarge, VolumetricError, XrdError, GenerationError,
                OutputNotEmpty, ScanError, StructureError, TemplateError):
        assert issubclass(cls, AditError), cls.__name__
    assert issubclass(AditValueError, ValueError)
    assert issubclass(TrajectoryTooLarge, ValueError)


def test_handoff_does_not_import_adit():
    text = Path("src/adit/handoff.py").read_text(encoding="utf-8")
    assert "from adit" not in text and "import adit" not in text


def test_missing_spec_file_says_what_to_do():
    try:
        CalculationSpec.load("/tmp/does-not-exist-adit.json")
    except FileNotFoundError as ex:
        message = CalculationSpec.describe_error(ex)
    assert "does-not-exist-adit.json" in message and "--sample" in message
    assert "Errno" not in message


def test_a_directory_given_instead_of_a_file_says_so(tmp_path):
    try:
        CalculationSpec.load(tmp_path)
    except (IsADirectoryError, PermissionError) as ex:
        message = CalculationSpec.describe_error(ex)
    assert "ディレクトリ" in message and str(tmp_path) in message


def test_analysis_can_write_outside_the_run_directory(tmp_path):
    from adit.analysis.report import AnalysisOptions, run_analysis

    run = Path("examples/qe_si_generated")
    res = run_analysis(run, AnalysisOptions(out_dir=tmp_path / "deep" / "out"))
    assert (tmp_path / "deep" / "out" / "summary.json").is_file()
    assert not (run / "analysis").exists() or all(
        not Path(p).is_relative_to(run) for p in res.figures.values())


def test_block_error_suggests_a_usable_fit_range_instead_of_narrowing():
    from adit.analysis import compute

    pos = (np.arange(21, dtype=float) ** 2)[:, None, None] * np.ones((1, 1, 3))
    out = compute.diffusion_blocks(pos, 5.0, 5, fit_fs=(10.0, 50.0))
    assert out["d_err_cm2_s"] is None and out["reason_code"] == "fit_range_not_available_in_all_blocks"
    assert "--msd-fit" in out["reason"]
    assert out["fit_range_fs"] == [10.0, 50.0]


def test_xrd_appears_in_the_analysis_summary(tmp_path):
    pytest.importorskip("pymatgen")
    from adit.analysis.report import AnalysisOptions, run_analysis

    res = run_analysis(Path("examples/qe_si_generated"), AnalysisOptions(out_dir=tmp_path, xrd="CuKa"))
    assert res.tables["xrd"]["n_peaks"] > 0 and (tmp_path / "xrd.csv").is_file()
    assert any("粉末 X 線回折" in n for n in res.notes)


@pytest.mark.parametrize("code,name,text,expected", [
    ("dftbplus", "output.log", "ERROR!\n-> Missing child: MaxAngularMomentum\n", "ERROR!"),
    ("espresso", "output.log", "     Error in routine  system_checkin (1):\n      ecutwfc out of range\n", "ecutwfc out of range"),
    ("cp2k", "output.log", " * [ABORT]  The specified OLD file <x> cannot be opened. *\n", "[ABORT]"),
    ("lammps", "log.lammps", "ERROR: Unrecognized pair style 'x' (src/force.cpp:275)\n", "Unrecognized pair style"),
    ("gromacs", "output.log", "Error in user input:\nInvalid command-line options\n", "Invalid command-line options"),
    ("abinit", "output.log", "--- !ERROR\nsrc_file: m_common.F90\nmessage: |\n    `pseudos` variable must be specified\n", "pseudos"),
    ("psi4", "output.dat", "*** Psi4 encountered an error. Buy a developer more coffee!\n", "encountered an error"),
    ("xtb", "output.log", "abnormal termination of xtb\n[ERROR] Program stopped due to fatal error\n", "abnormal termination"),
])
def test_failure_lines_quote_the_codes_own_message(tmp_path, code, name, text, expected):
    from adit.results import failure_lines, failure_note

    (tmp_path / name).write_text(text, encoding="utf-8")
    lines = failure_lines(tmp_path, code)
    assert lines and any(expected in line for line in lines)
    assert all(line.startswith(f"{name}:") for line in lines)
    assert expected in failure_note(tmp_path, code)


def test_no_error_marks_for_codes_we_did_not_verify(tmp_path):
    from adit.results import failure_lines

    (tmp_path / "output.log").write_text("ERROR: something\n", encoding="utf-8")
    for code in ("vasp", "orca", "nwchem", "openmm"):
        assert failure_lines(tmp_path, code) == []


def test_abinit_psp_header_is_read_without_naming_the_functional(tmp_path):
    from adit.codes.abinit_psp import describe, read_psp_header

    p = tmp_path / "14si.pspnc"
    p.write_text(" Troullier-Martins psp for element  Si        Thu Oct 27 1994\n"
                 "  14.00000   4.00000    940714                zatom, zion, pspdat\n"
                 "    1    1    2    2      2001    .00000      pspcod,pspxc,lmax,lloc,mmax,r2well\n",
                 encoding="utf-8")
    head = read_psp_header(p)
    assert head.zatom == 14 and head.zion == 4 and head.pspcod == 1 and head.pspxc == 1
    text = describe(head)
    assert "pspxc=1" in text and "LDA" not in text and "PBE" not in text


def test_abinit_psp_appears_in_the_report_table(tmp_path):
    from adit.report import load_run_report, parameter_rows
    from tests.conftest import cfg_for, water_spec  # noqa: F401  

    (tmp_path / "spec.json").write_text(Path("examples/abinit_si_generated/spec.json").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "14si.pspnc").write_text(" title\n  14.0 4.0 940714 zatom, zion, pspdat\n  1 1 2 2 2001 .0 pspcod,pspxc\n", encoding="utf-8")
    rows = parameter_rows(load_run_report(tmp_path))
    assert any(r[0] == "14si.pspnc" and "pspxc=1" in r[2] for r in rows)


def test_english_report_says_when_the_analysis_summary_is_japanese(tmp_path):
    import shutil

    from adit.report import load_run_report, methods_markdown

    run = tmp_path / "run"
    shutil.copytree("examples/abinit_si_generated", run)
    (run / "analysis").mkdir(exist_ok=True)
    (run / "analysis" / "summary.txt").write_text("エネルギー: 1 点、最終値 -310 eV\n", encoding="utf-8")
    text = methods_markdown([load_run_report(run)], "en")
    assert "adit-analyze` was run with the Japanese interface" in text


def test_espresso_dipole_correction_writes_the_verified_keywords(sk_root, tmp_path):
    from tests.conftest import cfg_for
    from tests.test_espresso import make_fake_upf, si_spec
    from adit.project import build_project
    from adit.spec import EspressoMethod

    cfg = cfg_for(sk_root)
    cfg.pseudo_root = str(make_fake_upf(tmp_path / "pseudo"))
    method = EspressoMethod(pseudo_set="fake-pbe", pseudo={"Si": "Si.pbe-fake.UPF"}, ecutwfc=40,
                            dipole_correction=True, dipole_direction=3, dipole_maxpos=0.02, dipole_decrease=0.05)
    files = build_project(si_spec(method=method), cfg)
    text = files.texts["pw.in"]
    control = text.split("&SYSTEM")[0]
    system = text.split("&SYSTEM")[1].split("&ELECTRONS")[0]
    assert "tefield          = .true." in control and "dipfield         = .true." in control
    for line in ("edir             = 3", "emaxpos          = 0.02", "eopreg           = 0.05", "eamp             = 0.0"):
        assert line in system
    assert "Computed dipole along edir" in files.texts["README.txt"]


def test_dipole_correction_without_a_direction_is_refused(sk_root, tmp_path):
    from tests.conftest import cfg_for
    from tests.test_espresso import make_fake_upf, si_spec
    from adit.codes.espresso import EspressoGenerator
    from adit.spec import EspressoMethod

    cfg = cfg_for(sk_root)
    cfg.pseudo_root = str(make_fake_upf(tmp_path / "pseudo"))
    spec = si_spec(method=EspressoMethod(pseudo_set="fake-pbe", pseudo={"Si": "Si.pbe-fake.UPF"}, ecutwfc=40,
                                         dipole_correction=True, dipole_decrease=0.05))
    errs = EspressoGenerator().validate(spec, cfg)
    assert any(e.location == "method.dipole_direction" for e in errs)
    spec2 = si_spec(method=EspressoMethod(pseudo_set="fake-pbe", pseudo={"Si": "Si.pbe-fake.UPF"}, ecutwfc=40,
                                          dipole_correction=True, dipole_direction=3))
    assert any(e.location == "method.dipole_decrease" for e in EspressoGenerator().validate(spec2, cfg))


def test_eyring_rate_reproduces_the_textbook_prefactor_and_barrier():
    from adit.analysis.rate import eyring_rate, summary_line

    assert eyring_rate(0.0).rate_per_s == pytest.approx(6.21e12, rel=1e-2)
    r = eyring_rate(100.0)
    assert r.rate_per_s == pytest.approx(1.88e-5, rel=1e-2) and r.half_life_s == pytest.approx(3.69e4, rel=1e-2)
    assert "ADIT は確かめません" in r.note
    assert "1/s" in summary_line(r)


def test_eyring_refuses_impossible_conditions():
    from adit.analysis.rate import RateError, eyring_rate

    with pytest.raises(RateError, match="温度|temperature"):
        eyring_rate(50.0, 0.0)
    with pytest.raises(RateError, match="透過係数|transmission"):
        eyring_rate(50.0, 300.0, 0.0)

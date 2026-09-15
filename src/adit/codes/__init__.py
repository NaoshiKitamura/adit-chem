"""Registry of the input generators. Importing this module fills GENERATORS."""

from adit.codes.base import GENERATORS, GenerationError, InputGenerator  # noqa: F401
from adit.codes import abinit, amber, cp2k, dcdftbmd, dftbplus, espresso, gromacs, lammps, mlip, molecular_engines, namd, nwchem, openmm, openmx, psi4, orca, vasp, xtb  # noqa: F401  

__all__ = ["GENERATORS", "GenerationError", "InputGenerator"]

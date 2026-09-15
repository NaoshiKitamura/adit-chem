
from __future__ import annotations

from dataclasses import dataclass

from adit.errors import AditValueError
from adit.lang import L

ELEMENTARY_CHARGE_C = 1.602176634e-19
BOLTZMANN_J_PER_K = 1.380649e-23
CM3_PER_ANG3 = 1.0e-24


class ConductivityError(AditValueError):
    pass


@dataclass
class Conductivity:
    sigma_s_per_cm: float
    n_ions: int
    charge: float
    volume_ang3: float
    temperature_k: float
    d_cm2_s: float

    def as_dict(self) -> dict:
        return {"sigma_s_per_cm": self.sigma_s_per_cm, "sigma_ms_per_cm": self.sigma_s_per_cm * 1e3,
                "n_ions": self.n_ions, "charge": self.charge, "volume_ang3": self.volume_ang3,
                "temperature_k": self.temperature_k, "d_cm2_s": self.d_cm2_s,
                "formula": "sigma = N q^2 D / (V k_B T)",
                "note": L("Nernst–Einstein の式です。イオンどうしの相関を無視しているので、"
                          "実測の伝導度より大きく出るのが普通です (その比が Haven 比)。"
                          "電荷は利用者が指定した値で、ADIT は酸化数を決めません。",
                          "The Nernst-Einstein relation. It ignores correlations between ions, so it is usually larger "
                          "than a measured conductivity (their ratio is the Haven ratio). The charge is the value you gave; "
                          "ADIT does not assign oxidation states.")}


def nernst_einstein(d_cm2_s: float, n_ions: int, charge: float, volume_ang3: float,
                    temperature_k: float) -> Conductivity:
    if d_cm2_s is None or d_cm2_s < 0:
        raise ConductivityError(L("拡散係数 D [cm²/s] が要ります (0 以上)", "a diffusion coefficient D in cm^2/s (>= 0) is required"))
    if n_ions <= 0:
        raise ConductivityError(L("イオンの数が 0 です", "the number of ions is zero"))
    if charge == 0:
        raise ConductivityError(L("電荷が 0 では伝導度になりません (Na なら 1、O なら -2 のように指定してください)",
                                  "a charge of zero gives no conductivity (give e.g. 1 for Na or -2 for O)"))
    if volume_ang3 <= 0 or temperature_k <= 0:
        raise ConductivityError(L("セルの体積 [Å³] と温度 [K] が要ります (どちらも正の値)",
                                  "a positive cell volume (A^3) and temperature (K) are required"))
    number_density = n_ions / (volume_ang3 * CM3_PER_ANG3)          # 1/cm³
    q = charge * ELEMENTARY_CHARGE_C                                 # C
    sigma = number_density * q * q * d_cm2_s / (BOLTZMANN_J_PER_K * temperature_k)   # S/cm
    return Conductivity(sigma_s_per_cm=float(sigma), n_ions=int(n_ions), charge=float(charge),
                        volume_ang3=float(volume_ang3), temperature_k=float(temperature_k), d_cm2_s=float(d_cm2_s))


def summary_line(c: Conductivity) -> str:
    return L(f"イオン伝導度 (Nernst–Einstein): {c.sigma_s_per_cm:.4g} S/cm "
             f"({c.sigma_s_per_cm * 1e3:.4g} mS/cm)。{c.n_ions} 個の電荷 {c.charge:+g} のイオン、"
             f"D = {c.d_cm2_s:.4g} cm²/s、体積 {c.volume_ang3:.1f} Å³、温度 {c.temperature_k:g} K。"
             "イオンどうしの相関を無視した式なので、実測より大きく出るのが普通です",
             f"ionic conductivity (Nernst-Einstein): {c.sigma_s_per_cm:.4g} S/cm "
             f"({c.sigma_s_per_cm * 1e3:.4g} mS/cm) from {c.n_ions} ions of charge {c.charge:+g}, "
             f"D = {c.d_cm2_s:.4g} cm^2/s, volume {c.volume_ang3:.1f} A^3, temperature {c.temperature_k:g} K. "
             "The relation ignores ion-ion correlations, so it is usually larger than a measurement")

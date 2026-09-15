
from __future__ import annotations

from adit.errors import AditValueError
from dataclasses import dataclass

import numpy as np

from adit.lang import L

BOLTZMANN_J_PER_K = 1.380649e-23
BAR_TO_PA = 1.0e5
ATM_TO_PA = 101325.0
ANG3_TO_M3 = 1.0e-30


class TransportError(AditValueError):
    pass


@dataclass
class ViscosityResult:
    eta_pa_s: float
    times_fs: np.ndarray
    running_pa_s: np.ndarray
    correlation_pa2: np.ndarray
    temperature_k: float
    volume_ang3: float
    points: int
    note: str

    def as_dict(self) -> dict:
        return {"eta_pa_s": float(self.eta_pa_s), "eta_mpa_s": float(self.eta_pa_s * 1e3),
                "temperature_k": float(self.temperature_k), "volume_ang3": float(self.volume_ang3),
                "points": int(self.points), "max_lag_fs": float(self.times_fs[-1]) if len(self.times_fs) else 0.0,
                "note": self.note}


def _autocorrelation(x: np.ndarray) -> np.ndarray:
    n = len(x)
    size = 1 << (2 * n - 1).bit_length()
    f = np.fft.rfft(x - 0.0, size)
    acf = np.fft.irfft(f * np.conjugate(f), size)[:n]
    return acf / (n - np.arange(n))


def green_kubo_viscosity(times_fs, components, volume_ang3: float, temperature_k: float,
                         pressure_unit: str = "bar", max_lag_fraction: float = 0.5) -> ViscosityResult:
    times = np.asarray(times_fs, dtype=float)
    series = [np.asarray(c, dtype=float) for c in components if c is not None and len(c) == len(times)]
    if len(times) < 4 or not series:
        raise TransportError(L("圧力テンソルの時系列が足りません (4 点以上と、pxy などの成分が要ります)",
                               "not enough pressure-tensor data (at least 4 points and one off-diagonal component are needed)"))
    steps = np.diff(times)
    if not np.allclose(steps, steps[0], rtol=1e-6, atol=1e-9):
        raise TransportError(L("時刻が等間隔ではありません。Green-Kubo の積分は等間隔の時系列にだけ使います",
                               "the times are not evenly spaced; the Green-Kubo integral is only applied to evenly spaced data"))
    if temperature_k <= 0 or volume_ang3 <= 0:
        raise TransportError(L("温度と体積が要ります (どちらも正の値)", "a positive temperature and volume are required"))
    scale = {"bar": BAR_TO_PA, "atm": ATM_TO_PA, "pa": 1.0}.get(pressure_unit.lower())
    if scale is None:
        raise TransportError(L(f"圧力の単位が分かりません: {pressure_unit}", f"unknown pressure unit: {pressure_unit}"))
    dt_s = float(steps[0]) * 1e-15
    acf = np.mean([_autocorrelation(s * scale) for s in series], axis=0)   # Pa^2
    keep = max(2, int(len(acf) * max_lag_fraction))
    acf = acf[:keep]
    integral = np.concatenate([[0.0], np.cumsum((acf[1:] + acf[:-1]) / 2.0) * dt_s])
    prefactor = volume_ang3 * ANG3_TO_M3 / (BOLTZMANN_J_PER_K * temperature_k)
    running = prefactor * integral
    note = L("Green-Kubo の式 η = V/(k_B T) ∫⟨P_ab(0)P_ab(t)⟩dt。時間原点をすべて使い、遅れ時間は全体の "
             f"{max_lag_fraction:.0%} まで。積分が収束しているかは判定していません (図で確かめてください)。",
             "Green-Kubo: eta = V/(k_B T) integral of <P_ab(0)P_ab(t)>. All time origins are used and lags go up to "
             f"{max_lag_fraction:.0%} of the trajectory. Whether the integral has converged is not assessed (check the figure).")
    return ViscosityResult(eta_pa_s=float(running[-1]), times_fs=times[:keep] - times[0], running_pa_s=running,
                           correlation_pa2=acf, temperature_k=float(temperature_k), volume_ang3=float(volume_ang3),
                           points=len(times), note=note)

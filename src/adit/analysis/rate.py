
from __future__ import annotations

import math
from dataclasses import dataclass

from adit.errors import AditValueError
from adit.lang import L

BOLTZMANN_J_PER_K = 1.380649e-23
PLANCK_J_S = 6.62607015e-34
GAS_CONSTANT_J_PER_MOL_K = 8.314462618


class RateError(AditValueError):
    pass


@dataclass
class RateResult:
    delta_g_kj_mol: float
    temperature_k: float
    transmission: float
    rate_per_s: float
    half_life_s: float | None
    note: str

    def as_dict(self) -> dict:
        return {"delta_g_kj_mol": self.delta_g_kj_mol, "temperature_k": self.temperature_k,
                "transmission": self.transmission, "rate_per_s": self.rate_per_s,
                "half_life_s": self.half_life_s, "note": self.note}


def eyring_rate(delta_g_kj_mol: float, temperature_k: float = 298.15, transmission: float = 1.0) -> RateResult:
    if temperature_k <= 0:
        raise RateError(L("温度は 0 K より大きい値が要ります", "the temperature must be greater than 0 K"))
    if transmission <= 0:
        raise RateError(L("透過係数は 0 より大きい値が要ります", "the transmission coefficient must be greater than 0"))
    exponent = -delta_g_kj_mol * 1000.0 / (GAS_CONSTANT_J_PER_MOL_K * temperature_k)
    rate = transmission * (BOLTZMANN_J_PER_K * temperature_k / PLANCK_J_S) * math.exp(exponent)
    half = math.log(2.0) / rate if rate > 0 else None
    note = L(f"Eyring の式 k = κ (k_B T / h) exp(−ΔG‡/RT)、κ = {transmission:g}、T = {temperature_k:g} K。"
             "この値が本当に遷移状態との差かどうかは、ADIT は確かめません (指定された値をそのまま使います)。"
             "トンネル効果・溶媒・標準状態は入れていません (1 分子反応として 1/s)。",
             f"Eyring: k = kappa (k_B T / h) exp(-dG#/RT) with kappa = {transmission:g}, T = {temperature_k:g} K. "
             "ADIT does not check that this value is really a barrier; the value you give is used as it is. "
             "Tunnelling, solvent and standard-state corrections are not included (unimolecular, per second).")
    return RateResult(delta_g_kj_mol=float(delta_g_kj_mol), temperature_k=float(temperature_k),
                      transmission=float(transmission), rate_per_s=float(rate), half_life_s=half, note=note)


def summary_line(result: RateResult) -> str:
    half = result.half_life_s
    if half is None:
        half_text = L("半減期は求められません", "no half-life")
    elif half < 1e-3 or half > 1e5:
        half_text = L(f"半減期 {half:.3g} s", f"half-life {half:.3g} s")
    else:
        half_text = L(f"半減期 {half:.4g} s", f"half-life {half:.4g} s")
    return L(f"速度定数 (Eyring): k = {result.rate_per_s:.4g} 1/s ({half_text}、ΔG‡ = {result.delta_g_kj_mol:g} kJ/mol、"
             f"T = {result.temperature_k:g} K)",
             f"rate constant (Eyring): k = {result.rate_per_s:.4g} 1/s ({half_text}, dG# = {result.delta_g_kj_mol:g} kJ/mol, "
             f"T = {result.temperature_k:g} K)")

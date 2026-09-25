"""Rolling stock model: traction, resistance and braking parameters (SI units internally)."""
from dataclasses import dataclass
from pathlib import Path

import yaml

G = 9.81


@dataclass(frozen=True)
class Train:
    name: str
    length_m: float
    mass_kg: float
    rotating_mass_factor: float
    max_te_n: float
    power_w: float
    vmax_mps: float
    davis_a_n: float
    davis_b: float
    davis_c: float
    service_decel: float
    emergency_decel: float
    traction_cutoff_s: float
    brake_buildup_emergency_s: float
    brake_buildup_service_s: float
    driver_reaction_s: float
    warning_time_s: float

    @property
    def effective_mass(self) -> float:
        return self.mass_kg * self.rotating_mass_factor

    def tractive_effort(self, v: float) -> float:
        """Constant-force region up to the power limit, then constant power (F = P / v)."""
        if v <= 0.1:
            return self.max_te_n
        return min(self.max_te_n, self.power_w / v)

    def resistance(self, v: float) -> float:
        """Davis equation R = A + B v + C v^2, in newtons."""
        return self.davis_a_n + self.davis_b * v + self.davis_c * v * v

    def grade_force(self, gradient_permille: float) -> float:
        return self.mass_kg * G * gradient_permille / 1000.0

    def max_acceleration(self, v: float, gradient_permille: float = 0.0) -> float:
        f = self.tractive_effort(v) - self.resistance(v) - self.grade_force(gradient_permille)
        return f / self.effective_mass


def load_trains(path: str | Path) -> dict[str, Train]:
    raw = yaml.safe_load(Path(path).read_text())
    trains = {}
    for key, p in raw.items():
        trains[key] = Train(
            name=key,
            length_m=p["length_m"],
            mass_kg=p["mass_t"] * 1000,
            rotating_mass_factor=p["rotating_mass_factor"],
            max_te_n=p["max_tractive_effort_kN"] * 1000,
            power_w=p["traction_power_kW"] * 1000,
            vmax_mps=p["max_speed_kmh"] / 3.6,
            davis_a_n=p["davis_A_kN"] * 1000,
            davis_b=p["davis_B_kN_per_mps"] * 1000,
            davis_c=p["davis_C_kN_per_mps2"] * 1000,
            service_decel=p["service_brake_decel_mps2"],
            emergency_decel=p["emergency_brake_decel_mps2"],
            traction_cutoff_s=p["traction_cutoff_s"],
            brake_buildup_emergency_s=p["brake_buildup_emergency_s"],
            brake_buildup_service_s=p["brake_buildup_service_s"],
            driver_reaction_s=p["driver_reaction_s"],
            warning_time_s=p["warning_time_s"],
        )
    return trains

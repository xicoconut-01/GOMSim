"""Weighted passenger delay (OI-12): the ranking criterion defined for regulation proposals (SYS-SUP-04).

Each trip carries `load_per_trip` passengers. A share alights at Union, of whom a share connects onward
(weight 1.5); the rest alight evenly at the other stations after the origin (weight 1.0). Passengers on a
trip listed as a last service are weighted 2.0 (the higher weight wins when both apply).
Delay counted = late arrival at the passenger's alighting station (early arrival counts as zero).
"""
from dataclasses import dataclass

from .propagation import Route, Trip


@dataclass(frozen=True)
class PassengerModel:
    load_per_trip: float
    union_alighting_share: float
    union_connecting_share: float
    weight_connecting: float = 1.5
    weight_last_service: float = 2.0
    weight_default: float = 1.0
    last_service_trips: tuple = ()

    @classmethod
    def from_config(cls, cfg: dict) -> "PassengerModel":
        return cls(cfg["load_per_trip"], cfg["union_alighting_share"], cfg["union_connecting_share"],
                   cfg["weight_connecting"], cfg["weight_last_service"], cfg["weight_default"],
                   tuple(cfg.get("last_service_trips", [])))


def trip_weighted_delay_min(route: Route, trip: Trip, pm: PassengerModel) -> float:
    n = len(route.km)
    order = list(range(n)) if trip.direction == "E" else list(range(n - 1, -1, -1))
    others = n - 2                                  # stations after origin, excluding Union
    last = trip.tid in pm.last_service_trips
    total = 0.0
    for k in range(1, n):
        delay_min = max(trip.arr[k] - trip.sched_arr[k], 0.0) / 60
        if delay_min == 0:
            continue
        if order[k] == route.union_idx:
            pax = pm.load_per_trip * pm.union_alighting_share
            w = (pm.union_connecting_share * pm.weight_connecting
                 + (1 - pm.union_connecting_share) * pm.weight_default)
        else:
            pax = pm.load_per_trip * (1 - pm.union_alighting_share) / others
            w = pm.weight_default
        if last:
            w = max(w, pm.weight_last_service)
        total += pax * w * delay_min
    return total


def weighted_passenger_delay_min(route: Route, trips: list[Trip], pm: PassengerModel) -> float:
    return sum(trip_weighted_delay_min(route, t, pm) for t in trips)

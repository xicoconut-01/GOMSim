"""Readers for OSRD simulation exports (phase 9)."""
import io
from pathlib import Path

import pandas as pd


def read_osrd_export(path: str) -> pd.DataFrame:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("op;"))
    df = pd.read_csv(io.StringIO("\n".join(lines[start:])), sep=";", decimal=",", dtype={"op": str})
    df["t"] = df["seconds"] - df["seconds"].iloc[0]
    df["pos_m"] = df["position"] * 1000.0
    return df


def extract_stops(df: pd.DataFrame) -> pd.DataFrame:
    """Every position where the train stands still: name, arrival and departure time (s)."""
    still = df[df["speed"] <= 1e-6].copy()
    still["key"] = still["pos_m"].round(0)
    stops = still.groupby("key", sort=True).agg(pos_m=("pos_m", "first"), arr=("t", "min"), dep=("t", "max"))
    names = df[df["op"].notna()].assign(key=lambda x: x["pos_m"].round(0)).groupby("key")["op"].first()
    stops["name"] = [names.get(k, "") for k in stops.index]
    return stops.reset_index(drop=True)


def speed_limit_segments(df: pd.DataFrame) -> list[list[float]]:
    pos, lim = df["pos_m"].to_numpy(), df["speedLimit"].to_numpy()
    segs = []
    for i in range(len(df) - 1):
        a, b = pos[i], pos[i + 1]
        if b > a:
            if segs and segs[-1][2] == lim[i] and abs(segs[-1][1] - a) < 1e-6:
                segs[-1][1] = b
            else:
                segs.append([a, b, float(lim[i])])
    return segs

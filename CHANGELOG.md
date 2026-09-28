# Changelog

## v0.3 — 2026-09-27 — validated against OSRD (phase 9)

Added
- Real corridor from OSRD data: path rebuilt on the RailJSON track graph, signals and detectors projected (`railjson_path.py`, `corridor_real.py`, `osrd_export.py`).
- BAL blocking times as implemented in OSRD and delay propagation with holds (`blocking.py`).
- Validation scripts VAL-03 (running time), VAL-04 (fixed-block headway, TC-TC-07), VAL-05 (incident knock-on); stepwise S1 → S2 attribution; Module 3 on the real corridor (`run_module3_real.py`).
- Export of golsim rolling stock to OSRD RailJSON; GTFS current-state baseline (2026-09-29).
- Tests UT-17 to UT-19.

Changed (each found by comparison with OSRD)
- CR-012: driver behaviour on lineside signalling — a lower limit is respected 100 m before it starts, acceleration waits 50 m after it ends (S1 only; not under CBTC with ATO).
- CR-013: safety approach speed into a buffer stop — 30 km/h over the last 200 m, 10 km/h over the last 100 m (S1 only).
- CR-014: a train caught inside the blocked section brakes to a stand and restarts from standstill instead of pausing; the pause under-estimated knock-on holds by about 1 minute.

## v0.2 — 2026-09-25
Parameters traced to SRS and OI; OI-02 reporting interval in moving block; OI-12 weighted passenger delay.

## v0.1 — 2026-09-25
Modules 1–3 on synthetic data.

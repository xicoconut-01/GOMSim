# golsim — GO Lakeshore Line simulation toolkit (v0.3)

Simulation model of the Lakeshore Line Modernization project (EN 50126-1:2017, phases 6 and 9).
golsim is the simulation model required as a precondition by the Simulation-level test cases in the DOORS
Test_Cases module (TC-TC-07, TC-SUP-01). Parameters are traced to the SRS and the TBD resolution log (OI-xx).

**v0.3 is validated against OSRD** (Open Source Railway Designer, commit 4a1a8bdce) on the real
Hamilton GO Centre – Oshawa GO corridor (116.130 km, 21 stops) built from OpenStreetMap data:
running times agree within 0.06 %, the fixed-block minimum headway falls inside OSRD's measured range, and
incident knock-on delays on the open line agree within ±1 minute. See `CHANGELOG.md` and `docs/traceability.csv`.

## Modules

| Module | File | Purpose | DOORS link |
|---|---|---|---|
| 1a Running time | `src/golsim/dynamics.py` | Envelope method: traction, Davis resistance, gradient, braking, train-length rule; driver margins (CR-012) and buffer-stop approach (CR-013) | — |
| 1b ATP supervision | `src/golsim/braking.py` | Simplified ETCS-style curves: EBD, EBI, SBI, Warning, Permitted | SYS-TC-04, OI-06 |
| 2 Headway | `src/golsim/headway.py` | Analytical fixed / moving block headway (OI-02 reporting interval, SYS-PRF-02 latency) | TC-TC-07 → SYS-TC-02, SYS-PRF-03 |
| 2 Real layout | `src/golsim/blocking.py`, `src/golsim/railjson_path.py` | Path rebuilt on the RailJSON track graph; BAL blocking times as in OSRD; delay propagation with holds | TC-TC-07, TC-SUP-01 |
| 3 Delay propagation | `src/golsim/propagation.py` | Both directions, rolling-stock circulation, Union recovery, in-section stop penalty (CR-014) | TC-SUP-01 → SYS-SUP-03/04 |
| 3 KPI | `src/golsim/passengers.py` | Weighted passenger delay (OI-12) | SYS-SUP-04 |
| Real corridor | `src/golsim/corridor_real.py`, `src/golsim/osrd_export.py` | Real stops, profiles with the right driving rules, headways on the real layout | — |

## Reproduce

```bash
pip install -r requirements.txt
python -m pytest                                   # UT-01 ... UT-19
python scripts/run_module3_real.py                 # v0.3 results on the real corridor -> outputs/v03/
python scripts/val03_cross_validation.py data/osrd/osrd_S1_export.csv S1_diesel_pushpull s1   # VAL-03
python scripts/val04_headway_real_signals.py       # VAL-04
python scripts/val05_incident.py                   # VAL-05 predictions
python scripts/stepwise_corridor.py data/osrd/osrd_S2_export.csv                                # S1 -> S2 attribution
```

`scripts/run_phase6.py`, `run_module3.py` and `run_recovery_s2.py` reproduce the v0.2 results on the synthetic
section and the equal-spacing corridor; they are kept for traceability and superseded by `run_module3_real.py`.

## Key results (v0.3)

- Journey Hamilton GO Centre – Oshawa GO: 149.6 min (S1) → 102.9 min (S2); Union operation −29.0, rolling stock −16.0, CBTC with ATO −1.6 min.
- Minimum headway: fixed block 580 s → moving block 174 s (−70 %; −65 to −77 % with 1–3 km blocks). TC-TC-07 passed.
- 30-min incident at Oakville–Clarkson, 15-min service: S2 44k weighted passenger-minutes on 16 sets; the realistic S1 (5-min Union dwell) 89k on 20 sets with comparable terminal slack.

## Known limitations

- Signals are generated from OpenStreetMap and are sparser than on the real corridor (ASM-11); fixed-block results are shown with a uniform-block sensitivity.
- Union station: missing platform detectors and a route data defect in the imported infrastructure (ASM-22); Union-internal thresholds are not validated.
- Westbound running times assumed equal to eastbound in Module 3 (ASM-23); rolling-stock and passenger values are assumptions (ASM-08, ASM-09, ASM-19).

## Data

`data/osrd/` holds the OSRD exports and the infrastructure topology used in phase 9. Contains information from
OpenStreetMap, © OpenStreetMap contributors, available under the Open Database License (ODbL).
Current-state service data: Metrolinx GO GTFS (see `docs/gtfs_baseline_2026-09-29.md`).

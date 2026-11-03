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

- Journey Hamilton GO Centre – Oshawa GO against a realistic baseline (5-min Union dwell, as in GO's current schedule, S1-5): 124.6 min → 102.9 min (S2); rolling stock −16.0, Union dwell 5 → 1 min −4.0, CBTC with ATO −1.6 min. The original brief assumed a 30-min Union dwell (S1, ASM-06), which gives 149.6 min and overstates the Union saving (−29.0 min); it is kept as a controlled baseline (CR-011).
- Signalling adds little journey time but a lot of capacity. Minimum headway on the same EMU: fixed block 580 s → moving block 174 s (−70 %; −65 to −77 % with 1–3 km blocks). TC-TC-07 passed.
- 30-min incident at Oakville–Clarkson, 15-min service: S2 44k weighted passenger-minutes on 16 sets; the realistic S1-5 with comparable terminal slack 40–49k on 20 sets with 1–2 km blocks (89k on the sparse generated signals). Disruption impact is comparable; S2's advantages are capacity and four fewer train sets.

## Known limitations

- Signals are generated from OpenStreetMap and are sparser than on the real corridor (ASM-11); fixed-block results are shown with a uniform-block sensitivity.
- Level track: the OpenStreetMap infrastructure carries no gradient or curve data, so golsim and OSRD both run on 0 ‰ (ASM-26). The OSRD cross-validation checks the calculation on identical inputs, not real-world running times.
- Not calibrated against actual train performance. Running times are 14–15 % (Lakeshore East Local) to 21–25 % (Lakeshore West Local) shorter than GO's current timetable for the closest comparable services.
- Rolling-stock performance values are estimates from public specifications (ASM-25); passenger values are assumptions (ASM-19).
- Union station: missing platform detectors and a route data defect in the imported infrastructure (ASM-22); Union-internal thresholds are not validated.
- Westbound running times assumed equal to eastbound in Module 3 (ASM-23).

All assumptions, open items and changes are listed in [`docs/assumptions.md`](docs/assumptions.md).

## Data

`data/osrd/` holds the OSRD exports and the infrastructure topology used in phase 9. Contains information from
OpenStreetMap, © OpenStreetMap contributors, available under the Open Database License (ODbL).
Current-state service data: Metrolinx GO GTFS (see `docs/gtfs_baseline_2026-09-29.md`).

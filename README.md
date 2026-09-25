# golsim — GO Lakeshore Line simulation toolkit (v0.2)

Phase 6 (design and implementation, EN 50126-1:2017) of the Lakeshore Line Modernization project.
golsim is the simulation model required as a precondition by the Simulation-level test cases in the DOORS
Test_Cases module (TC-TC-07, TC-SUP-01). Parameters are traced to the SRS and to the TBD resolution log (OI-xx).

## Modules

| Module | File | Purpose | DOORS link |
|---|---|---|---|
| 1a Running time | `src/golsim/dynamics.py` | Envelope method: traction, Davis resistance, gradient, braking, train-length rule | — |
| 1b ATP supervision | `src/golsim/braking.py` | Simplified ETCS-style curves: EBD, EBI, SBI, Warning, Permitted | SYS-TC-04, OI-06 |
| 2 Headway | `src/golsim/headway.py` | Plain-line and station headway, fixed vs moving block (OI-02 reporting interval and accuracy, SYS-PRF-02 latency) | TC-TC-07 → SYS-TC-02, SYS-PRF-03 |
| 3 Delay propagation | `src/golsim/propagation.py` | Event-based model: incident blockage, headway knock-on, Union recovery, rolling-stock circulation | TC-SUP-01 → SYS-SUP-03/04 |
| 3 KPI | `src/golsim/passengers.py` | Weighted passenger delay (connecting ×1.5, last service ×2.0) | OI-12, SYS-SUP-04 |

## ID conventions

- `SYS-*`, `URS-*`, `TC-*`: objects in the DOORS modules.
- `OI-*`: requirement-level TBD resolutions (TBD_resolution_log) — the master record for requirement values.
- `ASM-*`, `CR-*`, `OPEN-*`: model-only assumptions, changes and open items (assumption and change log).
- `UT-*`: model verification (is the model correct?). `SIM-*`: simulation runs used as requirement evidence.
  See `docs/traceability.csv`.

## Usage

```bash
pip install -r requirements.txt
python -m pytest                    # model verification UT-01 ... UT-16
python scripts/run_phase6.py        # Modules 1-2 -> outputs/results.md
python scripts/run_module3.py       # S3 disruption scenarios -> outputs/results_module3.md
python scripts/run_recovery_s2.py   # S2 recovery-time study -> outputs/results_recovery_s2.md
```

## Status and limitations

- **All corridor geometry is synthetic or approximated** (ASM-11, ASM-15); results are preliminary until the OSRD
  corridor model (phase 9) replaces it.
- Rolling-stock and passenger-load values are assumptions (ASM-08, ASM-09, ASM-19).
- Constant decelerations, no odometry confidence growth within a report interval, simplified blocking-time model.
- Module 3: no Union platform-capacity limit, no dispatcher interventions (short-turns, cancellations).

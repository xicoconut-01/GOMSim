# Assumptions and open items — golsim v0.3

This file is the English version of the project's assumption and change log (ASM-01 to ASM-24,
CR-001 to CR-015, OPEN-01 to OPEN-08). Config files, tests and `docs/traceability.csv` refer to
these IDs. When an assumption changes, update this file, re-run the tests and validation scripts,
and record the change as a CR.

- **ASM**: a condition the simulation relies on that is unverified or deliberately simplified.
- **CR**: a change request or decision relative to the original course-assignment baseline.
- **OPEN**: a parameter that has to be decided; placeholders are used until then.

"Effect" says whether the assumption makes results optimistic or pessimistic, so the
limitations of each result can cite it.

## Scenarios

| Scenario | Definition | Union operation | Rolling stock | Signalling |
|---|---|---|---|---|
| S1 current baseline | Hamilton GO Centre – Union as Lakeshore West, continuing as Lakeshore East to Oshawa GO | 30-min dwell (ASM-06); S1-5 variant with 5 min (CR-011) | MP40PHT-T4AC (MP54AC) diesel-electric + 12 BiLevel coaches, push-pull with a cab car at the other end | Existing fixed block (OSRD approximation) |
| S2 project target | Integrated Lakeshore Line, Local trains through-running end to end | Normal dwell only | Electrified, bi-level EMU, design speed 210 km/h | CBTC |
| S3 disruption | 30-min blockage applied to S1 and S2 | as S1 / S2 | as S1 / S2 | as S1 / S2 |

Between S1 and S2, step-by-step variants change one thing at a time (Union dwell, then rolling
stock, then signalling) so that each saving can be attributed separately (CR-005). Express and
Rapid services are conceptual only.

## Assumptions (ASM)

| ID | Category | Assumption | Reason | Source | Scenarios | Effect |
|---|---|---|---|---|---|---|
| ASM-01 | Scope | The west terminus is Hamilton GO Centre in every scenario | Through trains today mostly terminate at West Harbour or Aldershot and Hamilton GO Centre is peak-only; one terminus keeps scenarios comparable | Design decision; Railway Age | S1–S3 | Neutral |
| ASM-02 | Scope | The east terminus is Oshawa GO; the Bowmanville extension is excluded | Matches current service | Design decision | S1–S3 | Neutral |
| ASM-03 | Scope | Only end-to-end through trains are modelled; peak short-turn trains using yards near Union are excluded | Keeps scenarios clean and comparable | Design decision | S1–S3 | Optimistic (Union corridor load underestimated) |
| ASM-04 | Scope | Local trains only; Express and Rapid are conceptual | Focus on the Local service | Design decision | S2, S3 | Optimistic (no speed-difference conflicts) |
| ASM-05 | Scope | Only trains in the modelled timetable; VIA Rail, the Stouffville line sharing Lakeshore East, and other services are excluded | Focus on the through-running service layer | Design decision | S1–S3 | Optimistic (conflicts east of Union underestimated) |
| ASM-06 | Operations | In S1, trains dwell 30 min at Union for clearing, crew change, train-order change and cleaning | Observed in April 2023 during reduced service: through trains held at Union for about 30 and 28 min | Personal observation; Transit Toronto | S1 | **Does not match GTFS:** on 2026-09-29 the median scheduled Union dwell of 66 through links was 5 min, with only 4 at 30 min or more. Kept as a controlled baseline (CR-011); the 5-min S1-5 variant is the realistic case |
| ASM-07 | Operations | Terminal turnback is push-pull: the train reverses without turning, and the driver moves to the cab at the other end (locomotive or cab car); no run-round or locomotive repositioning | GO trains have a driving cab at both ends: the locomotive at one end, a cab car at the other | GO fleet | S1–S3 | Neutral |
| ASM-08 | Rolling stock | S1 traction is an MP40PHT-T4AC (technical model MP54AC) diesel-electric locomotive | User-specified; GO classes the MP54AC as MP40PHT-T4AC | GO fleet | S1 | Neutral |
| ASM-09 | Rolling stock | S2 bi-level EMU parameters are assumed, based on existing bi-level EMU products | GO has no EMUs today | Assumption | S2, S3 | Uncertain |
| ASM-10 | Rolling stock | S2 speed is limited by line speed; 210 km/h is the vehicle's design capability and does not affect Local running times | Lakeshore East limit 153 km/h and short station spacing | Lakeshore East | S2, S3 | Neutral |
| ASM-11 | Infrastructure | The line model is generated from OpenStreetMap with osm_to_railjson; missing signals are generated with --generate-signals and are not the real layout | No public real signal layout | OSRD documentation | S1–S3 | Uncertain |
| ASM-12 | Signalling | S1 fixed block is approximated by OSRD's existing signalling system; the headway effect of CBTC moving block is quantified by the Python model | OSRD support for moving block not confirmed | Design decision | S2, S3 | Uncertain |
| ASM-13 | Method | In OSRD, S3 is observed by shifting the delayed train's times; multi-round delay propagation is done in the Python model | OSRD's automatic delay propagation not confirmed | Design decision | S3 | Neutral |
| ASM-14 | Reference | The official GO Expansion option (ETCS Level 2, electric locomotives, refurbished bi-level coaches) is a qualitative reference, not simulated; the differences are analysed in the TBD resolution log | This project is an alternative-option study | GO Expansion technology as learned in interviews; TBD resolution log. An IRJ report of Level 1 was not adopted | Phase 1 option comparison | Neutral |
| ASM-15 | Method | Module 3 (v0.1–v0.2) approximates the corridor as equally spaced stations: Lakeshore West 64.2 km in 11 sections, Lakeshore East 50.1 km in 9. Superseded in v0.3 by real stop positions (CR-015) | No real station positions before phase 9 | Line lengths from Transit Toronto; spacing approximate | S3 | Uncertain |
| ASM-16 | Incident | S1 incident: a level-crossing incident between Hamilton and Union, line blocked for 30 min | Typical failure mode of today's diesel line | Design decision | S3 (S1) | Neutral |
| ASM-17 | Incident | S2 incident: a foreign object on the overhead contact system between Hamilton and Union, line blocked for 30 min; S2 implies no level crossings in that section | Typical failure mode of an electrified line | Design decision | S3 (S2) | Neutral |
| ASM-18 | Incident | Both incidents are in the same section (Oakville–Clarkson on the real line, about 30.4–38.2 km; the 6th section from Hamilton on the phase 6 synthetic line), start 90 min after the first departure, block both directions, and have no dispatcher intervention (no short turns, no cancellations) | Comparability; removes human dispatching as a variable | Design decision | S3 | Pessimistic (no dispatching intervention) |
| ASM-19 | Passengers | 400 passengers per trip; 50 % alight at Union, of whom 60 % connect onward; the rest alight evenly at other stations; OI-12 weights (connecting 1.5, last service 2.0) | Module 3's KPI needs a passenger distribution; no real OD data | Assumption; weights from OI-12 | S3 | Uncertain |
| ASM-20 | Method | OSRD vehicles are aligned with golsim: start-up time 0 s; const_gamma set to golsim's service deceleration; BAL stands in for the existing fixed block; in VAL-03, S2 runs as a non-electric proxy with identical curves | Cross-validation compares the models, not the inputs; the OpenStreetMap data has no catenary | Design decision; checked against the vehicle format of OSRD commit 4a1a8bd | VAL-03 | Neutral |
| ASM-21 | Infrastructure | In OSRD the Oshawa terminus is a location on the GO platform track (picked on the map), not the imported Oshawa operational point; golsim uses the same chainage | The track of the imported Oshawa operational point lacks block sections ("Missing block") | VAL-02 investigation | VAL-03, VAL-04 | Neutral |
| ASM-22 | Method | Single-train Union "Itineraries" conflicts in OSRD are treated as infrastructure data defects and excluded; conflict-count criteria count only conflicts between two or more trains | Unrelated to headway, dwell or Union track (8 or 7); a train cannot conflict with itself | VAL-02 to VAL-03 investigation | CV-4, TC07-4, VAL-05 | Optimistic (if the defect hides a real throat constraint) |
| ASM-23 | Method | On the real corridor, Module 3 takes westbound section running times equal to eastbound | Only the eastbound path was built in OSRD | Design decision | S3 (v0.3) | Uncertain |
| ASM-24 | Method | Module 3 uses the binding corridor minimum headway as one headway: S1 690 s (fixed block on generated signals), S2 174 s (moving block); the timetable is built mechanically on a 15-min grid, so terminal slack depends on journey time | Module 3 does not resolve blocks section by section; that is done in blocking.py and confirmed by VAL-05 | Design decision | S3 (v0.3) | Pessimistic for S1 |
| ASM-25 | Rolling stock | S1 and S2 performance values — tractive effort, power at rail, Davis resistance A/B/C, service and emergency braking, ATP timings — are estimates from public specifications, not manufacturer or Metrolinx data. S1 power at rail (3,200 kW) is to be checked against MP40PH-3C and MP54AC specifications | No fleet performance data available | Assumption (added 2026-11-03) | S1–S3 | Optimistic if traction or braking is overstated (running times too short) |
| ASM-26 | Infrastructure | Level track: none of the 3,150 track sections in the OSRD topology carries slope or curve data, so golsim and OSRD both run with 0 ‰ gradient | OpenStreetMap carries no gradient data | VAL-03 data check (added 2026-11-03) | S1–S3 | Optimistic (running times too short); the OSRD comparison checks the calculation, not real running times |

## Open items (OPEN)

| ID | Item | Decision needed | Blocks | Status |
|---|---|---|---|---|
| OPEN-01 | Consist | Number of bi-level coaches in S1 (peak 12 or shorter off-peak); S2 EMU length | Running time, platform-length check | Placeholder: 12 cars |
| OPEN-02 | Frequency | S1 current frequency; whether S2 uses the 15-min two-way all-day target | Timetable, conflict detection | Partly closed 2026-09-25: S2 uses 15 min; S1 run at both 30 and 15 min |
| OPEN-03 | Stopping pattern | List of Local stops; whether planned stations such as East Harbour are included | Timetable | Open |
| OPEN-04 | Terminal turnback | Minimum turnback at Hamilton GO Centre and Oshawa GO | Terminal conflict detection | Placeholder: 600 s (S1), 300 s (S2) |
| OPEN-05 | Minimum Union work time | Lower bound for the ASM-06 sensitivity | S1 sensitivity | Placeholder: 600 s |
| OPEN-06 | EMU parameters | S2 starting acceleration, service and emergency braking, mass | Running time, ATP curves | Open (see ASM-09, ASM-25) |
| OPEN-07 | Delay parameters | Which train, how long and where to inject the S3 delay | S3 | Closed 2026-09-25: see ASM-16 to ASM-18 |
| OPEN-08 | Option rationale | Why CBTC rather than ETCS, why EMU rather than electric locomotives | Phase 1 option comparison | Open |

## Changes (CR)

| ID | Change |
|---|---|
| CR-001 | Add implementation (phase 6) and simulation-based validation (phase 9) to the original assignment |
| CR-002 | Two tools: Python for principle-level models, OSRD for corridor-level simulation, cross-validated on the same section |
| CR-003 | Define the three scenarios S1 baseline, S2 target, S3 disruption |
| CR-004 | Narrow the scope to end-to-end through-running Local trains |
| CR-005 | Add step-by-step attribution variants between S1 and S2 |
| CR-006 | Organise the project on the EN 50126-1:2017 lifecycle; phases 7, 8 and 10–12 not applicable |
| CR-007 | Compare against the official GO Expansion option (phase 1) |
| CR-008 | S3 injects each scenario's typical incident into S1 and S2 separately, 30 min each |
| CR-009 | Add an S2 recovery-time study: Union recovery, running-time supplement, terminal slack and combinations |
| CR-010 | golsim v0.2: parameters traced to the SRS and OI; OI-02 reporting interval and accuracy in moving block; OI-12 weighted passenger delay as the Module 3 KPI |
| CR-011 | GTFS shows a 5-min median through dwell at Union and peak-only express service at Hamilton GO Centre; keep S1 as defined as a controlled baseline and add the S1-5 variant (Union 5 min) |
| CR-012 | Driver margins under lineside signalling: a lower limit is respected 100 m before it, acceleration waits 50 m after it (S1 only) |
| CR-013 | Safety approach into a buffer stop: 30 km/h over the last 200 m, 10 km/h over the last 100 m (S1 only); Oshawa terminus moved to the GO stub track |
| CR-014 | A train inside the blocked section brakes to a stand and restarts from standstill, instead of pausing at speed |
| CR-015 | Release golsim v0.3: Module 3 on the OSRD-validated real corridor; v0.2 synthetic results kept for traceability |

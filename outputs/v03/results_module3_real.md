# Module 3 on the real corridor — golsim v0.3

Corridor: OSRD-validated path Hamilton GO Centre – Oshawa GO (116.130 km, 21 stops). Incident Oakville–Clarkson 90 to 120 min after the first departure, both directions. Primary KPI: weighted passenger delay (OI-12).

## Minimum headways on the real layout

| Scenario | Signalling | Minimum headway (s) | Binding location (km) |
|---|---|---|---|
| S1 | fixed block (generated BAL signals) | 690 | 86.1 |
| S1-5 | fixed block (generated BAL signals) | 690 | 86.1 |
| S2 | moving block (CBTC) | 174 | 64.8 |

## Disruption (S3)

| Run | Weighted pax delay (pax-min) | Late trips (>5 min) | Train delay (train-min) | Max delay (min) | Max delay leaving Union E (min) | Fleet (sets) | Terminal slack (min) |
|---|---|---|---|---|---|---|---|
| S1 @ 30 min, baseline | 0 | 0 | 0 | 0.0 | 0.0 | 12 | 20.4 |
| S1 @ 30 min, incident | 12,578 | 2 | 16 | 8.4 | 7.4 | 12 | 20.4 |
| S1 @ 15 min, baseline | 0 | 0 | 0 | 0.0 | 0.0 | 22 | 5.4 |
| S1 @ 15 min, incident | 40,742 | 2 | 26 | 8.4 | 7.4 | 22 | 5.4 |
| S1-5 @ 15 min, baseline | 0 | 0 | 0 | 0.0 | 0.0 | 18 | 0.4 |
| S1-5 @ 15 min, incident | 251,975 | 34 | 696 | 31.6 | 31.2 | 18 | 0.4 |
| S2 @ 15 min, baseline | 0 | 0 | 0 | 0.0 | 0.0 | 16 | 12.1 |
| S2 @ 15 min, incident | 43,690 | 9 | 125 | 31.2 | 31.2 | 16 | 12.1 |
| S1-5 @ 15 min, slack matched, baseline | 0 | 0 | 0 | 0.0 | 0.0 | 20 | 15.4 |
| S1-5 @ 15 min, slack matched, incident | 89,364 | 20 | 344 | 31.6 | 27.4 | 20 | 15.4 |

## Sensitivity: S1-5 @ 15 min against the fixed-block layout

| Block layout | S1 minimum headway (s) | Weighted pax delay (pax-min) | Late trips | Train delay (train-min) |
|---|---|---|---|---|
| Generated signals (OSRD) | 690 | 251,975 | 34 | 696 |
| Uniform 2.0 km | 421 | 148,276 | 20 | 397 |
| Uniform 1.5 km | 371 | 138,629 | 18 | 371 |
| Uniform 1.0 km | 244 | 120,752 | 17 | 322 |

## S2 recovery options (15-min service, same incident)

| Option | Weighted pax delay (pax-min) | Added journey (min) | Fleet (sets) | Late trips | Train delay (train-min) |
|---|---|---|---|---|---|
| Terminal +13 min | 26,875 | 0.0 | 18 | 5 | 89 |
| Union +5 min & terminal +13 min | 29,636 | 5.0 | 18 | 5 | 98 |
| No recovery | 43,690 | 0.0 | 16 | 9 | 125 |
| Running +5 % | 55,035 | 4.2 | 16 | 9 | 154 |
| Union +5 min | 57,319 | 5.0 | 16 | 9 | 142 |

Natural terminal slack of the 15-min grid: 12.1 min above the minimum turnback.

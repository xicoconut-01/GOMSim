# Phase 6 results (synthetic reference section — not the real corridor)

## Running time (Module 1a)

| Train | Section times (s) | Running (s) | With dwell (s) |
|---|---|---|---|
| S1 diesel push-pull | 211, 195, 269, 270 | 946 | 1126 |
| S2 bi-level EMU | 164, 151, 235, 213 | 763 | 943 |

**ASM-10 check:** S2 running time with 210 km/h design speed = 763 s, capped at 150 km/h = 763 s (difference +0 s).

**Gain decomposition (S1 -> S2 = 182 s):** traction/acceleration 139 s, service braking 43 s.

## ATP supervision (Module 1b)

| Train | From (km/h) | EBD (m) | EBI (m) | SBI (m) | Permitted (m) |
|---|---|---|---|---|---|
| S1 diesel push-pull | 80 | 274 | 392 | 470 | 559 |
| S1 diesel push-pull | 120 | 616 | 781 | 897 | 1030 |
| S1 diesel push-pull | 150 | 965 | 1163 | 1309 | 1476 |
| S2 bi-level EMU | 80 | 205 | 266 | 299 | 388 |
| S2 bi-level EMU | 120 | 462 | 543 | 593 | 726 |
| S2 bi-level EMU | 150 | 723 | 820 | 883 | 1049 |

## Line headway (Module 2a)

| Case | Minimum (s) | at speed (km/h) | at 145 km/h (s) |
|---|---|---|---|
| S1 fixed block | 103 | 145 | 103 |
| S2 fixed block | 102 | 145 | 102 |
| S2 moving block (CBTC) | 37 | 110 | 38 |

**Reporting-interval sensitivity (S2 moving block, OI-02):**

| Report interval (s) | Line headway at 110 km/h (s) | Station headway, 60 s dwell (s) |
|---|---|---|
| 0.5 | 37.1 | 124.9 |
| 1.0 | 37.6 | 125.4 |
| 2.0 | 38.6 | 126.4 |
| 5.0 | 41.6 | 129.4 |

## Union station headway and platform demand at 15-min service (Module 2b)

| Variant | Station headway (s) | Platform tracks per direction |
|---|---|---|
| S1: fixed, 30 min Union dwell | 1973 | 3 |
| S1a: fixed, 60 s dwell | 233 | 1 |
| S1b: EMU, fixed, 60 s dwell | 217 | 1 |
| S2: EMU, CBTC, 60 s dwell | 125 | 1 |

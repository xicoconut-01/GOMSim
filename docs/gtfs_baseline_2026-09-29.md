# Current-state baseline from GO Transit GTFS

Source: Metrolinx GO Transit GTFS, feed_version 20260921115700 (published 2026-09-21, valid 2026-09-21 to 2026-11-27),
used under the Metrolinx Access and Use Agreement. Service day analysed: **Tuesday 2026-09-29** (OI-08 dated baseline).

## Lakeshore Local stopping patterns

| Pattern | Stops | Trips/day/direction | Scheduled run time |
|---|---|---|---|
| LE Local Durham College Oshawa GO - Union | OS-WH-AJ-PIN-RO-GU-EG-SC-DA-UN | 41 | 62-63 min |
| LW Local Aldershot - Union | AL-BU-AP-BO-OA-CL-PO-LO-MI-EX-UN | 16-17 | 68-72 min |
| LW Hamilton GO Centre - Union (peak only, express) | HA-AL-BU-AP-BO-OA-CL-UN | 4 (AM inbound, PM outbound) | 75-76 min |

## Frequency

Off-peak: 2 trains per hour per direction on each line (30-min service). Peak towards Union (AM) / from Union (PM): up to 5-6 trains per hour.

## Through-running at Union (same block_id, arrival on one line, departure on the other)

Union links: 71; line-changing (through-running): 66; same-line turnbacks: 5.
Scheduled Union dwell of through links: median 5 min, 75th percentile 5 min; 62 of 66 links at 12 min or less; 4 links of 30 min or more (midday storage and one 35-min off-peak link).


# VAL-03 cross-validation — S1_diesel_pushpull

OSRD export: export-S1A-final_output.csv; path length 116.130 km; 21 stops; terminal on buffer stop: yes (safety approach speed applied).

**CV-1** end-to-end running time: OSRD 6092 s, golsim 6093 s, difference +0.01 % -> PASS (limit +/-3 %)
**CV-2** interstation times: 20 of 20 within tolerance -> PASS
**CV-3** interstation max speed: 20 of 20 within +/-5 km/h -> PASS

| From | To | km | OSRD (s) | golsim (s) | Diff (s) | Diff (%) | CV-2 | Vmax OSRD | Vmax golsim | CV-3 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hamilton GO Centre | Aldershot | 9.39 | 658 | 661 | +3 | +0.4 | pass | 109 | 109 | pass |
| Aldershot | Burlington | 4.69 | 233 | 233 | -0 | -0.2 | pass | 119 | 119 | pass |
| Burlington | Appleby | 6.12 | 274 | 274 | -1 | -0.2 | pass | 130 | 130 | pass |
| Appleby | Bronte | 5.19 | 248 | 247 | -0 | -0.2 | pass | 123 | 123 | pass |
| Bronte | Oakville | 5.00 | 242 | 242 | -0 | -0.2 | pass | 122 | 122 | pass |
| Oakville | Clarkson | 7.81 | 320 | 319 | -1 | -0.2 | pass | 140 | 140 | pass |
| Clarkson | Port Credit | 6.15 | 275 | 275 | -0 | -0.2 | pass | 130 | 130 | pass |
| Port Credit | Long Branch | 5.00 | 242 | 242 | -0 | -0.2 | pass | 122 | 122 | pass |
| Long Branch | Mimico | 5.12 | 246 | 245 | -0 | -0.2 | pass | 123 | 123 | pass |
| Mimico | Exhibition | 7.22 | 315 | 315 | -0 | -0.1 | pass | 129 | 129 | pass |
| Exhibition | Toronto Union Station | 3.29 | 311 | 312 | +1 | +0.3 | pass | 92 | 92 | pass |
| Toronto Union Station | Danforth | 8.92 | 620 | 622 | +2 | +0.4 | pass | 124 | 124 | pass |
| Danforth | Scarborough | 5.27 | 250 | 249 | -0 | -0.2 | pass | 124 | 124 | pass |
| Scarborough | Eglinton | 3.17 | 184 | 184 | -0 | -0.2 | pass | 105 | 105 | pass |
| Eglinton | Guildwood | 3.28 | 188 | 187 | -0 | -0.2 | pass | 106 | 106 | pass |
| Guildwood | Rouge Hill | 6.33 | 280 | 280 | -1 | -0.2 | pass | 131 | 131 | pass |
| Rouge Hill | Pickering | 7.22 | 342 | 343 | +0 | +0.1 | pass | 125 | 125 | pass |
| Pickering | Ajax | 3.90 | 208 | 208 | -0 | -0.2 | pass | 112 | 112 | pass |
| Ajax | Whitby | 8.70 | 343 | 342 | -1 | -0.2 | pass | 137 | 137 | pass |
| Whitby | requested destination | 4.36 | 314 | 315 | +1 | +0.5 | pass | 112 | 113 | pass |

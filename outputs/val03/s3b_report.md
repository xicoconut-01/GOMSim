# VAL-03 cross-validation — S2_bilevel_emu

OSRD export: export-S2-final_output.csv; path length 116.130 km; 21 stops; terminal on buffer stop: yes (safety approach speed applied).

**CV-1** end-to-end running time: OSRD 5128 s, golsim 5130 s, difference +0.06 % -> PASS (limit +/-3 %)
**CV-2** interstation times: 20 of 20 within tolerance -> PASS
**CV-3** interstation max speed: 20 of 20 within +/-5 km/h -> PASS

| From | To | km | OSRD (s) | golsim (s) | Diff (s) | Diff (%) | CV-2 | Vmax OSRD | Vmax golsim | CV-3 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hamilton GO Centre | Aldershot | 9.39 | 626 | 629 | +3 | +0.4 | pass | 129 | 129 | pass |
| Aldershot | Burlington | 4.69 | 186 | 186 | -0 | -0.2 | pass | 129 | 129 | pass |
| Burlington | Appleby | 6.12 | 214 | 213 | -0 | -0.2 | pass | 153 | 153 | pass |
| Appleby | Bronte | 5.19 | 192 | 192 | -0 | -0.1 | pass | 153 | 153 | pass |
| Bronte | Oakville | 5.00 | 191 | 191 | -0 | -0.2 | pass | 153 | 153 | pass |
| Oakville | Clarkson | 7.81 | 254 | 253 | -0 | -0.2 | pass | 153 | 153 | pass |
| Clarkson | Port Credit | 6.15 | 214 | 214 | -0 | -0.1 | pass | 153 | 153 | pass |
| Port Credit | Long Branch | 5.00 | 191 | 190 | -0 | -0.2 | pass | 153 | 153 | pass |
| Long Branch | Mimico | 5.12 | 190 | 190 | -0 | -0.2 | pass | 153 | 153 | pass |
| Mimico | Exhibition | 7.22 | 271 | 270 | -0 | -0.1 | pass | 129 | 129 | pass |
| Exhibition | Toronto Union Station | 3.29 | 290 | 291 | +1 | +0.3 | pass | 97 | 98 | pass |
| Toronto Union Station | Danforth | 8.92 | 580 | 582 | +2 | +0.4 | pass | 153 | 153 | pass |
| Danforth | Scarborough | 5.27 | 197 | 197 | -0 | -0.2 | pass | 150 | 151 | pass |
| Scarborough | Eglinton | 3.17 | 143 | 143 | -0 | -0.2 | pass | 137 | 137 | pass |
| Eglinton | Guildwood | 3.28 | 148 | 148 | -0 | -0.2 | pass | 132 | 132 | pass |
| Guildwood | Rouge Hill | 6.33 | 230 | 230 | -0 | -0.2 | pass | 143 | 143 | pass |
| Rouge Hill | Pickering | 7.22 | 289 | 290 | +0 | +0.1 | pass | 149 | 149 | pass |
| Pickering | Ajax | 3.90 | 162 | 162 | -0 | -0.2 | pass | 137 | 137 | pass |
| Ajax | Whitby | 8.70 | 289 | 288 | -1 | -0.2 | pass | 137 | 137 | pass |
| Whitby | requested destination | 4.36 | 270 | 271 | +2 | +0.6 | pass | 137 | 137 | pass |

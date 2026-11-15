# Data: nasturtium leaves in low vs high humidity (Days 1–26)

Two terrariums, 21 Sep – 16 Oct 2026 (Day 1 = 21 Sep):

- **mh** = Low humidity, Melbourne-like (about 50–55% relative humidity most of the time; 68% on Days 11–16)
- **sh** = High humidity, Singapore-like (about 90–96%)

Each tagged leaf (L01–L14, by tag colour) was photographed once a day on 5 mm grid paper. Leaf IDs are separate in
the two tanks: `mh_L02` and `sh_L02` are different leaves. Leaves that died were replaced by new ones with new
tags. IDs look like `mh_L02_D05` = Low tank, leaf L02, Day 5. 263 photos in total.

| File | What it is |
|---|---|
| `mh-sh_L01-L14_D01-D26_combined_v6.tps` | 13 landmarks per photo (tpsDig format, y measured up from the bottom), with IMAGE, ID and SCALE (mm per pixel). Opens in MorphoJ. Landmark 1 = vein hub (clicked by hand); 2 = where the line from the leaf's centre through the hub meets the edge; 3–13 = every 30° clockwise from the hub. |
| `mh-sh_L01-L14_D01-D26_specimens_v6.csv` | One row per photo: tank, leaf, tag colour, day, first day of that leaf, whether it was an original leaf or a replacement, centroid size (px and mm) and where the scale came from. |
| `leaf_colour_v4.csv` | Greenness per photo: `gcc` = G/(R+G+B) inside the leaf after white-balancing to the paper; `yellow_pct` = % of the leaf that is yellow-brown; `glare_pct` = % very pale (glare); `traced` = the outline was traced by hand. |
| `leaf_area_perimeter_v4.csv` | Area (mm²), perimeter (mm) and roundness (4π·area/perimeter²) of each outline; `outline_source` = automatic or hand-traced. |
| `plan_D17-D26_results_v2.csv` | Results of the analysis planned before the Days 17–26 data existed: tank means, Low − High difference, 95% confidence interval, exact permutation p-value and the smallest difference the test could detect (80% power), by period (A = Days 2–10, B = 11–16, C = 17–26). |
| `plan_D17-D26_per_leaf_v2.csv` | The per-leaf values behind those results (one value per leaf and period: the leaf is the unit, not the photo). |
| `growth_summary_D01-D26_v1.csv` | Growth in size (% per day) by period and tank, and total growth of the leaves followed longest. |
| `tank_conditions_daily_v2.csv`, `tank_conditions_hourly_v2.csv` | Temperature, relative humidity and vapour-pressure deficit (VPD) in each tank, from the sensor log. |
| `sensor_log_raw_to_D28.csv` | The raw sensor log (two DHT temperature/humidity sensors and a PM sensor). DHT1 = High tank, DHT2 = Low tank (worked out from the readings: DHT1 was the more humid one in every paired hour of Days 1–10). The Low tank's sensor has a gap from late Day 22 to early Day 25. |

The analysis code that made these files is in `code/scripts` in this repository.

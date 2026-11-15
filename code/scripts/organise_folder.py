"""Move the morpho project files into a tidy folder layout (moves only: nothing is
deleted or renamed). Writes 4_docs/move_log_2026-10-07.csv (old path -> new path).
Usage: python organise_folder.py <morpho folder> [--run]   (without --run = dry run)
"""
import csv
import os
import re
import shutil
import sys

root = sys.argv[1]
run = "--run" in sys.argv

rules = [  # (regex on a top-level file name, destination folder) - first match wins
    (r"^L\d\d_D\d\d_(mh|sh)(_v2)?\.jpg$", "1_photos_tpsdig"),
    (r"^L0[1-5]_(mh|sh)_D01-D03\.tps$", "1_photos_tpsdig"),
    (r"^(L01-L10_sh_D04-D09|L02-L09_mh_D04-D10|L07_D08_mh_v2)\.tps$", "1_photos_tpsdig"),
    (r"^(L01_sh_D01-D03_hub|L01-L10_sh_D04-D09_hub_v2|L02-L09_mh_D04-D10_hub_v4)\.tps$", "1_photos_tpsdig"),
    (r"^(mh-sh_L01-L10_D01-D10_scale-list|ME_3photos_x3)\.tps$", "1_photos_tpsdig"),
    (r"^L0[1-5]_(mh|sh)_D01-D03_auto_v3\.tps$", "2_landmarks"),
    (r"^(L01-L10_sh_D04-D09|L02-L09_mh_D04-D10)_auto_v3\.tps$", "2_landmarks"),
    (r"^mh-sh_L01-L10_D01-D10_combined_v1\.tps$", "2_landmarks"),
    (r"^(Leaf_shape_progress_report_v1\.xlsx|morphoJresultsdata\.xlsx|mh-sh_L01-L10_D01-D10_specimens_v1\.csv|"
     r"growth_per_leaf_PRELIM_v1\.csv|leaf_colour_v1\.csv)$", "3_results"),
    (r"^(PlanV2 \(2\)\.docx|photo_log_mh_D04-D10_v2\.csv|photo_log_sh_D04-D09\.csv)$", "4_docs"),
    (r"^(humidity-20261006T000602Z-1-001\.zip|sh_zip file\.zip|IMG_4685\.jpg|IMG_4711 2\.jpg|day1_white_melhum\.jpg)$", "originals"),
    (r"^(my_output\.tps|output_auto\.tps|my_check_sheet\.jpg|output_check\.jpg|Windows PowerShell_pythonrunmorphooutlined1-10\.txt)$",
     "your_test_runs"),
    (r"^(FIX_.*\.tps|L0\d_D0\d_mh_fixguide\.jpg|L04_D0\d_mh_rep\d\.TPS|L04_mh\.morphoj|leaf_combined\.tps|test_traced1\.1\.TPS|"
     r"leaf4_day1_landmarks.*\.TPS|photo_log_mh_D04-D10\.csv|L07_D08_mh_v2_hub\.tps|"
     r".*_auto\.tps|.*_auto_v2\.tps|L01_sh_D01-D03_digitised\.tps|"
     r"L01-L10_sh_D04-D09_hub\.tps|L02-L09_mh_D04-D10_hub(_v2|_v3)?\.tps)$", "old_versions"),
]
KEEP = {"scripts"}

moves, unassigned = [], []
for name in sorted(os.listdir(root)):
    src = os.path.join(root, name)
    if os.path.isdir(src):
        if name == "digitise":
            ap = os.path.join(src, "auto_pilot")
            for f in sorted(os.listdir(ap)):
                if re.match(r"^(L0[1-5]_(mh|sh)_check_v3|L01-L10_sh_D04-D09_check_v3|L02-L09_mh_D04-D10_check_v3)\.jpg$", f):
                    moves.append((os.path.join(ap, f), os.path.join(root, "3_results", "check_sheets", f)))
            moves.append((src, os.path.join(root, "old_versions", "digitise")))   # the rest of digitise/, whole
        elif name not in KEEP and not re.match(r"^(1_photos_tpsdig|2_landmarks|3_results|4_docs|originals|your_test_runs|old_versions)$", name):
            unassigned.append(name + "/")
        continue
    dest = next((d for pat, d in rules if re.match(pat, name)), None)
    if dest:
        moves.append((src, os.path.join(root, dest, name)))
    else:
        unassigned.append(name)

clash = [d for s, d in moves if os.path.exists(d)]
counts = {}
for s, d in moves:
    k = os.path.relpath(os.path.dirname(d), root)
    counts[k] = counts.get(k, 0) + 1
for k in sorted(counts):
    print(f"  {k:28} {counts[k]:3} item(s)")
print("unassigned:", unassigned or "none")
print("would overwrite:", clash or "none")
if unassigned or clash:
    sys.exit("stopped: fix the rules first")
if not run:
    print("dry run only")
    sys.exit()

log = []
for s, d in moves:          # check sheets first (they live inside digitise/), then the rest
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.move(s, d)
    log.append((os.path.relpath(s, root), os.path.relpath(d, root)))
with open(os.path.join(root, "4_docs", "move_log_2026-10-07.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["old_location", "new_location"])
    w.writerows(log)
print(f"moved {len(log)} items; log written to 4_docs/move_log_2026-10-07.csv")

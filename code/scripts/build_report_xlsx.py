"""Build the progress report as an Excel workbook (report sheets + data sheets).
Numbers that come from the data sheets are Excel formulas; numbers from MorphoJ or
the Python permutation tests are typed in and their source is noted next to them.
Usage: python build_report_xlsx.py <out.xlsx>   (run from the morpho\\scripts folder)
"""
import csv
import sys

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

F = "Arial"
BODY, BOLD = Font(name=F, size=10), Font(name=F, size=10, bold=True)
TITLE, H2 = Font(name=F, size=14, bold=True), Font(name=F, size=12, bold=True)
NOTE = Font(name=F, size=9, italic=True, color="595959")
LINK = Font(name=F, size=10, color="0563C1", underline="single")
HEAD_FILL = PatternFill("solid", fgColor="D9E1F2")
WRAP = Alignment(wrap_text=True, vertical="top")
THIN = Border(bottom=Side(style="thin", color="BFBFBF"))

wb = Workbook()
wb.remove(wb.active)


def sheet(name, widths):
    ws = wb.create_sheet(name)
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    return ws


def put(ws, row, values, font=BODY, fill=None, wrap=True):
    for c, v in enumerate(values, 1):
        cell = ws.cell(row=row, column=c, value=v)
        cell.font = font
        if wrap:
            cell.alignment = WRAP
        if fill:
            cell.fill = fill
    return row + 1


def table(ws, row, header, rows):
    row = put(ws, row, header, BOLD, HEAD_FILL)
    first = row
    for r in rows:
        row = put(ws, row, r)
        for c in range(1, len(header) + 1):
            ws.cell(row=row - 1, column=c).border = THIN
    return row, first


def heading(ws, row, text, font=H2):
    ws.cell(row=row, column=1, value=text).font = font
    return row + 1


def read_csv(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


# ---------------- data sheets ----------------
spec = read_csv("../3_results/mh-sh_L01-L10_D01-D10_specimens_v2.csv")
ws = sheet("Specimens", [12, 10, 7, 18, 6, 10, 12, 18, 20, 14, 14, 36, 30])
cols = ["ID", "condition", "leaf", "tag", "day", "first_day_of_leaf", "days_since_first_photo",
        "original_leaf", "image", "centroid_size_px", "centroid_size_mm", "source_file", "scale_source"]
put(ws, 1, cols, BOLD, HEAD_FILL, wrap=False)
for i, r in enumerate(spec, 2):
    vals = [r["ID"], r["condition"], r["leaf"], r["tag"], int(r["day"]), int(r["first_day_of_leaf"]),
            int(r["days_since_first_photo"]), r["original_leaf"], r["image"], float(r["centroid_size_px"]),
            float(r["centroid_size_mm"]), r["source_file"], r["scale_source"]]
    put(ws, i, vals, wrap=False)
    ws.cell(row=i, column=10).number_format = "0.0"
    ws.cell(row=i, column=11).number_format = "0.00"
ws.freeze_panes = "A2"
N_SPEC = len(spec) + 1                                     # last data row

col = read_csv("../3_results/leaf_colour_v1.csv")
ws = sheet("Colour per photo", [12, 10, 7, 6, 20, 10, 11, 10, 8])
put(ws, 1, ["ID", "condition", "leaf", "day", "image", "greenness_gcc", "yellow_pct", "glare_pct", "traced"],
    BOLD, HEAD_FILL, wrap=False)
for i, r in enumerate(col, 2):
    put(ws, i, [r["ID"], r["condition"], r["leaf"], int(r["day"]), r["image"], float(r["gcc"]),
                float(r["yellow_pct"]), float(r["glare_pct"]), r["traced"]], wrap=False)
    ws.cell(row=i, column=6).number_format = "0.000"
ws.freeze_panes = "A2"
N_COL = len(col) + 1

gro = read_csv("../3_results/growth_per_leaf_v2.csv")
ws = sheet("Growth per leaf", [10, 10, 9, 9, 9, 18])
put(ws, 1, ["leaf", "condition", "n_photos", "first_day", "last_day", "growth_pct_per_day"], BOLD, HEAD_FILL, wrap=False)
for i, r in enumerate(gro, 2):
    put(ws, i, [r["leaf"], r["condition"], int(r["n_photos"]), int(r["first_day"]), int(r["last_day"]),
                float(r["growth_pct_per_day"])], wrap=False)
    ws.cell(row=i, column=6).number_format = "+0.00;-0.00;0.00"
N_GRO = len(gro) + 1
ws.cell(row=N_GRO + 2, column=1, value="Source: slope of ln(centroid size, mm) against day for each leaf with 3+ photos, "
        "computed by scripts\\growth_allometry.py, using the scales re-measured on 7 Oct 2026.").font = NOTE
ws.freeze_panes = "A2"

S = lambda c: f"Specimens!${c}$2:${c}${N_SPEC}"
C = lambda c: f"'Colour per photo'!${c}$2:${c}${N_COL}"
G = lambda c: f"'Growth per leaf'!${c}$2:${c}${N_GRO}"

# ---------------- Leaves ----------------
leaves = [
    ("mh", "L01", "red", "Original", "Yes", "Shrivelled; replaced Day 4"),
    ("mh", "L02", "yellow", "Original", "No", "Kept to Day 10"),
    ("mh", "L03", "green", "Original", "Yes", "Shrivelled; replaced Day 4"),
    ("mh", "L04", "white", "Original", "Yes", "Curled; replaced Day 7"),
    ("mh", "L05", "black", "Original", "Yes", "Shrivelled; replaced Day 4"),
    ("mh", "L06", "brown (muddy red)", "Replacement", "No", "Tagged Day 4"),
    ("mh", "L07", "pen", "Replacement", "No", "Tagged Day 4"),
    ("mh", "L08", "pencil", "Replacement", "No", "Tagged Day 4"),
    ("mh", "L09", "blue", "Replacement", "No", "Tagged Day 7"),
    ("sh", "L01", "red", "Original", "No", "Kept to Day 9 (Day 10 not uploaded)"),
    ("sh", "L02", "yellow", "Original", "Yes", "Damaged; replaced Day 4"),
    ("sh", "L03", "green", "Original", "Yes", "Damaged; replaced Day 5"),
    ("sh", "L04", "white", "Original", "No", "Kept to Day 9 (Day 10 not uploaded)"),
    ("sh", "L05", "black", "Original", "No", "Kept to Day 9 (Day 10 not uploaded)"),
    ("sh", "L06", "brown (muddy red)", "Replacement", "No", "Tagged Day 4"),
    ("sh", "L09", "blue", "Replacement", "Yes", "Tagged Day 5; damaged, replaced by aqua Day 9"),
    ("sh", "L10", "aqua", "Replacement", "No", "Tagged Day 9"),
]
ws = sheet("Leaves", [11, 7, 18, 14, 11, 9, 10, 9, 40])
r = heading(ws, 1, "Leaves tracked, and why leaves were replaced", TITLE)
ws.cell(row=2, column=1, value="mh = Low humidity (50% RH, Melbourne); sh = High humidity (80–85% RH, Singapore). "
        "Leaf numbers follow the tag colour, so L01 in mh and L01 in sh are different leaves.").font = NOTE
put(ws, 4, ["Condition", "Leaf", "Tag", "Type", "Replaced?", "Photos", "First day", "Last day", "Notes"], BOLD, HEAD_FILL)
for i, (c, l, t, typ, rep, note) in enumerate(leaves, 5):
    put(ws, i, [c, l, t, typ, rep,
                f"=COUNTIFS({S('B')},A{i},{S('C')},B{i})",
                f"=H{i}-F{i}+1",
                f"=SUMPRODUCT(MAX(({S('B')}=A{i})*({S('C')}=B{i})*{S('E')}))",
                note])
    for cc in range(1, 10):
        ws.cell(row=i, column=cc).border = THIN
LEAF_LAST = 4 + len(leaves)
ws.cell(row=LEAF_LAST + 2, column=1, value="Photos, first and last day are formulas over the Specimens sheet "
        "(first day = last day − photos + 1, because each leaf was photographed on consecutive days).").font = NOTE
ws.freeze_panes = "A5"
L = lambda c: f"Leaves!${c}$5:${c}${LEAF_LAST}"

# ---------------- Colour by leaf ----------------
ws = sheet("Colour by leaf", [11, 7, 16, 22])
heading(ws, 1, "Greenness per leaf, Days 2–10 (after treatment began)", TITLE)
put(ws, 3, ["Condition", "Leaf", "Photos Days 2–10", "Mean greenness Days 2–10"], BOLD, HEAD_FILL)
for i, (c, l, *_rest) in enumerate(leaves, 4):
    put(ws, i, [c, l, f"=COUNTIFS({C('B')},A{i},{C('C')},B{i},{C('D')},\">=2\")",
                f"=IFERROR(AVERAGEIFS({C('F')},{C('B')},A{i},{C('C')},B{i},{C('D')},\">=2\"),\"\")"])
    ws.cell(row=i, column=4).number_format = "0.000"
CBL_LAST = 3 + len(leaves)
CB = lambda c: f"'Colour by leaf'!${c}$4:${c}${CBL_LAST}"

# ---------------- Summary ----------------
ws = sheet("Summary", [46, 20, 20, 60])
wb.move_sheet("Summary", offset=-wb.index(wb["Summary"]))
r = heading(ws, 1, "Leaf Shape Study — Progress Report", TITLE)
ws.cell(row=2, column=1, value="As of 7 Oct 2026 · Prepared by Seara").font = NOTE
r = heading(ws, 4, "Summary")
for text in [
    "The leaf-shape (geometric morphometrics) part of the terrarium study has a full first dataset: 95 leaf photos "
    "from the Low-humidity (50% RH, \"mh\") and High-humidity (80–85% RH, \"sh\") terrariums, Days 1–10 "
    "(21–30 Sep 2026), each with 13 landmarks.",
    "Average leaf shape did not differ detectably between Low and High humidity (permutation test p = 0.76, 9 vs 8 leaves). "
    "Low humidity instead cost more leaves (4 of 5 originals replaced after shrivelling or damage, against 2 of 5), High-humidity "
    "leaves grew faster (+1.7 vs +0.1% per day, p = 0.082, not significant), and "
    "Low-humidity leaves were less green from Day 2 (p = 0.016). Mature leaves seem to respond to humidity through damage "
    "rather than by changing shape.",
    "Still to do: the measurement-error check for hub clicks, re-measuring 2 scales that failed the check, and the "
    "High-humidity Day 10 photos.",
]:
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    c = ws.cell(row=r, column=1, value=text)
    c.font, c.alignment = BODY, WRAP
    ws.row_dimensions[r].height = 42
    r += 1
r = heading(ws, r + 1, "Key numbers")
rows = [
    ("Leaves tracked", f"=COUNTIF({L('A')},\"mh\")", f"=COUNTIF({L('A')},\"sh\")", "Formula: Leaves sheet"),
    ("Photos digitised (13 landmarks each)", f"=COUNTIF({S('B')},\"mh\")", f"=COUNTIF({S('B')},\"sh\")", "Formula: Specimens sheet"),
    ("Original leaves replaced (of 5)", f"=COUNTIFS({L('A')},\"mh\",{L('D')},\"Original\",{L('E')},\"Yes\")",
     f"=COUNTIFS({L('A')},\"sh\",{L('D')},\"Original\",{L('E')},\"Yes\")", "Formula: Leaves sheet"),
    ("Mean growth, % per day", f"=AVERAGEIF({G('B')},\"mh\",{G('F')})", f"=AVERAGEIF({G('B')},\"sh\",{G('F')})",
     "Formula: Growth per leaf sheet. Difference not significant (permutation p = 0.082, Python)"),
    ("Leaves that shrank (growth < 0)", f"=COUNTIFS({G('B')},\"mh\",{G('F')},\"<0\")", f"=COUNTIFS({G('B')},\"sh\",{G('F')},\"<0\")",
     "Formula: Growth per leaf sheet"),
    ("Greenness on Day 1", f"=AVERAGEIFS({C('F')},{C('B')},\"mh\",{C('D')},1)", f"=AVERAGEIFS({C('F')},{C('B')},\"sh\",{C('D')},1)",
     "Formula: Colour per photo sheet"),
    ("Greenness Days 2–10 (mean of leaf averages)", f"=AVERAGEIF({CB('A')},\"mh\",{CB('D')})", f"=AVERAGEIF({CB('A')},\"sh\",{CB('D')})",
     "Formula: Colour by leaf sheet. Difference p = 0.016 (permutation test, Python)"),
]
r, first = table(ws, r, ["Measure", "Low humidity (mh)", "High humidity (sh)", "Source / note"], rows)
for rr in range(first + 3, first + 4):
    for cc in (2, 3):
        ws.cell(row=rr, column=cc).number_format = "+0.00;-0.00;0.00"
for rr in range(first + 5, first + 7):
    for cc in (2, 3):
        ws.cell(row=rr, column=cc).number_format = "0.000"
r = heading(ws, r + 1, "Typed-in results (not formulas)")
r, _ = table(ws, r, ["Measure", "Value", "", "Source"], [
    ("Procrustes distance between mh and sh mean shapes (leaf averages)", 0.01700781, "", "MorphoJ 1.08 discriminant function, averaged dataset"),
    ("Permutation p, Procrustes distance (1000 runs)", 0.755, "", "MorphoJ 1.08"),
    ("Leaves classified correctly under cross-validation", "9 of 17", "", "MorphoJ 1.08 (chance level)"),
    ("Typical shape distance between two leaves in the same tank", 0.063, "", "Python, median of leaf-mean distances"),
    ("Shape change explained by size within leaves", "1.4% (p = 0.31)", "", "Python, scripts\\growth_allometry.py"),
    ("Scale repeatability (same photo measured twice, 93 photos)", "1.8% typical (SD 2.8%)", "", "Old vs re-measured scales, 7 Oct 2026"),
    ("mh vs sh shape test with 4 alignment methods (centroid, hub, hub + direction, two fixed points)", "p = 0.67–0.74", "", "Python; same conclusion every time"),
])

# ---------------- Method ----------------
ws = sheet("Method", [6, 26, 90])
heading(ws, 1, "Method", TITLE)
table(ws, 3, ["Step", "What", "Details"], [
    (1, "Photos", "Phone photos (HEIC) converted to JPEG and renamed L##_D##_mh/sh.jpg. Most leaf-days have two shots; the "
        "first was used (Days 1–3 hand-picked). Photo logs record the original photo behind every image."),
    (2, "Hand step (tpsDig)", "Set the scale from the grid squares and click landmark 1, the vein hub where the stalk joins."),
    (3, "Automatic step (Python)", "scripts\\auto_landmarks.py finds the leaf edge by colour, draws a line from the leaf's "
        "centre through the hub (12 o'clock) and places landmarks 2–13 where clock lines every 30° meet the edge."),
    (4, "Checking", "Every photo is shown on a check sheet with its outline and points; the script flags hubs off the leaf, "
        "unusual sizes and deep notches. Four glare photos were traced by hand."),
    (5, "Analysis", "MorphoJ 1.08: Procrustes fit, PCA, discriminant function with permutation test on one averaged shape per "
        "leaf. Python: growth rates, shape vs size, leaf greenness."),
])

# ---------------- Results ----------------
ws = sheet("Results", [26, 16, 16, 60])
r = heading(ws, 1, "Results so far", TITLE)
r = heading(ws, 3, "Greenness by day (daily mean of all leaves photographed)")
put(ws, r, ["Day", "Low humidity (mh)", "High humidity (sh)", "Note"], BOLD, HEAD_FILL)
t0 = r + 1
for d in range(1, 11):
    rr = t0 + d - 1
    put(ws, rr, [d, f"=IFERROR(AVERAGEIFS({C('F')},{C('B')},\"mh\",{C('D')},A{rr}),NA())",
                 f"=IFERROR(AVERAGEIFS({C('F')},{C('B')},\"sh\",{C('D')},A{rr}),NA())",
                 {1: "Before the treatment had time to act", 5: "Glare on 4 Low-humidity photos",
                  10: "High-humidity Day 10 not uploaded yet (#N/A leaves a gap in the chart)"}.get(d, "")])
    for cc in (2, 3):
        ws.cell(row=rr, column=cc).number_format = "0.000"
chart = LineChart()
chart.title = "Greenness by day: Low vs High humidity"
chart.y_axis.title, chart.x_axis.title = "Greenness (GCC)", "Day"
chart.y_axis.scaling.min, chart.y_axis.scaling.max = 0.40, 0.60
chart.add_data(Reference(ws, min_col=2, max_col=3, min_row=t0 - 1, max_row=t0 + 9), titles_from_data=True)
chart.set_categories(Reference(ws, min_col=1, min_row=t0, max_row=t0 + 9))
chart.height, chart.width = 8, 16
ws.add_chart(chart, "F3")
r = t0 + 12
r = heading(ws, r, "Notes")
for text in [
    "Shape: no detectable difference in mean shape (Procrustes distance 0.017, permutation p = 0.755; see Summary). "
    "Individual leaves differ about four times more than the two groups.",
    "Growth: High-humidity leaves grew faster (+1.7 vs +0.1% per day, p = 0.082, not significant). Four leaves shrank (mh L03, L04, L05; sh L09), and all four were later replaced for damage.",
    "Greenness: Days 2–10 difference p = 0.016; holds without Day 5 (p = 0.023) and for Days 4–10 (p = 0.041). "
    "Gap largest on Days 3–6, closed on Days 7–9 when most Low-humidity leaves were replacements.",
    "Caveats: greenness varies about ±0.035 day to day within a leaf; one tank per condition; wetter leaves in the humid "
    "tank may look greener; greenness from photos is an index, not chlorophyll.",
]:
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    c = ws.cell(row=r, column=1, value=text)
    c.font, c.alignment = BODY, WRAP
    ws.row_dimensions[r].height = 30
    r += 1

# ---------------- Problems ----------------
ws = sheet("Problems & fixes", [42, 36, 50])
heading(ws, 1, "Problems found and fixed", TITLE)
table(ws, 3, ["Problem", "Effect", "Fix"], [
    ("tpsDig records clicks about 4.5× too small when the zoom shows 1.00 with the whole photo in view",
     "Scales about 5× wrong; hubs off the leaf", "Hover the hub to check coordinates before clicking; script flags sizes outside 35–75 mm"),
    ("Hand-placed outline points on each leaf's own corners (10–12 per leaf)", "Leaves could not be compared",
     "Hub + 12 clock-point scheme"),
    ("Glare on four Day 5 Low-humidity photos", "Part of the leaf edge looked like paper", "Outlines traced by hand in tpsDig"),
    ("Leaf in deep shadow, or a grey shadow cast by another leaf", "Outline cut into the leaf or swallowed the shadow",
     "Script rules for near-black leaf pixels and grey cast shadows"),
    ("Leaf cut off by the photo frame (mh L07 Day 8)", "Bottom edge missing", "Used the second photo of that pair"),
    ("Scale outlier rule", "—", "Re-measure only if leaf size is >10% from both neighbouring days; only mh L02 Day 4 broke it"),
    ("Scale re-measurement (7 Oct)", "2 of 95 new scales failed the check", "Kept the old scale for mh L02 Day 5 (tpsDig zoom fault) and mh L06 Day 10 (+17%); flagged for re-measuring"),
])

# ---------------- Changes from plan ----------------
ws = sheet("Changes from plan", [26, 90])
heading(ws, 1, "Changes from PlanV2 (state in the methods)", TITLE)
table(ws, 3, ["Area", "Change"], [
    ("Software", "MorphoJ 1.08 instead of the geomorph package in R"),
    ("Landmarks", "1 hand-placed hub + 12 automatic outline points at equal angles; like semilandmarks but not slid"),
    ("Photos", "Phone photos with grid paper as scale, not a fixed webcam with a calibration marker"),
    ("Leaves", "Dead or damaged leaves replaced with new tagged leaves; only 1 Low and 3 High original leaves span the experiment"),
    ("Not yet done", "Smoke conditions, logistic growth fit, fluctuating asymmetry, vein and areole density"),
])

# ---------------- Interpretation ----------------
ws = sheet("Interpretation", [24, 60, 50])
r = heading(ws, 1, "Interpretation", TITLE)
c = ws.cell(row=2, column=1, value="Reframed question: Is leaf form in nasturtium (Tropaeolum majus) plastic under Melbourne- versus "
            "Singapore-like air, and does the atmosphere act on shape while a leaf grows, or only on the health of leaves that are already mature?")
ws.merge_cells("A2:C2")
c.font, c.alignment = BODY, WRAP
ws.row_dimensions[2].height = 30
r, _ = table(ws, 4, ["Hypothesis", "Prediction", "Status"], [
    ("H1 Developing leaves", "Leaves that grow under low humidity are smaller, possibly differently shaped (Carins Murphy et al. 2014)",
     "Not tested: needs leaves that emerge during treatment"),
    ("H2 Mature leaves", "Outline shape stays the same, but leaves show stress under low humidity",
     "Fits current data: shape p = 0.76; 4 of 5 vs 2 of 5 leaves lost; Low leaves less green (p = 0.016)"),
    ("H3 Smoke", "Smoke affects leaf function more than shape; nasturtium's self-cleaning surface may limit particle build-up "
     "(Calder et al. 2010; Barthlott & Neinhuis 1997)", "Not tested yet"),
])
r = heading(ws, r + 1, "Why no shape difference showed")
table(ws, r, ["Possible explanation", "Evidence", "Check or fix"], [
    ("Leaves were already mature; size and shape are set while a leaf grows", "Tsukaya 2005; Carins Murphy et al. 2014",
     "Track leaves that emerge during treatment"),
    ("The response is in size, veins or function, not outline", "Calder et al. 2010; Carins Murphy et al. 2014",
     "Growth, colour and vein density analyses"),
    ("Too few leaves and too short (8–9 leaves, 10 days)", "Altman & Bland 1995", "State as a limitation; more leaves next run"),
    ("Survivor bias: the most damaged Low-humidity leaves were replaced", "Own data", "Report leaf loss per tank"),
    ("Measurement error lowers power", "Fruciano 2016", "Measurement-error check"),
    ("The tanks may have differed less than planned", "Humidity logs", "Compare logged humidity between tanks"),
])

# ---------------- Next steps ----------------
ws = sheet("Next steps", [70, 16, 16])
heading(ws, 1, "Next steps", TITLE)
ws.cell(row=2, column=1, value="Fill in Status (drop-down) and Owner as tasks progress.").font = NOTE
tasks = [
    "Re-measure the scale on all 95 photos (same number of grid squares, at least 5)",
    "Measurement-error check: 3 photos digitised 3 times each",
    "Re-run growth analysis with the new scales",
    "Add High-humidity Day 10 once the photos are uploaded",
    "Compare logged humidity and temperature of the two tanks with the targets",
    "Upload the High-humidity Day 10 photos (teammate)",
    "Count leaves that shrivelled or were replaced per tank, with dates",
    "Smoke run: count particles on nasturtium leaves with the Phase 1 ImageJ method",
]
done = {"Re-measure the scale on all 95 photos (same number of grid squares, at least 5)", "Re-run growth analysis with the new scales"}
tasks.insert(1, "Re-measure 2 scales that failed the check (mh L02 Day 5, mh L06 Day 10)")
r, first = table(ws, 4, ["Task", "Status", "Owner"], [(t, "Done" if t in done else "Not started", "") for t in tasks])
dv = DataValidation(type="list", formula1='"Not started,In progress,Done"', allow_blank=True)
ws.add_data_validation(dv)
dv.add(f"B{first}:B{r - 1}")

# ---------------- References ----------------
refs = [
    ("Altman & Bland 1995", "Absence of evidence is not evidence of absence", "BMJ 311: 485", "https://www.bmj.com/content/311/7003/485"),
    ("Barthlott & Neinhuis 1997", "Purity of the sacred lotus, or escape from contamination in biological surfaces", "Planta 202: 1–8",
     "https://agris.fao.org/search/ar/records/65df5a8790674e46e6538f59"),
    ("Calder et al. 2010", "Physiological effects of smoke exposure on deciduous and conifer tree species",
     "International Journal of Forestry Research 2010: 438930", "https://digitalcommons.usu.edu/aspen_bib/7404/"),
    ("Carins Murphy et al. 2014", "Acclimation to humidity modifies the link between leaf size and the density of veins and stomata",
     "Plant, Cell & Environment 37: 124–131", "https://eprints.utas.edu.au/23095/"),
    ("Chitwood & Sinha 2016", "Evolutionary and environmental forces sculpting leaf development", "Current Biology 26: R297–R306",
     "https://par.nsf.gov//servlets/purl/10357593"),
    ("Fruciano 2016", "Measurement error in geometric morphometrics", "Development Genes and Evolution 226: 139–158",
     "https://researchportal.port.ac.uk/en/publications/measurement-error-in-geometric-morphometrics/"),
    ("Klingenberg 2011", "MorphoJ: an integrated software package for geometric morphometrics", "Molecular Ecology Resources 11: 353–357",
     "https://research.manchester.ac.uk/en/publications/morphoj-an-integrated-software-package-for-geometric-morphometric/"),
    ("Klingenberg et al. 2002", "Shape analysis of symmetric structures: quantifying variation among individuals and asymmetry",
     "Evolution 56: 1909–1920", "https://kops.uni-konstanz.de/entities/publication/e86b1a1c-f255-4843-b227-bbfcdd3bb782"),
    ("Kozlov et al. 1996", "Fluctuating asymmetry of birch leaves increases under pollution impact", "Journal of Applied Ecology 33: 1489–1495",
     "https://acnpsearch.tweb-dev.unibo.it/singlejournalindex/3524435"),
    ("Lendzion & Leuschner 2008", "Growth of European beech saplings is limited by elevated atmospheric vapour pressure deficits",
     "Forest Ecology and Management, doi:10.1016/j.foreco.2008.05.008",
     "https://dspacecris7.sub.uni-goettingen.de/entities/publication/28071cb2-0a20-4fe2-9769-44c560d3f267"),
    ("Nicotra et al. 2011", "The evolution and functional significance of leaf shape in the angiosperms", "Functional Plant Biology 38: 535–552",
     "https://researchportalplus.anu.edu.au/en/publications/the-evolution-and-functional-significance-of-leaf-shape-in-the-an/"),
    ("Peppe et al. 2011", "Sensitivity of leaf size and shape to climate: global patterns and paleoclimatic applications",
     "New Phytologist, doi:10.1111/j.1469-8137.2010.03615.x", "https://pubs.usgs.gov/publication/70034957"),
    ("Tsukaya 2005", "Leaf shape: genetic controls and environmental factors", "International Journal of Developmental Biology 49: 547–555",
     "https://ijdb.ehu.eus/article/041921ht"),
    ("Viscosi & Cardini 2011", "Leaf morphology, taxonomy and geometric morphometrics: a simplified protocol for beginners",
     "PLoS ONE 6: e25630", "https://pmc.ncbi.nlm.nih.gov/articles/PMC3184990"),
    ("Wright et al. 2017", "Global climatic drivers of leaf size", "Science 357: 917–921",
     "https://spiral.imperial.ac.uk/entities/publication/eb9bfa77-c3c3-4628-bb4d-d93ad080b77d"),
    ("Zverev, Lama & Kozlov 2018", "Fluctuating asymmetry of birch leaves did not increase with pollution and drought stress in a controlled experiment",
     "Ecological Indicators 84: 283–289", "https://research.utu.fi/converis/portal/detail/Publication/27046984?lang=en_US"),
]
ws = sheet("References", [26, 60, 40, 14])
heading(ws, 1, "References", TITLE)
ws.cell(row=2, column=1, value="Details checked online; read each abstract before citing.").font = NOTE
r, first = table(ws, 4, ["Authors (year)", "Title", "Journal", "Link"], [(a, t, j, "Open") for a, t, j, u in refs])
for i, (_, _, _, url) in enumerate(refs):
    cell = ws.cell(row=first + i, column=4)
    cell.hyperlink, cell.font = url, LINK

wb._sheets = [wb["Summary"], wb["Method"], wb["Leaves"], wb["Results"], wb["Problems & fixes"], wb["Changes from plan"],
              wb["Interpretation"], wb["Next steps"], wb["References"], wb["Colour by leaf"], wb["Growth per leaf"],
              wb["Colour per photo"], wb["Specimens"]]
wb.calculation.fullCalcOnLoad = True
wb.save(sys.argv[1])
print("saved", sys.argv[1])

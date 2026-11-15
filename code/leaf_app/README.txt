LEAF LANDMARKS 2.0  (LeafLandmarks_v2.exe, Windows 10/11)

Measures nasturtium leaves in photos: finds the leaf outline, places 13 landmarks for geometric morphometrics
(tpsDig / MorphoJ format) and measures leaf size (centroid size), area, perimeter, roundness and greenness. It uses
the same method as our nasturtium humidity project and gives the same numbers (checked on 68 of the project's
photos, including 40 hand-traced ones).

PLEASE NOTE
- FOR NASTURTIUM LEAVES ONLY (for now). The method was made and tested on nasturtium: round leaves whose veins
  all spread from one hub inside the leaf. On other kinds of leaves the outline, landmarks and numbers can be
  wrong, even when they look plausible.
- YOU CLICK THE HUB YOURSELF. The app does not find the vein hub by itself: you click it once on every photo.
  After that click, the outline, the 13 landmarks, the scale and all the measurements are automatic. The hub is
  landmark 1 and decides where all the other landmarks go, so zoom in and click it carefully.

STARTING IT
Double-click LeafLandmarks_v2.exe. Nothing is installed. It takes a few seconds to open.
Windows may say "Windows protected your PC" because the app is not signed by a company: click "More info", then
"Run anyway".

TAKING THE PHOTOS
- One nasturtium leaf per photo, lying flat on grid paper, photographed from straight above.
- The whole leaf in the photo, with paper all around it. Light paper with thin dark grid lines works best.
- Even light: avoid glare and strong shadows. Green leaves work best; yellow or brown edges may need tracing by hand.
- JPEG, PNG, TIFF and iPhone HEIC photos all work.

USING IT
1. Add photos (or a whole folder).
2. Set the grid square size in mm (default 5 mm).
3. Click the vein hub yourself: the point where the veins meet (where the stalk joins). Zoom in with the mouse
   wheel for a precise click. The outline and the 13 points appear after a second or two.
4. Check the blue outline. If it is wrong, use "Trace outline by hand". Check that the dashed square in the
   top-left corner is one grid square. If it isn't, or no grid was found, use "Set scale with ruler" (click two
   points a known distance apart).
5. Right arrow = next photo. When done, "Save results".
The Help button in the app explains everything in more detail.

WHAT YOU GET (a new folder, leaf_results_<date>_<time>; earlier results are never overwritten)
- landmarks.tps: 13 landmarks per photo with its scale, for MorphoJ or tpsDig
- measurements.csv: one row per photo (README_results.txt in the folder explains every column)
- check_pictures: one picture per photo with the outline and the points. Look at them all.
- session.json: open it with "Open session" to carry on later

PRIVACY
Your photos are only read, never changed. Nothing is uploaded: everything stays on your computer.

LIMITS
- Greenness depends on the light and the camera, so only compare photos taken the same way.
- On our 5 mm grid photos, automatic scales differed from careful hand measurements by 1.35% (median; worst
  6.6%). On other paper, check the dashed square.
- The outline step uses some randomness (GrabCut), so measuring the same photo twice can differ very slightly
  (landmarks typically by less than 1% of the leaf radius).


FOR DEVELOPERS
Files in this folder:
  leaf_app.py        the window (tkinter). Run from source: python leaf_app.py
  leaf_core.py       the measuring, built on the project's scripts in ..\scripts (auto_landmarks.py,
                     auto_scale.py, leaf_area.py), which are imported unchanged; the colour step repeats
                     leaf_colour.py's calculation for one outline
  validate_core.py   re-measures project photos and compares with the project's results
                     (validation\core_vs_project_v2.csv and _log.txt: all 68 match)
  make_icon.py       draws leaf_icon.ico
  build_exe.ps1      builds dist\LeafLandmarks_v<N>.exe:  .\build_exe.ps1 2   (never overwrites an existing exe)
Needs Python 3 with numpy, opencv-python-headless, pillow, pillow-heif and pyinstaller.
leaf_app.py --selftest <spec.json> drives the window automatically (adds photos, clicks, saves, screenshot) for
testing a build.

"""Leaf Landmarks: a desktop app that measures leaves in photos the way the nasturtium project did.

For each photo the user clicks the leaf's vein hub; the app finds the outline, places 13 landmarks, reads the scale
from the grid paper and measures size, shape and greenness (leaf_core.py, which uses the project's scripts). A wrong
outline can be traced by hand, and a missing scale set from two clicked points a known distance apart. Results:
landmarks.tps (tpsDig/MorphoJ), measurements.csv, one check picture per photo and a session file to carry on later.
Photos are only read, never changed, and nothing leaves the computer.
Run: python leaf_app.py      Windows .exe: build_exe.ps1
"""
import csv
import datetime
import itertools
import json
import os
import queue
import sys
import threading
import traceback
from collections import OrderedDict

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

import leaf_core as C

APP, VERSION = "Leaf Landmarks", "2.0"
FOR_WHOM = ("For nasturtium leaves only (for now). You click the vein hub yourself on every photo: the app does not "
            "find it. Everything after that click is automatic.")
PHOTO_TYPES = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".heic", ".heif")
HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))     # bundled files inside the .exe
HELP = """WHAT IT DOES
Finds the outline of a leaf in a photo, places 13 landmarks for geometric morphometrics (tpsDig / MorphoJ format) and measures leaf size, area, perimeter, roundness and greenness.

FOR NASTURTIUM LEAVES ONLY (FOR NOW)
The method was made and tested on nasturtium leaves: round leaves whose veins all spread from one hub inside the leaf. On other kinds of leaves the outline, the 13 landmarks and the numbers can be wrong, even if they look plausible.

YOU CLICK THE HUB YOURSELF
The app does not find the vein hub by itself. On every photo you click the hub once. After that click, the outline, the 13 landmarks, the scale and all the measurements are automatic. The hub is landmark 1 and sets where every other landmark goes, so click it carefully (zoom in first).

TAKING THE PHOTOS
- One nasturtium leaf per photo, lying flat on grid paper, photographed from straight above.
- The whole leaf in the photo, with paper all around it. Light paper with thin dark grid lines works best.
- Even light: avoid glare and strong shadows. Green leaves work best; yellow or brown edges may need tracing by hand.

STEP BY STEP
1. Add photos (or a whole folder). The app starts looking for the grid in each photo.
2. Set the grid square size in mm in the toolbar (default 5 mm).
3. Click the vein hub yourself: the point where the veins meet (where the stalk joins). Zoom in with the mouse wheel first for a precise click. The outline (blue) and the 13 points appear after a second or two. Click again to move the hub.
4. Check the photo. Does the blue line follow the leaf edge? If not, use "Trace outline by hand". Is the dashed square in the top-left corner the size of one grid square? If not, or if no grid was found, use "Set scale with ruler".
5. Go to the next photo with the right arrow key (left arrow goes back).
6. Save results. To carry on later, use Open session and pick session.json in the results folder.

MOUSE AND KEYS
Mouse wheel = zoom. Right-drag or middle-drag = move around. F = fit the photo. Left / right arrows = previous / next photo. While tracing: Enter = finish, Backspace = undo the last part, Esc = cancel.

THE 13 LANDMARKS
1 = the hub. 2 = where the line from the leaf's centre through the hub meets the edge (12 o'clock). 3 to 13 = where lines from the hub every 30 degrees clockwise meet the edge.

WHAT YOU GET (a new folder, leaf_results_<date>_<time>)
- landmarks.tps: 13 landmarks per photo with its scale, for MorphoJ or tpsDig. To view it in tpsDig, put it in the same folder as the photos.
- measurements.csv: one row per photo. README_results.txt in the folder explains every column.
- check_pictures: one picture per photo with the outline and the points.
- session.json: your clicks, traces and scales, to reopen in this app.

GOOD TO KNOW
- Photos are shown the way tpsDig shows them (the phone's rotation flag is ignored), so some may look sideways. That does not change any result.
- Your photos are never changed, and nothing is uploaded: everything stays on this computer.
- Greenness depends on the light and the camera, so only compare photos taken the same way.
- Every number depends on the outline and the scale: look at every check picture before using the results.
"""


class Photo:
    """One photo and the user's input for it. Points are image pixels with y measured down."""

    def __init__(self, path, rid):
        self.path, self.rid = path, rid
        self.hub = None                 # (x, y)
        self.strokes = []               # finished hand trace
        self.ruler = None               # dict(p1, p2, mm)
        self.grid = None                # (square_px or None, info) once looked for
        self.result = self.error = self.pic = None
        self.token = 0                  # goes up whenever the input changes, so out-of-date results are dropped
        self.measuring = False

    @property
    def name(self):
        return os.path.basename(self.path)

    def scale(self, square_mm):
        """(mm per pixel, where it came from) or (None, why not)."""
        if self.ruler:
            return self.ruler["mm"] / float(np.hypot(*np.subtract(self.ruler["p2"], self.ruler["p1"]))), "ruler"
        if self.grid is None:
            return None, "looking for the grid..."
        if self.grid[0] is None:
            return None, "grid not found: " + self.grid[1].get("note", "")
        if not square_mm:
            return None, "grid square size is not a number"
        return square_mm / self.grid[0], "grid"

    def status(self):
        if self.measuring:
            return "measuring"
        if self.error:
            return "failed"
        if self.result:
            return "CHECK" if self.result["warnings"] else "ok"
        return "click hub" if self.hub is None else "waiting"


class Images:
    """Pixels of the last few photos opened, shared by the window and the worker thread."""

    def __init__(self, keep=4):
        self.keep, self.lock, self.d = keep, threading.Lock(), OrderedDict()

    def get(self, path):
        with self.lock:
            if path in self.d:
                self.d.move_to_end(path)
                return self.d[path]
        img = C.load_photo(path)
        with self.lock:
            self.d[path] = img
            while len(self.d) > self.keep:
                self.d.popitem(last=False)
        return img


class Worker(threading.Thread):
    """Runs the slow steps (grid scale; outline, landmarks and measurements) one at a time, off the window's thread."""

    def __init__(self, images):
        super().__init__(daemon=True)
        self.images, self.jobs, self.done, self.order = images, queue.PriorityQueue(), queue.Queue(), itertools.count()

    def submit(self, prio, kind, photo, args=()):
        self.jobs.put((prio, next(self.order), kind, photo, args))

    def run(self):
        while True:
            _, _, kind, photo, args = self.jobs.get()
            try:
                if kind == "grid":
                    out = photo.grid or C.grid_square_px(self.images.get(photo.path))  # skip if done already
                else:
                    img = self.images.get(photo.path)
                    token, hub, strokes = args
                    res, err = C.measure(img, hub, strokes)
                    pic = res and cv2.imencode(".jpg", C.check_picture(img, res, photo.rid),
                                               [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tobytes()
                    out = (res, err, pic)
                self.done.put((kind, photo, args, True, out))
            except Exception as e:                                       # keep going; tell the user
                traceback.print_exc()
                self.done.put((kind, photo, args, False, f"{type(e).__name__}: {e}"))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.f = self.winfo_fpixels("1i") / 96.0              # screen scaling: widths below are for a 100% screen
        self.title(f"{APP} {VERSION}  -  for nasturtium leaves; you click the vein hub on each photo")
        self.geometry(f"{self.px(1360)}x{self.px(840)}")
        self.minsize(self.px(900), self.px(560))
        try:
            self.iconbitmap(os.path.join(HERE, "leaf_icon.ico"))
        except tk.TclError:
            pass
        self.photos, self.cur, self.mode = [], None, "hub"
        self.draft, self.chunks, self.ruler_pts = [], [], []    # trace in progress (points, sizes of each part); ruler
        self.pending, self.dirty = 0, False
        self.images = Images()
        self.worker = Worker(self.images)
        self.worker.start()
        self.square_mm = tk.StringVar(value="5")
        self.square_mm.trace_add("write", lambda *_: self.refresh())
        self.pil = self.tkimg = None
        self.z, self.ox, self.oy, self.fitted = 1.0, 0.0, 0.0, True
        self._render_job, self._pan, self._last = None, None, None
        self.build()
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.after(100, self.poll)

    # ---------- layout ----------
    def px(self, v):
        return int(round(v * self.f))

    def build(self):
        bar = ttk.Frame(self, padding=(6, 4))
        bar.pack(side="top", fill="x")
        for text, cmd in (("Add photos...", self.add_photos), ("Add folder...", self.add_folder),
                          ("Remove photo", self.remove_photo)):
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=2)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Label(bar, text="Grid square size (mm):").pack(side="left")
        ttk.Spinbox(bar, from_=0.5, to=100, increment=0.5, width=6, textvariable=self.square_mm).pack(side="left", padx=4)
        for text, cmd in (("Help", self.show_help), ("Save results...", self.save_results),
                          ("Open session...", self.open_session)):
            ttk.Button(bar, text=text, command=cmd).pack(side="right", padx=2)

        self.status = ttk.Label(self, anchor="w", padding=(8, 2), relief="sunken")
        self.status.pack(side="bottom", fill="x")

        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        self.tree = ttk.Treeview(left, columns=("scale", "result"), selectmode="browse")
        self.tree.heading("#0", text="Photo")
        self.tree.heading("scale", text="Scale")
        self.tree.heading("result", text="Result")
        self.tree.column("#0", width=self.px(190))
        self.tree.column("scale", width=self.px(58), anchor="center")
        self.tree.column("result", width=self.px(78), anchor="center")
        for tag, colour in (("ok", "#1d7a1d"), ("CHECK", "#b35c00"), ("failed", "#c00000")):
            self.tree.tag_configure(tag, foreground=colour)
        sb = ttk.Scrollbar(left, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        body.add(left, weight=0)

        self.canvas = tk.Canvas(body, background="#3a3a3a", highlightthickness=0, cursor="crosshair")
        body.add(self.canvas, weight=1)
        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_drag)
        c.bind("<ButtonRelease-1>", self.on_release)
        for b in ("2", "3"):
            c.bind(f"<ButtonPress-{b}>", lambda e: setattr(self, "_pan", (e.x, e.y)))
            c.bind(f"<B{b}-Motion>", self.on_pan)
        c.bind("<MouseWheel>", self.on_wheel)
        c.bind("<Configure>", lambda e: self.fit() if self.fitted else self.request_render())
        for key, fn in (("<Right>", lambda: self.step(1)), ("<Next>", lambda: self.step(1)),
                        ("<Left>", lambda: self.step(-1)), ("<Prior>", lambda: self.step(-1)),
                        ("<Return>", self.finish_trace), ("<Escape>", self.cancel_mode),
                        ("<BackSpace>", self.undo_trace), ("f", self.fit), ("F", self.fit)):
            self.bind_all(key, lambda e, fn=fn: None if e.widget.winfo_class() in ("TSpinbox", "Entry") else fn())

        right = ttk.Frame(body, padding=8, width=self.px(340))
        right.pack_propagate(False)
        body.add(right, weight=0)
        self.title_lbl = ttk.Label(right, font=("Segoe UI", 11, "bold"), wraplength=self.px(320))
        self.title_lbl.pack(anchor="w")
        self.howto = ttk.Label(right, wraplength=self.px(320), foreground="#1f4e8c")
        self.howto.pack(anchor="w", pady=(6, 8))
        self.btn_box = ttk.Frame(right)                             # only the buttons that apply right now
        self.btn_box.pack(fill="x")
        self.btn = {key: ttk.Button(self.btn_box, text=text, command=cmd) for key, text, cmd in (
            ("trace", "Trace outline by hand", self.start_trace), ("auto", "Use automatic outline", self.clear_trace),
            ("finish", "Finish trace (Enter)", self.finish_trace), ("undo", "Undo last part (Backspace)", self.undo_trace),
            ("ruler", "Set scale with ruler", self.start_ruler), ("grid", "Use grid scale instead", self.clear_ruler),
            ("cancel", "Cancel (Esc)", self.cancel_mode))}
        self.info = tk.Text(right, wrap="word", height=20, relief="flat", background=self.cget("background"),
                            font=("Segoe UI", 10))
        self.info.tag_configure("warn", foreground="#b35c00")
        self.info.tag_configure("err", foreground="#c00000")
        self.info.tag_configure("bold", font=("Segoe UI", 10, "bold"))
        self.info.pack(fill="both", expand=True, pady=(8, 4))
        nav = ttk.Frame(right)
        nav.pack(fill="x")
        ttk.Button(nav, text="< Previous", command=lambda: self.step(-1)).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(nav, text="Next >", command=lambda: self.step(1)).pack(side="left", expand=True, fill="x", padx=2)
        self.refresh()

    # ---------- photos ----------
    def add_photos(self):
        paths = filedialog.askopenfilenames(title="Add leaf photos", filetypes=[
            ("Photos", " ".join("*" + e for e in PHOTO_TYPES)), ("All files", "*.*")])
        self.add_paths(paths)

    def add_folder(self):
        d = filedialog.askdirectory(title="Add every photo in a folder")
        if d:
            self.add_paths([os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith(PHOTO_TYPES)])

    def add_paths(self, paths, rids=None):
        have = {os.path.normcase(os.path.abspath(p.path)) for p in self.photos}
        used = {p.rid for p in self.photos}
        added = []
        for i, path in enumerate(paths):
            if os.path.normcase(os.path.abspath(path)) in have:
                continue
            rid = (rids[i] if rids else None) or os.path.splitext(os.path.basename(path))[0].replace(" ", "_")
            base, k = rid, 2
            while rid in used:                                     # same file name in two folders
                rid, k = f"{base}_{k}", k + 1
            used.add(rid)
            p = Photo(os.path.abspath(path), rid)
            self.photos.append(p)
            self.tree.insert("", "end", iid=rid, text=p.name)
            self.submit(3, "grid", p)                               # look for the grid in the background
            added.append(p)
        if added and self.cur is None:
            self.show(added[0])
        self.refresh()
        return added

    def remove_photo(self):
        p = self.cur
        if p is None:
            return
        if (p.hub or p.ruler) and not messagebox.askyesno(APP, f"Remove {p.name} and its hub, trace and scale from the "
                                                               "list? (The photo file itself is not touched.)"):
            return
        i = self.photos.index(p)
        self.photos.remove(p)
        p.token += 1                                               # drop any result still on its way
        self.tree.delete(p.rid)
        self.cur, self.pil = None, None
        if self.photos:
            self.show(self.photos[min(i, len(self.photos) - 1)])
        self.refresh()
        self.request_render()

    def on_select(self, _):
        sel = self.tree.selection()
        p = next((p for p in self.photos if sel and p.rid == sel[0]), None)
        if p is not None and p is not self.cur:
            self.show(p)

    def step(self, d):
        if self.photos and self.cur is not None and self.mode == "hub":
            i = (self.photos.index(self.cur) + d) % len(self.photos)
            self.show(self.photos[i])

    def show(self, p):
        self.cur, self.mode = p, "hub"
        self.draft, self.chunks, self.ruler_pts = [], [], []
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            self.pil = Image.fromarray(cv2.cvtColor(self.images.get(p.path), cv2.COLOR_BGR2RGB))
        except Exception as e:
            self.pil, p.error = None, f"Can't open this photo ({e})."
        self.config(cursor="")
        if self.tree.selection() != (p.rid,):
            self.tree.selection_set(p.rid)
            self.tree.see(p.rid)
        if p.grid is None:
            self.submit(1, "grid", p)                               # this photo's grid before the others
        if p.hub is not None and p.result is None and p.error is None and not p.measuring:
            self.remeasure(p, 1)
        self.fit()
        self.refresh()

    # ---------- background work ----------
    def submit(self, prio, kind, photo, args=()):
        self.pending += 1
        self.worker.submit(prio, kind, photo, args)

    def remeasure(self, p, prio=0):
        p.token += 1
        p.result = p.error = p.pic = None
        p.measuring = p.hub is not None
        self.dirty = True
        if p.measuring:
            self.submit(prio, "measure", p, (p.token, p.hub, [list(s) for s in p.strokes]))

    def poll(self):
        changed = False
        while True:
            try:
                kind, p, args, ok, out = self.worker.done.get_nowait()
            except queue.Empty:
                break
            self.pending -= 1
            changed = True
            if kind == "grid":
                if p.grid is None:
                    p.grid = out if ok else (None, {"note": out})
            elif args[0] == p.token:                               # still the latest hub/trace
                p.measuring = False
                if ok:
                    p.result, p.error, p.pic = out
                else:
                    p.error = "Something went wrong while measuring: " + out
        if changed:
            self.refresh()
            self.request_render()
        self.after(100, self.poll)

    # ---------- view ----------
    def fit(self):
        self.fitted = True
        if self.pil is None:
            self.request_render()
            return
        cw, ch = max(self.canvas.winfo_width(), 50), max(self.canvas.winfo_height(), 50)
        W, H = self.pil.size
        self.z = 0.97 * min(cw / W, ch / H)
        self.ox, self.oy = (cw - W * self.z) / 2, (ch - H * self.z) / 2
        self.request_render()

    def to_canvas(self, p):
        return self.ox + p[0] * self.z, self.oy + p[1] * self.z

    def to_image(self, x, y):
        return (x - self.ox) / self.z, (y - self.oy) / self.z

    def on_wheel(self, e):
        if self.pil is None:
            return
        fit_z = min(self.canvas.winfo_width() / self.pil.size[0], self.canvas.winfo_height() / self.pil.size[1])
        z = min(max(self.z * (1.25 if e.delta > 0 else 0.8), 0.5 * fit_z), 8.0)
        ix, iy = self.to_image(e.x, e.y)
        self.z, self.ox, self.oy, self.fitted = z, e.x - ix * z, e.y - iy * z, False
        self.request_render()

    def on_pan(self, e):
        if self._pan:
            self.ox += e.x - self._pan[0]
            self.oy += e.y - self._pan[1]
            self._pan, self.fitted = (e.x, e.y), False
            self.request_render()

    def request_render(self):
        if self._render_job is None:
            self._render_job = self.after(15, self.render)

    def render(self):
        self._render_job = None
        c = self.canvas
        c.delete("all")
        if self.pil is None:
            msg = ("Add nasturtium leaf photos to start:\nAdd photos... or Add folder... at the top left.\n\n"
                   "This app is for nasturtium leaves only (for now).\n"
                   "You click the vein hub yourself on every photo: the app does not find it.\n"
                   "Everything after that click is automatic." if not self.photos else "This photo can't be opened.")
            c.create_text(c.winfo_width() / 2, c.winfo_height() / 2, text=msg, fill="white", font=("Segoe UI", 13),
                          justify="center")
            return
        cw, ch = c.winfo_width(), c.winfo_height()
        W, H = self.pil.size
        x0, y0 = max(0.0, -self.ox / self.z), max(0.0, -self.oy / self.z)
        x1, y1 = min(W, (cw - self.ox) / self.z), min(H, (ch - self.oy) / self.z)
        if x1 > x0 and y1 > y0:
            size = (max(1, round((x1 - x0) * self.z)), max(1, round((y1 - y0) * self.z)))
            im = self.pil.resize(size, Image.NEAREST if self.z >= 2 else Image.BILINEAR, box=(x0, y0, x1, y1),
                                 reducing_gap=None if self.z >= 1 else 2.0)
            self.tkimg = ImageTk.PhotoImage(im)
            c.create_image(self.ox + x0 * self.z, self.oy + y0 * self.z, image=self.tkimg, anchor="nw")
        self.overlay()

    def label(self, x, y, text, colour="white", size=10, anchor="center"):
        """Text with a dark edge, readable on any photo."""
        for dx, dy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
            self.canvas.create_text(x + dx, y + dy, text=text, fill="black", font=("Segoe UI", size, "bold"), anchor=anchor)
        self.canvas.create_text(x, y, text=text, fill=colour, font=("Segoe UI", size, "bold"), anchor=anchor)

    def overlay(self):
        p, c = self.cur, self.canvas
        r = p.result
        if r and self.mode != "trace":
            cnt = r["contour"][::max(1, len(r["contour"]) // 1500)]
            pts = [v for q in cnt for v in self.to_canvas(q)]
            c.create_line(*pts, *pts[:2], fill="#00c8ff", width=2)
            cx, cy = self.to_canvas(r["centre"])
            c.create_line(cx, cy, *self.to_canvas(r["landmarks"][1]), fill="#ffff00", dash=(4, 3))
            c.create_line(cx - 7, cy, cx + 7, cy, fill="#ffff00", width=2)
            c.create_line(cx, cy - 7, cx, cy + 7, fill="#ffff00", width=2)
            hx, hy = self.to_canvas(r["landmarks"][0])
            for k, q in enumerate(r["landmarks"]):
                x, y = self.to_canvas(q)
                c.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#ff8c00" if k == 1 else "#ff2020", outline="white")
                d = max(np.hypot(x - hx, y - hy), 1)
                lx, ly = (x + 6, y - 12) if k == 0 else (x + 17 * (x - hx) / d, y + 17 * (y - hy) / d)
                self.label(lx, ly, str(k + 1))
        else:
            if p.strokes and self.mode != "trace":                 # finished trace waiting for a hub
                pts = [v for q in p.strokes[0] for v in self.to_canvas(q)]
                c.create_line(*pts, *pts[:2], fill="#ff40ff", width=2)
            if p.hub is not None:
                x, y = self.to_canvas(p.hub)
                c.create_oval(x - 6, y - 6, x + 6, y + 6, fill="#ff2020", outline="white", width=2)
                if p.measuring:
                    self.label(x, y - 20, "measuring...", "#ffff80", 11)
        if self.mode == "trace" and self.draft:
            pts = [v for q in self.draft for v in self.to_canvas(q)]
            if len(pts) >= 4:
                c.create_line(*pts, fill="#ff40ff", width=2)
                c.create_line(*pts[-2:], *pts[:2], fill="#ff40ff", dash=(3, 3))
            c.create_oval(pts[0] - 4, pts[1] - 4, pts[0] + 4, pts[1] + 4, fill="#ff40ff", outline="white")
        if p.ruler:
            (x1, y1), (x2, y2) = self.to_canvas(p.ruler["p1"]), self.to_canvas(p.ruler["p2"])
            c.create_line(x1, y1, x2, y2, fill="#ffa000", width=3)
            self.label((x1 + x2) / 2, (y1 + y2) / 2 - 14, f"{p.ruler['mm']:g} mm", "#ffd080")
        for q in self.ruler_pts:
            x, y = self.to_canvas(q)
            c.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#ffa000", outline="white", width=2)
        if not p.ruler and p.grid and p.grid[0]:                   # one detected grid square, to compare by eye
            s, a = p.grid[0] * self.z, np.radians(p.grid[1].get("grid_angle_deg", 0))
            self.label(self.px(12), self.px(14), f"found: 1 grid square = {p.grid[0]:.0f} px", "#ffff80", 9, "w")
            if s < 0.4 * min(c.winfo_width(), c.winfo_height()):
                u, v = np.array([np.cos(a), np.sin(a)]) * s, np.array([-np.sin(a), np.cos(a)]) * s
                o = np.array([self.px(14) + max(0, -v[0]), self.px(34) + max(0, -u[1])])
                corners = [o, o + u, o + u + v, o + v]
                c.create_polygon(*[t for q in corners for t in q], outline="#ffff00", fill="", width=2, dash=(5, 3))

    # ---------- mouse ----------
    def inside(self, pt):
        return self.pil is not None and 0 <= pt[0] < self.pil.size[0] and 0 <= pt[1] < self.pil.size[1]

    def on_press(self, e):
        p = self.cur
        pt = self.to_image(e.x, e.y)
        if p is None or not self.inside(pt):
            return
        if self.mode == "hub":
            p.hub = (round(pt[0], 1), round(pt[1], 1))
            self.remeasure(p)
        elif self.mode == "trace":
            self.draft.append(pt)
            self.chunks.append(1)
            self._last = (e.x, e.y)
        elif self.mode == "ruler":
            self.ruler_pts.append(pt)
            if len(self.ruler_pts) == 2:
                self.after(10, self.ask_ruler)
        self.refresh()
        self.request_render()

    def on_drag(self, e):
        if self.mode != "trace" or not self.chunks or self._last is None:
            return
        if np.hypot(e.x - self._last[0], e.y - self._last[1]) >= 3:     # a point every 3 screen pixels
            pt = self.to_image(e.x, e.y)
            if self.inside(pt):
                self.draft.append(pt)
                self.chunks[-1] += 1
                self._last = (e.x, e.y)
                self.request_render()

    def on_release(self, _):
        self._last = None
        if self.mode == "trace":
            self.refresh()

    # ---------- trace and ruler ----------
    def start_trace(self):
        if self.cur is not None and self.pil is not None:
            self.mode, self.draft, self.chunks = "trace", [], []
            self.refresh()
            self.request_render()

    def finish_trace(self):
        if self.mode != "trace":
            return
        if len(self.draft) < 10:
            messagebox.showinfo(APP, "Trace all the way round the leaf first (at least 10 points).")
            return
        p = self.cur
        p.strokes = [[(round(x, 1), round(y, 1)) for x, y in self.draft]]
        self.mode, self.draft, self.chunks = "hub", [], []
        self.remeasure(p)
        self.refresh()
        self.request_render()

    def undo_trace(self):
        if self.mode == "trace" and self.chunks:
            n = self.chunks.pop()
            del self.draft[-n:]
            self.refresh()
            self.request_render()

    def clear_trace(self):
        if self.cur is not None and self.cur.strokes:
            self.cur.strokes = []
            self.remeasure(self.cur)
            self.refresh()
            self.request_render()

    def start_ruler(self):
        if self.cur is not None and self.pil is not None:
            self.mode, self.ruler_pts = "ruler", []
            self.refresh()
            self.request_render()

    def ask_ruler(self):
        mm = simpledialog.askfloat(APP, "Distance between the two points, in mm:", parent=self, minvalue=0.01)
        a, b = self.ruler_pts
        if mm and np.hypot(a[0] - b[0], a[1] - b[1]) > 5:
            self.cur.ruler = dict(p1=(round(a[0], 1), round(a[1], 1)), p2=(round(b[0], 1), round(b[1], 1)), mm=mm)
            self.dirty = True
        self.mode, self.ruler_pts = "hub", []
        self.refresh()
        self.request_render()

    def clear_ruler(self):
        if self.cur is not None and self.cur.ruler:
            self.cur.ruler, self.dirty = None, True
            self.refresh()
            self.request_render()

    def cancel_mode(self):
        self.mode, self.draft, self.chunks, self.ruler_pts = "hub", [], [], []
        self.refresh()
        self.request_render()

    # ---------- side panel, list and status ----------
    def square(self):
        try:
            v = float(self.square_mm.get().replace(",", "."))
            return v if v > 0 else None
        except ValueError:
            return None

    def refresh(self):
        sq = self.square()
        for p in self.photos:
            sc, src = p.scale(sq)
            st = p.status()
            self.tree.item(p.rid, values=(src if sc else ("..." if p.grid is None else "none"), st),
                           tags=(st,) if st in ("ok", "CHECK", "failed") else ())
        n_done = sum(p.result is not None for p in self.photos)
        self.status.config(text=f"{len(self.photos)} photos, {n_done} measured" +
                           (f"   |   working ({self.pending} step{'s' * (self.pending != 1)} left)..." if self.pending else "") +
                           "   |   mouse wheel = zoom, right-drag = move, arrows = previous/next photo")
        p = self.cur
        hub_mode = p is not None and self.pil is not None and self.mode == "hub"
        show = dict(trace=hub_mode, auto=hub_mode and bool(p.strokes), finish=self.mode == "trace",
                    undo=self.mode == "trace", ruler=hub_mode, grid=hub_mode and bool(p.ruler), cancel=self.mode != "hub")
        for k, b in self.btn.items():
            b.pack_forget()
            if show[k]:
                b.pack(fill="x", pady=2)
        self.btn["undo"].state(["!disabled"] if self.chunks else ["disabled"])
        info = self.info
        info.configure(state="normal")
        info.delete("1.0", "end")
        if p is None:
            self.title_lbl.config(text="No photo yet")
            self.howto.config(text="Add leaf photos with the buttons at the top left. Help explains how to take them.\n\n"
                                   + FOR_WHOM)
            info.configure(state="disabled")
            return
        self.title_lbl.config(text=f"{p.name}   ({self.photos.index(p) + 1} of {len(self.photos)})")
        self.howto.config(text={
            "trace": "Trace the leaf edge: hold the left mouse button and draw round the leaf, or click point by point. "
                     "Lifting the button is fine; the line carries on from the last point. Enter = finish, "
                     "Backspace = undo the last part, Esc = cancel. Zoom and move as usual.",
            "ruler": "Click two points a known distance apart: two marks on a ruler, or grid lines several squares "
                     "apart. Then type the distance in mm."}.get(self.mode) or (
            "Click the vein hub: the point where the veins meet, where the stalk joins. The app can't find it by "
            "itself, so click it on every photo. Zoom in with the mouse wheel for a precise click." if p.hub is None else
            "Click the hub again (on the leaf), or trace the outline by hand." if p.error else
            "Check that the blue line follows the leaf edge and that the points look right. Click again to move "
            "the hub. Wrong outline? Trace outline by hand. Next photo: right arrow."))
        sc, src = p.scale(sq)
        info.insert("end", f"ID in results: {p.rid}\n")
        if sc:
            how = f"grid, 1 square = {p.grid[0]:.1f} px" if src == "grid" else f"ruler, {p.ruler['mm']:g} mm"
            info.insert("end", f"Scale: {sc:.6f} mm per pixel ({how})\n")
        else:
            info.insert("end", f"Scale: none ({src}). Use 'Set scale with ruler' to measure in mm.\n", "warn")
        r = p.result
        if p.error:
            info.insert("end", "\n" + p.error + "\n", "err")
        elif p.measuring:
            info.insert("end", "\nMeasuring...\n")
        elif r:
            mm = (lambda v, k=1: f"{v * sc ** k:.{2 if k == 1 else 1}f} mm{'²' if k == 2 else ''}") if sc else \
                (lambda v, k=1: f"{v:.0f} px{'²' if k == 2 else ''}")
            info.insert("end", f"Outline: {r['outline']}\n\n")
            info.insert("end", "Leaf size (centroid size): ", "bold")
            info.insert("end", f"{mm(r['centroid_size_px'])}\n")
            info.insert("end", f"Area: {mm(r['area_px'], 2)}\nPerimeter: {mm(r['perimeter_px'])}\n"
                               f"Roundness: {r['roundness']:.3f}  (1 = a perfect circle)\n")
            if r["colour"]:
                col = r["colour"]
                info.insert("end", "Greenness (GCC): ", "bold")
                info.insert("end", f"{col['gcc']:.4f}\nYellow-brown: {col['yellow_pct']:.1f}% of the leaf\n"
                                   f"Glare: {col['glare_pct']:.1f}% of the leaf\n")
            for w in r["warnings"]:
                info.insert("end", "\nCheck: " + w + "\n", "warn")
            for n in r["notes"]:
                info.insert("end", "\nNote: " + n + "\n")
        info.configure(state="disabled")

    # ---------- saving and reopening ----------
    def save_results(self, parent=None, quiet=False):
        busy = [p for p in self.photos if p.measuring or (p.result and p.grid is None and not p.ruler)]
        if busy:
            for p in busy:
                if p.grid is None:
                    self.submit(0, "grid", p)                       # their grid before any others
            messagebox.showinfo(APP, f"Still measuring or finding the grid on {len(busy)} photo"
                                     f"{'s' * (len(busy) != 1)}. Try again in a moment.")
            return None
        if not any(p.result for p in self.photos):
            messagebox.showinfo(APP, "Nothing measured yet: click the vein hub on at least one photo.")
            return None
        parent = parent or filedialog.askdirectory(title="Where should the results folder go?")
        if not parent:
            return None
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        out, k = os.path.join(parent, f"leaf_results_{stamp}"), 2
        while os.path.exists(out):                                 # never overwrite earlier results
            out, k = os.path.join(parent, f"leaf_results_{stamp}_{k}"), k + 1
        os.makedirs(os.path.join(out, "check_pictures"))
        sq = self.square()
        tps, rows = [], []
        for p in self.photos:
            sc, src = p.scale(sq)
            r, image = p.result, p.name
            if r:
                if p.path.lower().endswith(C.HEIC):                 # tpsDig can't open HEIC: JPEG copy next to the tps
                    image = p.rid + ".jpg"
                    cv2.imencode(".jpg", self.images.get(p.path), [cv2.IMWRITE_JPEG_QUALITY, 95])[1].tofile(
                        os.path.join(out, image))
                tps += C.tps_record(r, image, p.rid, sc)
                with open(os.path.join(out, "check_pictures", f"{p.rid}_check.jpg"), "wb") as fh:
                    fh.write(p.pic)
            rows.append(self.csv_row(p, image, sc, src, sq))
        with open(os.path.join(out, "landmarks.tps"), "w", newline="") as fh:
            fh.write("\r\n".join(tps) + "\r\n")
        with open(os.path.join(out, "measurements.csv"), "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        with open(os.path.join(out, "session.json"), "w", encoding="utf-8") as fh:
            json.dump(self.session(), fh, indent=1)
        with open(os.path.join(out, "README_results.txt"), "w", encoding="utf-8") as fh:
            fh.write(results_readme(sq, stamp))
        self.dirty = False
        n = sum(p.result is not None for p in self.photos)
        if not quiet and messagebox.askyesno(APP, f"Saved {n} measured photo{'s' * (n != 1)} to\n{out}\n\nOpen the folder?"):
            os.startfile(out)
        return out

    @staticmethod
    def csv_row(p, image, sc, src, sq):
        r = p.result
        f = lambda v, d: "" if v is None else round(v, d)
        row = dict(ID=p.rid, photo=p.name, image_in_tps=image if r else "",
                   status="measured" if r else (p.error or "not measured: hub not clicked"),
                   outline=r["outline"] if r else "", scale_mm_per_px=f(sc, 8), scale_from=src if sc else "none",
                   grid_square_mm=sq if sc and src == "grid" else "",
                   ruler_mm=p.ruler["mm"] if sc and src == "ruler" else "")
        cs, area, per = (r["centroid_size_px"], r["area_px"], r["perimeter_px"]) if r else (None, None, None)
        col = (r or {}).get("colour") or {}
        row.update(centroid_size_mm=f(cs and sc and cs * sc, 2), area_mm2=f(area and sc and area * sc ** 2, 1),
                   perimeter_mm=f(per and sc and per * sc, 2), roundness=f(r and r["roundness"], 4),
                   gcc=f(col.get("gcc"), 4), yellow_pct=f(col.get("yellow_pct"), 2), glare_pct=f(col.get("glare_pct"), 2),
                   centroid_size_px=f(cs, 1), area_px=f(area, 0), perimeter_px=f(per, 1),
                   hub_offset_pct=f(r and 100 * r["hub_offset"], 1), warnings="; ".join(r["warnings"]) if r else "")
        return row

    def session(self):
        return dict(app=APP, version=VERSION, grid_square_mm=self.square_mm.get(), photos=[
            dict(path=p.path, id=p.rid, hub=p.hub, trace=p.strokes, ruler=p.ruler) for p in self.photos])

    def open_session(self):
        path = filedialog.askopenfilename(title="Open a saved session", filetypes=[("Session", "session.json"),
                                                                                    ("JSON", "*.json")])
        if not path:
            return
        try:
            data = json.load(open(path, encoding="utf-8"))
            entries = data["photos"]
        except Exception as e:
            messagebox.showerror(APP, f"That file isn't a saved session ({e}).")
            return
        if self.photos and not messagebox.askyesno(APP, "Replace the photos in the list with the saved session?"):
            return
        for p in self.photos:
            p.token += 1
        self.photos, self.cur, self.pil = [], None, None
        self.tree.delete(*self.tree.get_children())
        self.square_mm.set(data.get("grid_square_mm", "5"))
        found = [e for e in entries if os.path.exists(e["path"])]
        for p, e in zip(self.add_paths([e["path"] for e in found], [e["id"] for e in found]), found):
            p.hub = tuple(e["hub"]) if e.get("hub") else None
            p.strokes = [[tuple(q) for q in s] for s in e.get("trace") or []]
            p.ruler = e.get("ruler")
            if p.hub:
                self.remeasure(p, 2)
        self.dirty = False
        missing = [e["path"] for e in entries if e not in found]
        if missing:
            messagebox.showwarning(APP, "These photos were not found (moved or renamed?) and were left out:\n\n" +
                                   "\n".join(missing[:15]) + ("\n..." if len(missing) > 15 else ""))
        if self.photos:
            self.show(self.photos[0])

    def show_help(self):
        w = tk.Toplevel(self)
        w.title(f"{APP} - help")
        w.geometry("720x640")
        t = tk.Text(w, wrap="word", padx=12, pady=10, font=("Segoe UI", 10))
        sb = ttk.Scrollbar(w, command=t.yview)
        t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        t.pack(fill="both", expand=True)
        t.insert("end", HELP)
        t.configure(state="disabled")

    def quit_app(self):
        if self.dirty and any(p.result for p in self.photos) and not messagebox.askyesno(
                APP, "You have results that are not saved. Quit anyway?"):
            return
        self.destroy()


def results_readme(sq, stamp):
    return f"""Results from {APP} {VERSION}, saved {stamp.replace('_', ' ')}. Grid square size used: {sq} mm.

landmarks.tps       13 landmarks per measured photo (tpsDig format: y measured up from the bottom of the photo),
                    with IMAGE, ID and SCALE (mm per pixel) when the photo has a scale. Opens in MorphoJ and
                    tpsDig; tpsDig looks for the photos next to the .tps file. HEIC photos have a JPEG copy here.
                    Landmark 1 = vein hub; 2 = where the line from the leaf's centre through the hub meets the
                    edge (12 o'clock); 3-13 = where lines from the hub every 30 degrees clockwise meet the edge.
measurements.csv    one row per photo:
  ID, photo             the ID used in landmarks.tps (photo name without spaces) and the photo's file name
  image_in_tps          the IMAGE= name in landmarks.tps
  status                measured, or why not
  outline               automatic, automatic (strict colour: a shadow was merged in, check it) or hand-traced
  scale_mm_per_px       mm per pixel; scale_from = grid (found from the grid lines) or ruler (two clicked points)
  centroid_size_mm      leaf size: square root of the summed squared distances of the 13 landmarks from their
                        mean (the size measure geometric morphometrics uses)
  area_mm2, perimeter_mm  of the outline (automatic outlines are smoothed slightly for the perimeter)
  roundness             4 x pi x area / perimeter squared (1 = a perfect circle)
  gcc                   greenness: G / (R + G + B) inside the leaf, after white-balancing the photo to the paper
                        around the leaf. Compare only photos taken with the same camera and light.
  yellow_pct            % of the leaf that is yellow-brown rather than green
  glare_pct             % of the leaf that is very pale (glare); high values make gcc less reliable
  *_px                  the same sizes in pixels (useful when there is no scale)
  hub_offset_pct        how far the hub is from the leaf's centre, as % of the leaf radius (below 8% the
                        12 o'clock direction is unreliable)
  warnings              things to check in the photo's check picture
check_pictures      the outline (blue), centre (yellow cross), hub (1) and landmarks 2-13 for each photo,
                    marked ok or CHECK
session.json        the hubs, traces and scales, to reopen in {APP} (Open session)
"""


def selftest(app, spec_path):
    """For testing the built app: add photos, click hubs / trace / ruler through the real mouse handlers, save, take a
    screenshot and quit. spec: photos, square_mm, actions [{photo, hub | trace | ruler + mm}], out_parent, screenshot,
    report."""
    spec = json.load(open(spec_path, encoding="utf-8"))
    for key in ("<Right>", "<Next>", "<Left>", "<Prior>", "<Return>", "<Escape>", "<BackSpace>", "f", "F"):
        app.unbind_all(key)                     # typing elsewhere while the test window has focus can't change it
    app.square_mm.set(str(spec.get("square_mm", 5)))
    app.add_paths(spec["photos"])
    actions = list(spec.get("actions", []))
    simpledialog.askfloat = lambda *a, **k: app._ruler_mm               # the ruler's question, answered by the spec

    def click(pt):
        x, y = app.to_canvas(pt)
        app.canvas.event_generate("<ButtonPress-1>", x=round(x), y=round(y))

    def run_next():
        if app.pending:
            app.after(300, run_next)
            return
        if not actions:
            app.after(600, finish)
            return
        a = actions.pop(0)
        app.show(app.photos[a["photo"]])
        app.update()
        if "trace" in a:
            app.start_trace()
            click(a["trace"][0])
            for q in a["trace"][1:]:
                x, y = app.to_canvas(q)
                app.canvas.event_generate("<B1-Motion>", x=round(x), y=round(y), state=0x100)
            app.canvas.event_generate("<ButtonRelease-1>", x=round(x), y=round(y))
            app.finish_trace()
        if "hub" in a:
            click(a["hub"])
            app.canvas.event_generate("<ButtonRelease-1>")
        if "ruler" in a:
            app._ruler_mm = a["mm"]
            app.start_ruler()
            for q in a["ruler"]:
                click(q)
                app.canvas.event_generate("<ButtonRelease-1>")
        app.after(300, run_next)

    def finish():
        if app.photos:
            app.show(app.photos[spec.get("show", 0)])
        app.update()
        app.after(1500, finish2)

    def finish2():
        if spec.get("screenshot"):
            grab_window(app, spec["screenshot"])
        shown = app.photos.index(app.cur) if app.cur else None
        out = app.save_results(spec["out_parent"], quiet=True) if any(p.result for p in app.photos) else None
        json.dump(dict(out=out, shown=shown, photos=[dict(id=p.rid, status=p.status(), error=p.error) for p in app.photos]),
                  open(spec["report"], "w", encoding="utf-8"), indent=1)
        app.dirty = False
        app.destroy()

    app.after(800, run_next)


def grab_window(app, path):
    """Picture of the app window itself, even when other windows cover it (Windows PrintWindow), for the self-test."""
    import ctypes
    from ctypes import wintypes as W
    u, g, vp = ctypes.windll.user32, ctypes.windll.gdi32, ctypes.c_void_p
    for fn, args, res in ((u.GetWindowDC, [vp], vp), (g.CreateCompatibleDC, [vp], vp),
                          (g.CreateCompatibleBitmap, [vp, ctypes.c_int, ctypes.c_int], vp), (g.SelectObject, [vp, vp], vp),
                          (u.PrintWindow, [vp, vp, ctypes.c_uint], ctypes.c_int),
                          (g.GetDIBits, [vp, vp, ctypes.c_uint, ctypes.c_uint, vp, vp, ctypes.c_uint], ctypes.c_int),
                          (g.DeleteObject, [vp], ctypes.c_int), (g.DeleteDC, [vp], ctypes.c_int),
                          (u.ReleaseDC, [vp, vp], ctypes.c_int), (u.GetWindowRect, [vp, ctypes.POINTER(W.RECT)], ctypes.c_int)):
        fn.argtypes, fn.restype = args, res

    class Header(ctypes.Structure):
        _fields_ = [("size", W.DWORD), ("width", ctypes.c_long), ("height", ctypes.c_long), ("planes", W.WORD),
                    ("bits", W.WORD), ("compression", W.DWORD), ("image_size", W.DWORD), ("xppm", ctypes.c_long),
                    ("yppm", ctypes.c_long), ("used", W.DWORD), ("important", W.DWORD)]

    hwnd = int(app.wm_frame(), 16)
    r = W.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = u.GetWindowDC(hwnd)
    mdc, bmp = g.CreateCompatibleDC(hdc), g.CreateCompatibleBitmap(hdc, w, h)
    g.SelectObject(mdc, bmp)
    u.PrintWindow(hwnd, mdc, 2)                                       # 2 = PW_RENDERFULLCONTENT
    buf = ctypes.create_string_buffer(w * h * 4)
    head = Header(ctypes.sizeof(Header), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    g.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(head), 0)
    g.DeleteObject(bmp)
    g.DeleteDC(mdc)
    u.ReleaseDC(hwnd, hdc)
    Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB").save(path)


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)            # sharp text on high-resolution screens
        except Exception:
            pass
    app = App()
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest":
        selftest(app, sys.argv[2])
    app.mainloop()


if __name__ == "__main__":
    main()

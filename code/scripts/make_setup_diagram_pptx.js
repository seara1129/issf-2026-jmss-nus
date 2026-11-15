// Small flat 2D set-up diagram for the poster methods (the gap above box 2 of the methods diagram), redrawn from the
// user's sketch and set-up photo: clear tank on two stands, two trays of nasturtium seedlings, temperature + humidity
// sensor between them with its wires out through the floor, and a mist maker in a cup of water on a spray/wait timer,
// cabled to the tank floor. Native shapes and text (editable after uploading to Canva); labels use the methods
// diagram's green leader lines. Shaped like the gap (about 2.5 : 1).
// Usage: node make_setup_diagram_pptx.js <output .pptx>
const fs = require("fs");
const PptxGenJS = require("pptxgenjs");

const out = process.argv[2];
if (fs.existsSync(out)) throw new Error(`${out} already exists - not overwriting`);
const GREEN = "3D6B2C", DARK = "25451A", LEAF = "6F9E45", STEM = "9BBF6A", INK = "222222", PLASTIC = "7D8A92";
const SOIL = "6B4A2B", WATER = "A9CDEE", CABLE = "333333";
const W = 6.6, H = 2.62, FONT = 18;
const pres = new PptxGenJS();
pres.defineLayout({ name: "SETUP", width: W, height: H });
pres.layout = "SETUP";
pres.theme = { headFontFace: "Arial", bodyFontFace: "Arial" };
pres.title = "Set-up";
const slide = pres.addSlide();
slide.background = { color: "FFFFFF" };
const S = pres.shapes;
const none = { type: "none" };
const rect = (x, y, w, h, fill, line, name, shape = S.RECTANGLE, extra = {}) => slide.addShape(shape, { x, y, w, h,
  fill: fill ? { color: fill } : { type: "none" }, line: line || none, objectName: name, ...extra });
const seg = (x1, y1, x2, y2, color, width, name) => slide.addShape(S.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2),
  w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), flipV: (x2 - x1) * (y2 - y1) < 0, line: { color, width },
  objectName: name });
const path = (pts, color, width, name) => pts.slice(1).forEach((p, i) => seg(...pts[i], ...p, color, width, `${name} ${i + 1}`));
const dot = (x, y, r, fill, name, line) => rect(x - r, y - r, 2 * r, 2 * r, fill, line, name, S.OVAL);

// ---------- tank on two stands ----------
rect(0.3, 1.85, 0.7, 0.45, "EFE6D6", { color: "B9AB92", width: 1 }, "Stand left");
rect(2.1, 1.85, 0.7, 0.45, "EFE6D6", { color: "B9AB92", width: 1 }, "Stand right");
rect(0.1, 0.48, 2.9, 1.37, "F3F7F9", { color: PLASTIC, width: 1.5 }, "Tank");
rect(0.05, 0.36, 3.0, 0.12, "DFE7EC", { color: PLASTIC, width: 1.5 }, "Lid", S.ROUNDED_RECTANGLE, { rectRadius: 0.04 });
rect(1.25, 0.25, 0.5, 0.11, "F3F7F9", { color: PLASTIC, width: 1 }, "Lid fitting", S.ROUNDED_RECTANGLE,
  { rectRadius: 0.03 });

// ---------- two trays of seedlings (round nasturtium leaves) ----------
for (const [x0, side] of [[0.25, "left"], [1.8, "right"]]) {
  rect(x0, 1.4, 1.05, 0.42, SOIL, null, `Soil ${side}`);
  [[0.2, 1.06, 1], [0.52, 0.93, -1], [0.85, 1.1, 1]].forEach(([dx, top, s], i) => {
    const x = x0 + dx;
    seg(x, 1.4, x, top, STEM, 1.5, `Stem ${side} ${i + 1}`);
    dot(x + 0.14 * s, (top + 1.4) / 2 + 0.03, 0.08, LEAF, `Leaf ${side} ${i + 1}b`, { color: DARK, width: 0.75 });
    dot(x, top, 0.12, LEAF, `Leaf ${side} ${i + 1}`, { color: DARK, width: 0.75 });
  });
}

// ---------- sensor, its wires out through the floor, and the mist cable ----------
["D64545", "3A9A4A", "2F6DB5"].forEach((c, i) => seg(1.51 + 0.04 * i, 0.89, 1.51 + 0.04 * i, 2.0, c, 1, `Sensor wire ${i + 1}`));
rect(1.47, 0.6, 0.16, 0.24, "2F6DB5", { color: "1E4F8A", width: 0.75 }, "Sensor");
rect(1.47, 0.84, 0.16, 0.05, "F2C94C", null, "Sensor pins");
rect(1.66, 1.55, 0.1, 0.29, "FFFFFF", { color: PLASTIC, width: 1 }, "Mist cable end", S.ROUNDED_RECTANGLE,
  { rectRadius: 0.03 });
path([[1.71, 1.85], [1.71, 2.5], [4.3, 2.5], [4.3, 2.38]], CABLE, 2.25, "Cable tank-timer");

// ---------- timer and mist maker in a cup of water ----------
rect(4.0, 2.03, 0.6, 0.35, "333333", null, "Timer", S.ROUNDED_RECTANGLE, { rectRadius: 0.06 });
[4.15, 4.3, 4.45].forEach((x, i) => dot(x, 2.2, 0.035, "FFFFFF", `Timer button ${i + 1}`));
path([[4.6, 2.2], [4.85, 2.2], [4.85, 1.45], [5.62, 1.45], [5.62, 1.95]], CABLE, 2.25, "Cable timer-mister");
rect(5.32, 1.77, 0.61, 0.58, WATER, null, "Water");
rect(5.3, 1.5, 0.65, 0.87, null, { color: PLASTIC, width: 1.5 }, "Cup");
rect(5.5, 1.92, 0.24, 0.33, "FFFFFF", { color: PLASTIC, width: 1 }, "Mist maker", S.ROUNDED_RECTANGLE,
  { rectRadius: 0.05 });

// ---------- labels ----------
const text = { fontFace: "Arial", fontSize: FONT, color: INK, margin: 0, isTextBox: true, valign: "middle" };
slide.addText("Temp + humidity sensor", { ...text, x: 3.3, y: 0.52, w: 3.25, h: 0.36, objectName: "Label sensor" });
seg(3.22, 0.7, 1.66, 0.7, GREEN, 1.5, "Leader sensor");
dot(1.66, 0.7, 0.045, GREEN, "Leader sensor dot");
slide.addText("Mist maker on a timer", { ...text, x: 3.85, y: 0.98, w: 2.7, h: 0.36, objectName: "Label mist maker" });

pres.writeFile({ fileName: out }).then((f) => console.log(`wrote ${f}`));

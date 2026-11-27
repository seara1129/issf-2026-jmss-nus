// Editable PowerPoint version of the poster methods diagram, built from the layout that
// poster_methods_diagram_a0.py --editable writes. Boxes, numbers, titles, bullets and connector lines are native shapes
// and text (Arial, same sizes and positions as the PNG); the leaf drawing is one picture. Upload the .pptx to Canva, or
// open it in PowerPoint / Google Slides, to edit it; the text can then be switched to the poster's font.
// Usage: node make_methods_pptx.js <layout .json> <output .pptx>
const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");

const [layoutPath, outPath] = process.argv.slice(2);
if (fs.existsSync(outPath)) throw new Error(`${outPath} already exists - not overwriting`);
const L = JSON.parse(fs.readFileSync(layoutPath, "utf8"));
const m = L.metrics;
const hex = (c) => (c === "white" ? "FFFFFF" : c.replace("#", "").toUpperCase());
const GREEN = hex(L.colours.green), DARK = hex(L.colours.dark), INK = hex(L.colours.ink);
const PT = 7.2;                                   // points per diagram unit (1 unit = 0.1 in)
const X = (u) => u / 10;                          // diagram units -> inches
const Y = (u) => (L.H - u) / 10;                  // diagram y runs up from the bottom; slide y runs down from the top

const pres = new PptxGenJS();
pres.defineLayout({ name: "METHODS", width: L.W / 10, height: L.H / 10 });
pres.layout = "METHODS";
pres.theme = { headFontFace: "Arial", bodyFontFace: "Arial" };
pres.title = L.title;
const slide = pres.addSlide();
// see-through boxes (--no-fill) are shown on the poster's background colour, as they will look on the poster
slide.background = { color: L.boxes.some((b) => b.fill === "none") ? "E4E9D9" : "FFFFFF" };
const font = { fontFace: "Arial", margin: 0 };

const th = (L.title_pt * 1.5) / PT;
slide.addText(L.title, { ...font, x: 0, y: Y(L.title_y + th / 2), w: X(L.W), h: X(th), fontSize: L.title_pt, bold: true,
  color: DARK, align: "center", valign: "middle", isTextBox: true, objectName: "Title" });

slide.addImage({ path: path.join(path.dirname(layoutPath), L.leaf.file), x: X(L.leaf.x), y: Y(L.leaf.top),
  w: X(L.leaf.w), h: X(L.leaf.h), objectName: "Leaf drawing" });

// connector lines first, so the boxes sit on top of their ends as in the PNG
L.links.forEach(([x1, y1, x2, y2], i) => {
  const [sx1, sy1, sx2, sy2] = [X(x1), Y(y1), X(x2), Y(y2)];
  slide.addShape(pres.shapes.LINE, { x: Math.min(sx1, sx2), y: Math.min(sy1, sy2), w: Math.abs(sx2 - sx1),
    h: Math.abs(sy2 - sy1), flipV: (sx2 - sx1) * (sy2 - sy1) < 0, line: { color: GREEN, width: 1.8 },
    objectName: `Line ${i + 1}` });
  slide.addShape(pres.shapes.OVAL, { x: X(x2 - 0.7), y: Y(y2 + 0.7), w: X(1.4), h: X(1.4), fill: { color: GREEN },
    line: { type: "none" }, objectName: `Line ${i + 1} dot` });
});

for (const b of L.boxes) {
  const name = `Box ${b.num}`;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X(b.x), y: Y(b.top), w: X(b.w), h: X(b.h),
    fill: b.fill === "none" ? { type: "none" } : { color: hex(b.fill) },   // "none": see-through box (--no-fill)
    line: { color: GREEN, width: 2.4 }, rectRadius: 0.16, objectName: name });
  const cy = b.top - m.head, r = m.rad, cx = b.x + 1.4 * r;
  slide.addText(String(b.num), { ...font, shape: pres.shapes.OVAL, x: X(cx - r), y: Y(cy + r), w: X(2 * r), h: X(2 * r),
    fill: { color: GREEN }, line: { type: "none" }, fontSize: m.label, bold: true, color: "FFFFFF", align: "center",
    valign: "middle", objectName: `${name} number` });
  const tH = (m.body * 1.5) / PT;
  slide.addText(b.title, { ...font, x: X(b.x + m.tx), y: Y(cy + tH / 2), w: X(b.w - m.tx - m.rpad), h: X(tH),
    fontSize: m.body, bold: true, color: DARK, valign: "middle", isTextBox: true, objectName: `${name} title` });
  const yTop = b.top - m.first + 0.62 * m.step;  // top of the first bullet line
  // one paragraph per bullet, with soft line breaks where the PNG wraps (PowerPoint would otherwise break at dashes)
  // (paragraph options only on a bullet's first row: pptxgenjs starts a new paragraph at every run that has them)
  const items = b.rows.flatMap((rows, i) => rows.map((row, j) => {
    const last = j === rows.length - 1 && i < b.rows.length - 1;
    return { text: row, options: j === 0 ? { bullet: { indent: m.bul * PT }, paraSpaceAfter: m.gap * PT, breakLine: last }
      : { softBreakBefore: true, breakLine: last } };
  }));
  // the text box reaches almost to the box edge: PowerPoint's Arial runs a little wider than matplotlib's, and a
  // box exactly as wide as the PNG's text wraps the longest lines once more ("(2)" in box 4)
  slide.addText(items, { ...font, x: X(b.x + m.pad), y: Y(yTop), w: X(b.w - m.pad - 0.25 * m.rpad),
    h: X(yTop - (b.top - b.h) - 0.4 * m.bottom), fontSize: m.body, color: INK, valign: "top", lineSpacing: m.step * PT,
    isTextBox: true, objectName: `${name} text` });
}

pres.writeFile({ fileName: outPath }).then((f) => console.log(`wrote ${f}`));

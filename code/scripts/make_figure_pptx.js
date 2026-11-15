// Editable PowerPoint version of a poster figure, from editable_text.py's output: the figure without its text as one
// picture, every title, axis label, tick number, legend entry and note as an editable text box in the same place,
// size and colour, and the legend's dots and line samples as separate shapes. Upload the .pptx to Canva (or open it in
// PowerPoint) to edit it.
// Usage: node make_figure_pptx.js <..._text.json> <output .pptx>
const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");

const [layoutPath, outPath] = process.argv.slice(2);
if (fs.existsSync(outPath)) throw new Error(`${outPath} already exists - not overwriting`);
const L = JSON.parse(fs.readFileSync(layoutPath, "utf8"));
const pres = new PptxGenJS();
pres.defineLayout({ name: "FIGURE", width: L.width_in, height: L.height_in });
pres.layout = "FIGURE";
pres.theme = { headFontFace: "Arial", bodyFontFace: "Arial" };
const slide = pres.addSlide();
slide.background = { color: "E4E9D9" };          // the poster's background, so the preview looks as on the poster
slide.addImage({ path: path.join(path.dirname(layoutPath), L.image), x: 0, y: 0, w: L.width_in, h: L.height_in,
  objectName: "Graph (no text)" });

L.texts.forEach((t, i) => {
  // boxes don't wrap, so their size only matters for alignment: each is widened away from the side it is anchored to
  const upright = t.rotation === 0, long = upright ? t.w : t.h, short = upright ? t.h : t.w;
  const bw = long + 0.4, bh = short + 0.1, cx = t.x + t.w / 2, cy = t.y + t.h / 2;
  let x = cx - bw / 2;
  if (upright && t.ha === "left") x = t.x;
  if (upright && t.ha === "right") x = t.x + t.w - bw;
  slide.addText(t.text, { x, y: cy - bh / 2, w: bw, h: bh, rotate: upright ? 0 : 360 - t.rotation,
    fontFace: "Arial", fontSize: t.size, bold: t.bold, italic: t.italic, color: t.color.replace("#", "").toUpperCase(),
    align: upright ? t.ha : "center", valign: "middle", margin: 0, wrap: false,
    lineSpacing: +(0.94 * t.linespacing * t.size).toFixed(1),       // matplotlib's line pitch for Arial, in points
    isTextBox: true, objectName: `Text ${i + 1}` });
});

const hex = (c) => c.replace("#", "").toUpperCase();
(L.shapes || []).forEach((s, i) => {
  if (s.kind === "dot") {
    slide.addShape(pres.shapes.OVAL, { x: s.cx - s.d / 2, y: s.cy - s.d / 2, w: s.d, h: s.d, fill: { color: hex(s.fill) },
      line: { color: hex(s.edge), width: s.edge_pt }, objectName: `Legend symbol ${i + 1}` });
  } else {
    slide.addShape(pres.shapes.LINE, { x: Math.min(s.x1, s.x2), y: Math.min(s.y1, s.y2), w: Math.abs(s.x2 - s.x1),
      h: Math.abs(s.y2 - s.y1), line: { color: hex(s.color), width: s.width_pt }, objectName: `Legend symbol ${i + 1}` });
  }
});

pres.writeFile({ fileName: outPath }).then((f) => console.log(`wrote ${f}`));

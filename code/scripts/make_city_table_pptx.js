// Two-city comparison for the poster introduction, editable: Melbourne vs Singapore rows, plus a humidity strip that
// puts each city's typical humidity next to the terrarium that imitates it. Values are the ones in the poster's intro
// table, typed in here (not computed). Colours match the result figures, which use the poster's greens: dark green =
// Melbourne / Low humidity tank, sage = Singapore / High humidity tank (a darker sage for sage text, so it reads); the
// background is the poster's cream. Native shapes and text, so it can be uploaded to Canva and restyled.
// Usage: node make_city_table_pptx.js <output .pptx>
const fs = require("fs");
const PptxGenJS = require("pptxgenjs");

const out = process.argv[2];
if (fs.existsSync(out)) throw new Error(`${out} already exists - not overwriting`);
const MEL = "406327", SIN = "5E7A47", SIN_MARK = "7F9C65", INK = "222222", QUIET = "555555", RULE = "D5D9D0";
const TINT = "EDF1E5", PAPER = "FBFAF3";
const W = 16, H = 8.0, M = 0.3;
const pres = new PptxGenJS();
pres.defineLayout({ name: "CITIES", width: W, height: H });
pres.layout = "CITIES";
pres.theme = { headFontFace: "Arial", bodyFontFace: "Arial" };
pres.title = "Melbourne vs Singapore";
const slide = pres.addSlide();
slide.background = { color: PAPER };
const font = { fontFace: "Arial", margin: 0 };
const box = { ...font, isTextBox: true };

// ---------- Melbourne | row label | Singapore ----------
const colW = 5.3, midX = M + colW, midW = W - 2 * M - 2 * colW, rightX = W - M - colW;
for (const [name, x, fill] of [["Melbourne", M, MEL], ["Singapore", rightX, SIN_MARK]]) {
  slide.addText(name, { ...font, shape: pres.shapes.ROUNDED_RECTANGLE, x, y: M, w: colW, h: 0.95, rectRadius: 0.2,
    fill: { color: fill }, line: { type: "none" }, fontSize: 32, bold: true, color: "FFFFFF", align: "center",
    valign: "middle", objectName: `${name} header` });
}
slide.addText("vs", { ...box, x: midX, y: M, w: midW, h: 0.95, fontSize: 26, bold: true, color: QUIET, align: "center",
  valign: "middle", objectName: "vs" });
const rows = [["Climate", "Temperate", "Tropical"],
              ["Daytime high", "~14–26 °C (mean)", "31–33 °C"],
              ["PM2.5 sensors", "<20 official", "~60"]];
const RH0 = 1.45, RH = 0.85;
rows.forEach(([label, mel, sin], i) => {
  const y = RH0 + i * RH;
  if (i % 2 === 0) slide.addShape(pres.shapes.RECTANGLE, { x: M, y, w: W - 2 * M, h: RH, fill: { color: TINT },
    line: { type: "none" }, objectName: `Row ${i + 1} shading` });
  slide.addText(mel, { ...box, x: M, y, w: colW, h: RH, fontSize: 28, color: INK, align: "center", valign: "middle",
    objectName: `${label} Melbourne` });
  slide.addText(label, { ...box, x: midX, y, w: midW, h: RH, fontSize: 22, color: QUIET, align: "center",
    valign: "middle", objectName: `${label} label` });
  slide.addText(sin, { ...box, x: rightX, y, w: colW, h: RH, fontSize: 28, color: INK, align: "center",
    valign: "middle", objectName: `${label} Singapore` });
});

// ---------- humidity strip: cities on top, our terrariums underneath, one shared % RH scale ----------
const yh = RH0 + rows.length * RH + 0.4;
const yc = yh + 1.35, yt = yh + 2.6, ya = yh + 3.1;               // city row, tank row, axis
const sx0 = 3.7, sx1 = W - M - 0.6, x = (v) => sx0 + ((v - 40) / 60) * (sx1 - sx0);
slide.addText("Humidity (% RH)", { ...box, x: M, y: yh, w: 6, h: 0.5, fontSize: 24, bold: true, color: INK,
  valign: "middle", objectName: "Humidity title" });
for (const [label, y] of [["Cities", yc], ["Our terrariums", yt]]) {
  slide.addText(label, { ...box, x: M, y: y - 0.25, w: sx0 - M - 0.3, h: 0.5, fontSize: 22, color: QUIET,
    valign: "middle", objectName: `${label} row label` });
}
for (let v = 40; v <= 100; v += 10) {
  slide.addShape(pres.shapes.LINE, { x: x(v), y: yh + 0.75, w: 0, h: ya - yh - 0.75, line: { color: RULE, width: 1 },
    objectName: `Grid ${v}` });
  slide.addText(`${v}%`, { ...box, x: x(v) - 0.5, y: ya + 0.05, w: 1, h: 0.4, fontSize: 18, color: QUIET,
    align: "center", objectName: `Tick ${v}` });
}
const label = (cx, y, name, value, color) => slide.addText([{ text: name + " ", options: { bold: true } },
  { text: value }], { ...box, x: cx - 2.5, y: y - 0.62, w: 5, h: 0.4, fontSize: 20, color, align: "center",
  valign: "middle", objectName: `${name} label` });
for (const [name, v, note, color, mark] of [["Melbourne", 52, "~52% (afternoon)", MEL, MEL],
                                            ["Singapore", 82, "~82% (mean)", SIN, SIN_MARK]]) {
  slide.addShape(pres.shapes.OVAL, { x: x(v) - 0.17, y: yc - 0.17, w: 0.34, h: 0.34, fill: { color: mark },
    line: { color: "FFFFFF", width: 1.5 }, objectName: `${name} dot` });
  label(x(v), yc, name, note, color);
}
for (const [name, lo, hi, color, mark] of [["Low tank", 52, 54, MEL, MEL], ["High tank", 90, 96, SIN, SIN_MARK]]) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x(lo), y: yt - 0.16, w: x(hi) - x(lo), h: 0.32, rectRadius: 0.16,
    fill: { color: mark }, line: { type: "none" }, objectName: `${name} bar` });
  label((x(lo) + x(hi)) / 2, yt, name, `${lo}–${hi}%`, color);
}

pres.writeFile({ fileName: out }).then((f) => console.log(`wrote ${f}`));

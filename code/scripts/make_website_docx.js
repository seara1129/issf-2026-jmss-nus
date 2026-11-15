// Word copy of the website's text, for editing: every heading, paragraph, list row, caption, button and placeholder
// in page order (from website_to_blocks.py's blocks.json), with small pictures showing where each figure and photo
// sits. Yellow = still to fill in; [square brackets] = describes something on the page.
// Usage: node make_website_docx.js <blocks.json> <output .docx>
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, HeadingLevel, AlignmentType, LevelFormat, BorderStyle, ShadingType,
} = require("docx");

const [blocksPath, outPath] = process.argv.slice(2);
if (fs.existsSync(outPath)) throw new Error(`${outPath} already exists - not overwriting`);
const blocks = JSON.parse(fs.readFileSync(blocksPath, "utf8"));
const GREEN = "2F4A1C", SAGE = "5E7A47", GREY = "595959", ACCENT = "C0502A";
const PAGE_W_IN = 6.3;                                   // A4 with 2.5 cm margins

function runs(rs, extra = {}) {
  const out = [];
  rs.forEach((r) => {
    r.t.split("\n").forEach((part, i) => {
      out.push(new TextRun({ text: part, break: i ? 1 : 0, bold: r.bold || extra.bold, italics: r.italic || extra.italics,
        highlight: r.todo || extra.todo ? "yellow" : undefined, color: extra.color, size: extra.size }));
    });
  });
  return out;
}

function picture(b, widthIn) {
  const w = Math.round(widthIn * 72), h = Math.round(w * b.h / b.w);       // docx-js sizes images in points-ish px
  return new ImageRun({ type: path.extname(b.path).slice(1).replace("jpeg", "jpg"), data: fs.readFileSync(b.path),
    transformation: { width: w, height: h } });
}

const children = [
  new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("Website text for editing")] }),
  new Paragraph({
    shading: { type: ShadingType.CLEAR, fill: "EEF2E6" },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: SAGE, space: 8 } },
    spacing: { after: 120 },
    children: [new TextRun({ text: "How to use this: ", bold: true }),
      new TextRun("change any text below, in the same order as on the website. Turning on Review > Track Changes first " +
        "makes your edits easy to copy back. Yellow text is still to be filled in. Text in [square brackets] describes " +
        "something on the page, such as a button or a photo strip. The pictures only show where each figure or photo " +
        "goes; to change one, write a note next to it.")],
  }),
];
let numInstance = 0, prevKind = "";
blocks.forEach((b) => {
  switch (b.kind) {
    case "h1": children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: runs(b.runs) })); break;
    case "h2": children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: runs(b.runs) })); break;
    case "h3": children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: runs(b.runs) })); break;
    case "h4": children.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: runs(b.runs) })); break;
    case "label":
      children.push(new Paragraph({ spacing: { before: 360, after: 0 }, keepNext: true,
        children: runs(b.runs, { bold: true, color: ACCENT, size: 18 }) }));
      break;
    case "bullet": children.push(new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(b.runs) })); break;
    case "num":
      if (prevKind !== "num") numInstance += 1;          // each list starts again at 1
      children.push(new Paragraph({ numbering: { reference: "numbers", level: 0, instance: numInstance }, children: runs(b.runs) }));
      break;
    case "figcaption":
      children.push(new Paragraph({ spacing: { after: 200 }, children: runs(b.runs, { italics: true, color: GREY, size: 20 }) }));
      break;
    case "note": children.push(new Paragraph({ keepNext: true, children: runs(b.runs, { italics: true, color: SAGE, size: 20 }) })); break;
    case "todo": children.push(new Paragraph({ children: runs([{ t: "[Placeholder] " }, ...b.runs], { todo: true }) })); break;
    case "button": children.push(new Paragraph({ children: runs([{ t: "[Button] " }, ...b.runs], { bold: true, color: GREEN }) })); break;
    case "img":
      children.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
        children: [picture(b, Math.min(4.6, PAGE_W_IN) * (b.h > b.w * 1.2 ? 0.6 : 1))] }));
      break;
    case "pair": {
      const each = b.imgs.length > 2 ? 1.45 : 2.4, items = [];
      b.imgs.forEach((im, i) => { if (i) items.push(new TextRun("  ")); items.push(picture(im, each)); });
      children.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 }, children: items }));
      break;
    }
    default: children.push(new Paragraph({ children: runs(b.runs) }));
  }
  if (b.kind !== "img" && b.kind !== "pair") prevKind = b.kind;   // pictures inside a list don't restart its numbers
});

const heading = (size, font, color, before, after) => ({
  run: { font, size, bold: false, color }, paragraph: { spacing: { before, after }, keepNext: true, keepLines: true } });
const doc = new Document({
  creator: "", title: "Website text for editing",
  styles: {
    default: { document: { run: { font: "Arial", size: 22 }, paragraph: { spacing: { after: 100, line: 276 } } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", run: { font: "Georgia", size: 40, color: GREEN }, paragraph: { spacing: { before: 0, after: 200 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, ...heading(36, "Georgia", GREEN, 120, 120) },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, ...heading(28, "Georgia", GREEN, 320, 100) },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Arial", size: 22, bold: true, color: "1D2616" }, paragraph: { spacing: { before: 200, after: 60 }, keepNext: true } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 360, hanging: 260 } } } }] },
    { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 360, hanging: 300 } } } }] },
  ] },
  sections: [{ properties: { page: { margin: { top: 1300, bottom: 1300, left: 1417, right: 1417 } } }, children }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(outPath, buf); console.log(`wrote ${outPath}`); });

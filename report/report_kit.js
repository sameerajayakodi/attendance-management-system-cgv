/**
 * report_kit.js - document-building helpers for build_report.js
 *
 *   Used by build_report.js; not run directly.
 *
 * Every number quoted in the report comes from an actual run of the prototype
 * (see prototype/tools/evaluate.py and prototype/tests/run_tests.py); the
 * figures are the PNGs those programs wrote into report/figures.
 */

const fs = require("fs");
const path = require("path");
const {
  AlignmentType, BorderStyle, Document, Footer, Header, HeadingLevel, ImageRun,
  PageBreak, PageNumber, Packer, Paragraph, ShadingType, Table, TableCell,
  TableOfContents, TableRow, TextRun, WidthType, VerticalAlign,
} = require("docx");

const FIG_DIR = path.join(__dirname, "figures");
const CONTENT_DXA = 9026;      // A4 minus 1 inch margins
const CONTENT_PX = 600;

//  Small helpers


let figureNo = 0;
let tableNo = 0;
let equationNo = 0;

const INK = "1A1A1A";
const MUTED = "5A5A5A";
const ACCENT = "1F4E79";
const HEADER_FILL = "E8EDF3";
const ZEBRA_FILL = "F5F7FA";

function pngSize(file) {
  const buffer = fs.readFileSync(file);
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

function p(text, options = {}) {
  const { size = 22, bold = false, italics = false, align, spacingAfter = 120,
          spacingBefore = 0, color = INK, font, indent } = options;
  return new Paragraph({
    alignment: align,
    spacing: { after: spacingAfter, before: spacingBefore, line: 276 },
    indent,
    children: [new TextRun({ text, size, bold, italics, color, font })],
  });
}

/** A paragraph built from [text, {bold/italics/code}] fragments. */
function rich(parts, options = {}) {
  const { align, spacingAfter = 120, spacingBefore = 0, indent } = options;
  return new Paragraph({
    alignment: align,
    spacing: { after: spacingAfter, before: spacingBefore, line: 276 },
    indent,
    children: parts.map((part) => {
      if (typeof part === "string") return new TextRun({ text: part, size: 22, color: INK });
      return new TextRun({
        text: part.text,
        size: part.size || (part.code ? 20 : 22),
        bold: !!part.bold,
        italics: !!part.italics,
        color: part.color || INK,
        font: part.code ? "Consolas" : part.font,
      });
    }),
  });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 200 },
    pageBreakBefore: true,
    children: [new TextRun({ text, size: 32, bold: true, color: ACCENT })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 300, after: 140 },
    children: [new TextRun({ text, size: 26, bold: true, color: ACCENT })],
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, size: 23, bold: true, color: INK })],
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    bullet: { level },
    spacing: { after: 80, line: 276 },
    children: [new TextRun({ text, size: 22, color: INK })],
  });
}

function numbered(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "report-numbering", level },
    spacing: { after: 80, line: 276 },
    children: [new TextRun({ text, size: 22, color: INK })],
  });
}

function code(lines) {
  const rows = Array.isArray(lines) ? lines : [lines];
  return rows.map((line, index) =>
    new Paragraph({
      spacing: { after: index === rows.length - 1 ? 160 : 0, before: index === 0 ? 60 : 0, line: 240 },
      shading: { type: ShadingType.CLEAR, fill: "F4F4F4" },
      indent: { left: 240 },
      children: [new TextRun({ text: line || " ", size: 18, font: "Consolas", color: "202020" })],
    })
  );
}

/** Centred italic display equation with a right-aligned number. */
function equation(text, note) {
  equationNo += 1;
  const out = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 140, after: note ? 40 : 160 },
      children: [
        new TextRun({ text: text, size: 22, italics: true, font: "Cambria", color: INK }),
        new TextRun({ text: `        (${equationNo})`, size: 20, color: MUTED }),
      ],
    }),
  ];
  if (note) {
    out.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 160 },
      children: [new TextRun({ text: note, size: 18, italics: true, color: MUTED })],
    }));
  }
  return out;
}

function figure(fileName, caption, widthPx = CONTENT_PX) {
  const file = path.join(FIG_DIR, fileName);
  if (!fs.existsSync(file)) {
    console.warn(`  ! missing figure: ${fileName}`);
    return [p(`[figure missing: ${fileName}]`, { italics: true, color: "AA0000", align: AlignmentType.CENTER })];
  }
  figureNo += 1;
  const { width, height } = pngSize(file);
  const scaled = Math.min(widthPx, width);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 200, after: 80 },
      children: [
        new ImageRun({
          type: "png",
          data: fs.readFileSync(file),
          transformation: { width: scaled, height: Math.round((height * scaled) / width) },
        }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 240 },
      children: [
        new TextRun({ text: `Figure ${figureNo}. `, size: 19, bold: true, color: MUTED }),
        new TextRun({ text: caption, size: 19, italics: true, color: MUTED }),
      ],
    }),
  ];
}

function cell(text, options = {}) {
  const { bold = false, fill, width, align = AlignmentType.LEFT, size = 19 } = options;
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: fill ? { type: ShadingType.CLEAR, fill } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 60, bottom: 60, left: 110, right: 110 },
    children: [
      new Paragraph({
        alignment: align,
        spacing: { after: 0, line: 240 },
        children: [new TextRun({ text: String(text), size, bold, color: INK })],
      }),
    ],
  });
}

/**
 * A caption-above table.  Column widths are given in DXA and must sum to the
 * table width, and each cell repeats its width - Google Docs renders
 * percentage widths incorrectly, so DXA is used throughout.
 */
function table(caption, columnWidths, header, rows, options = {}) {
  const { aligns = [], zebra = true } = options;
  tableNo += 1;
  const captionParagraph = new Paragraph({
    spacing: { before: 200, after: 100 },
    children: [
      new TextRun({ text: `Table ${tableNo}. `, size: 19, bold: true, color: MUTED }),
      new TextRun({ text: caption, size: 19, italics: true, color: MUTED }),
    ],
  });

  const headerRow = new TableRow({
    tableHeader: true,
    children: header.map((text, index) =>
      cell(text, { bold: true, fill: HEADER_FILL, width: columnWidths[index], align: aligns[index] })
    ),
  });

  const bodyRows = rows.map((row, rowIndex) =>
    new TableRow({
      children: row.map((text, index) =>
        cell(text, {
          width: columnWidths[index],
          align: aligns[index],
          fill: zebra && rowIndex % 2 === 1 ? ZEBRA_FILL : undefined,
        })
      ),
    })
  );

  return [
    captionParagraph,
    new Table({
      width: { size: columnWidths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
      columnWidths,
      borders: {
        top: { style: BorderStyle.SINGLE, size: 4, color: "B4C2D4" },
        bottom: { style: BorderStyle.SINGLE, size: 4, color: "B4C2D4" },
        left: { style: BorderStyle.SINGLE, size: 4, color: "B4C2D4" },
        right: { style: BorderStyle.SINGLE, size: 4, color: "B4C2D4" },
        insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: "D5DDE7" },
        insideVertical: { style: BorderStyle.SINGLE, size: 2, color: "D5DDE7" },
      },
      rows: [headerRow, ...bodyRows],
    }),
    p("", { spacingAfter: 200 }),
  ];
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

module.exports = {
  fs, path, FIG_DIR, CONTENT_DXA, CONTENT_PX, INK, MUTED, ACCENT, HEADER_FILL, ZEBRA_FILL,
  AlignmentType, BorderStyle, Document, Footer, Header, HeadingLevel, ImageRun, PageBreak,
  PageNumber, Packer, Paragraph, ShadingType, Table, TableCell, TableOfContents, TableRow,
  TextRun, WidthType, VerticalAlign,
  p, rich, h1, h2, h3, bullet, numbered, code, equation, figure, table, pageBreak, pngSize,
  counters: {
    get figureNo() { return figureNo; },
    get tableNo() { return tableNo; },
    get equationNo() { return equationNo; },
  },
};

/**
 * build_report.js - generates CS402.3_CGV_Coursework_Report.docx
 *
 *     node build_report.js
 *
 * Every number quoted in the report comes from an actual run of the prototype
 * (prototype/tools/evaluate.py and prototype/tests/run_tests.py); the figures
 * are the PNGs those programs wrote, copied into report/figures by
 * prototype/tools/make_figures.py --copy-to-report.
 *
 * >>> BEFORE SUBMITTING: replace the ten placeholder entries in MEMBERS below
 *     with the real names and index numbers of the group. <<<
 */

const fs = require("fs");
const path = require("path");
const {
  AlignmentType, Document, Footer, Header, LevelFormat, Packer, PageNumber,
  Paragraph, TextRun,
} = require("docx");

const K = require("./report_kit");
const main = require("./content_main");
const contrib = require("./content_contributions");

// ---------------------------------------------------------------------------
//  Group members - EDIT THESE TEN LINES BEFORE SUBMISSION


const MEMBERS = [
  { name: "<< Member 1 - full name >>",  index: "<< index >>", role: "Project Lead and Systems Architect" },
  { name: "<< Member 2 - full name >>",  index: "<< index >>", role: "Image Acquisition and Pre-processing Engineer" },
  { name: "<< Member 3 - full name >>",  index: "<< index >>", role: "Binarisation and Thresholding Engineer" },
  { name: "<< Member 4 - full name >>",  index: "<< index >>", role: "Geometric Rectification Engineer" },
  { name: "<< Member 5 - full name >>",  index: "<< index >>", role: "Table Detection Engineer (morphology)" },
  { name: "<< Member 6 - full name >>",  index: "<< index >>", role: "Signature Segmentation and Classification Engineer" },
  { name: "<< Member 7 - full name >>",  index: "<< index >>", role: "Data Modelling and Persistence Engineer" },
  { name: "<< Member 8 - full name >>",  index: "<< index >>", role: "Data Visualisation Engineer" },
  { name: "<< Member 9 - full name >>",  index: "<< index >>", role: "Signature Recognition Engineer" },
  { name: "<< Member 10 - full name >>", index: "<< index >>", role: "Quality Assurance and Evaluation Engineer" },
];

// ---------------------------------------------------------------------------

function runningHeader() {
  return new Header({
    children: [
      new Paragraph({
        alignment: AlignmentType.RIGHT,
        spacing: { after: 60 },
        border: { bottom: { style: "single", size: 4, color: "C8D2DE", space: 6 } },
        children: [
          new TextRun({
            text: "CS402.3  Computer Graphics and Visualization  |  Student Attendance Management System",
            size: 16,
            color: "6E7A88",
          }),
        ],
      }),
    ],
  });
}

function runningFooter() {
  return new Footer({
    children: [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text: "Page ", size: 16, color: "6E7A88" }),
          new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "6E7A88" }),
          new TextRun({ text: " of ", size: 16, color: "6E7A88" }),
          new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, color: "6E7A88" }),
        ],
      }),
    ],
  });
}

function build() {
  const body = [
    ...main.titlePage(MEMBERS),
    ...main.contents(),
    ...main.introduction(),
    ...main.systemOverview(),
    ...main.methodology(),
    ...main.dataLayer(),
    ...main.visualisation(),
    ...main.recognition(),
    ...main.testing(),
    ...main.discussion(),
    ...main.conclusion(),
    ...main.references(),
    ...contrib.contributions(MEMBERS),
    ...contrib.appendices(),
  ];

  return new Document({
    creator: "CS402.3 group coursework",
    title: "Student Attendance Management System - CS402.3 Coursework Report",
    description: "Image processing and data visualisation prototype for reading paper signing sheets.",
    styles: {
      default: {
        document: { run: { font: "Calibri", size: 22, color: K.INK } },
      },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 32, bold: true, color: K.ACCENT, font: "Calibri" } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 26, bold: true, color: K.ACCENT, font: "Calibri" } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 23, bold: true, color: K.INK, font: "Calibri" } },
      ],
    },
    numbering: {
      config: [
        {
          reference: "report-numbering",
          levels: [
            { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.START,
              style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
            { level: 1, format: LevelFormat.LOWER_LETTER, text: "%2.", alignment: AlignmentType.START,
              style: { paragraph: { indent: { left: 1440, hanging: 360 } } } },
          ],
        },
      ],
    },
    features: { updateFields: true },
    sections: [
      {
        properties: {
          page: {
            margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
          },
        },
        headers: { default: runningHeader() },
        footers: { default: runningFooter() },
        children: body,
      },
    ],
  });
}

const outputPath = path.join(__dirname, "CS402.3_CGV_Coursework_Report.docx");

Packer.toBuffer(build())
  .then((buffer) => {
    fs.writeFileSync(outputPath, buffer);
    const stats = fs.statSync(outputPath);
    console.log(`Wrote ${outputPath}`);
    console.log(`  ${(stats.size / 1024).toFixed(0)} KB`);
    console.log(`  ${K.counters.figureNo} figures, ${K.counters.tableNo} tables, ${K.counters.equationNo} equations`);
  })
  .catch((error) => {
    console.error("Failed to build the report:", error);
    process.exitCode = 1;
  });

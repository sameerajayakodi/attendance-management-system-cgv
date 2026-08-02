/**
 * content_main.js - sections 1 to 10 of the coursework report.
 */

const K = require("./report_kit");
const { p, rich, h1, h2, h3, bullet, code, equation, figure, table, pageBreak } = K;
const { AlignmentType } = K;

// --------------------------------------------------------------------------
//  Measured results (all produced by prototype/tools/evaluate.py)
// --------------------------------------------------------------------------

const CELLS = [
  ["10000409", "M S Dilshanika Perera", "15.97 P", "14.67 P", "14.67 P", "13.75 P", "11.51 P", "5/5"],
  ["10009301", "C W M A Shehan Abeyrathne", "8.54 P", "11.64 P", "0.47 A", "0.35 A", "11.20 P", "3/5"],
  ["10009302", "B A K M Chithrananda", "9.17 P", "11.77 P", "0.00 A", "4.44 P", "4.62 P", "4/5"],
  ["10009303", "W Shashini Minosha De Silva", "9.39 P", "10.32 P", "11.60 P", "0.44 A", "11.33 P", "4/5"],
  ["10009304", "K L Udara Maduranga Liyanage", "5.70 P", "6.41 P", "6.84 P", "6.64 P", "10.74 P", "5/5"],
  ["10009306", "Hansa Anuradha Wickramanayake", "3.30 P", "4.53 P", "12.21 P", "6.73 P", "15.01 P", "5/5"],
];

const STAGE_TIMES = [
  ["1", "Acquisition", "Rescale to the working resolution", "26.7", "20.8 - 39.8"],
  ["2", "Greyscale", "BT.601 luma conversion", "1.0", "0.7 - 1.5"],
  ["3", "Illumination correction", "Divide out the estimated shading field", "70.8", "67.7 - 74.5"],
  ["4", "Edge-preserving denoise", "Bilateral filter", "40.8", "34.6 - 45.2"],
  ["5", "Binarisation", "Adaptive Gaussian threshold (+ Otsu)", "30.1", "27.5 - 34.1"],
  ["6", "Skew correction", "Hough line angle, then rotate and re-binarise", "452.1", "429.8 - 468.2"],
  ["7", "Rule extraction", "Morphological opening, two orientations", "24.8", "23.9 - 25.8"],
  ["8", "Table reconstruction", "Projection profiles, grid, repair", "13.3", "12.3 - 14.2"],
  ["9", "Signature analysis", "Component ownership and thresholding", "25.9", "18.9 - 46.6"],
];

// --------------------------------------------------------------------------

function titlePage(members) {
  const rows = members.map((m, i) => [String(i + 1), m.index, m.name, m.role]);
  return [
    p("NSBM Green University Town", { align: AlignmentType.CENTER, size: 26, bold: true, spacingBefore: 600 }),
    p("School of Computing", { align: AlignmentType.CENTER, size: 24, spacingAfter: 60 }),
    p("BSc (Hons) in Software Engineering", { align: AlignmentType.CENTER, size: 22, color: K.MUTED, spacingAfter: 500 }),

    p("CS402.3", { align: AlignmentType.CENTER, size: 30, bold: true, color: K.ACCENT, spacingAfter: 60 }),
    p("Computer Graphics and Visualization", { align: AlignmentType.CENTER, size: 28, bold: true, color: K.ACCENT, spacingAfter: 400 }),

    p("Group Coursework 2026 / 2027", { align: AlignmentType.CENTER, size: 22, color: K.MUTED, spacingAfter: 200 }),
    p("Student Attendance Management System (SAMS)", { align: AlignmentType.CENTER, size: 26, bold: true, spacingAfter: 60 }),
    p("Automated reading of paper signing sheets by image processing,", { align: AlignmentType.CENTER, size: 22, italics: true, color: K.MUTED, spacingAfter: 20 }),
    p("with attendance visualisation and signature verification", { align: AlignmentType.CENTER, size: 22, italics: true, color: K.MUTED, spacingAfter: 420 }),

    ...table(
      "Group members, indices and roles.",
      [700, 1900, 3200, 3226],
      ["No", "Student Index", "Name", "Role in the project"],
      rows,
      { aligns: [AlignmentType.CENTER] }
    ),

    p("Module Leader: Dr. Rasika Ranaweera", { align: AlignmentType.CENTER, size: 22, spacingBefore: 320, spacingAfter: 40 }),
    p("ranaweera.r@nsbm.lk", { align: AlignmentType.CENTER, size: 20, color: K.MUTED, spacingAfter: 40 }),
    p("Date of submission: ____________________", { align: AlignmentType.CENTER, size: 20, color: K.MUTED }),
    pageBreak(),
  ];
}

function contents() {
  return [
    p("Contents", { size: 30, bold: true, color: K.ACCENT, spacingAfter: 220 }),
    new K.TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-3" }),
    p("(In Word: right-click this table and choose Update Field to build the page numbers.)",
      { size: 18, italics: true, color: K.MUTED, spacingBefore: 200 }),
    pageBreak(),
  ];
}

function introduction() {
  return [
    h1("1. Introduction"),

    h2("1.1 The scenario"),
    p("Attendance at NSBM Green University Town is recorded on paper. A printed signing sheet is circulated during each lecture; every student signs the row bearing their index number, and the lecturer signs the header table. The completed sheets are then photographed with a smart phone by the administrative staff and passed to the department as ordinary JPEG files, together with a roster file that lists the students enrolled in the subject."),
    p("Turning that pile of photographs into usable attendance data is, at present, a manual clerical task. This coursework asks for a prototype that automates it: given a photograph of a signing sheet and an XML roster, the program must decide for each student whether a signature appears against their name, record the outcome in a local database, and present a student's attendance graphically."),

    h2("1.2 Objectives"),
    p("The system was built to satisfy five concrete objectives:"),
    bullet("Read an unconstrained smart-phone photograph of a signing sheet - hand-held, unevenly lit, slightly rotated - without asking the photographer to change anything about how the picture is taken."),
    bullet("Locate the roster table on the sheet automatically, rather than assuming fixed pixel coordinates, so that the same program works on every photograph of the same printed form."),
    bullet("Decide PRESENT or ABSENT for each roster row from the ink in its signature cell, and show every intermediate step of the image processing while it runs."),
    bullet("Store the result in a local database that can be re-run over the same sheet without creating duplicate records."),
    bullet("Visualise a student's attendance, and compare the signatures a student has left across sessions in order to flag any that do not match."),

    h2("1.3 Scope of the prototype"),
    p("The deliverable is a working command-line prototype in Python, built on OpenCV, NumPy and Matplotlib. Three programs make up the system, and their invocation follows the brief exactly:"),
    ...code([
      "$ python sams.py 31.05.2019.jpeg info.xml",
      "$ python infovis.py 10000409",
      "$ python investigate.py 10000409",
    ]),
    p("Deliberately outside the scope are optical character recognition of the printed or hand-written text (the session date is taken from the file name, as the brief's own example implies), any cloud or web component, and any machine-learning model that would need training data the coursework does not supply."),

    h2("1.4 How this report is organised"),
    p("Section 2 gives the architecture of the system. Section 3 is the substance of the image-processing work: the nine stages of the pipeline, the mathematics behind each, and the output of each stage on a real sheet. Section 4 covers the roster format and the database. Sections 5 and 6 cover data visualisation and signature recognition. Section 7 reports the testing: the accuracy of the system on all five supplied sheets, measured against a hand-labelled ground truth, together with the unit-test results and an honest evaluation of the recognition module. Section 8 discusses the difficulties encountered and how each was resolved, and Section 9 concludes. Section 11 records the individual contribution of each group member."),
  ];
}

function systemOverview() {
  return [
    h1("2. System overview"),

    h2("2.1 Architecture"),
    p("The prototype is organised into four layers, each depending only on the layer beneath it. The entry points contain no image processing; the processing modules know nothing about databases or charts; and every tunable parameter lives in a single configuration object rather than being scattered through the algorithms as literal numbers."),
    ...figure("architecture.png", "Layered architecture of the prototype. Arrows show the direction of dependency."),
    p("The pipeline itself is expressed as a list of interchangeable stage objects. Each stage is a small class with one responsibility that reads from and writes to a shared context, returns the image it wants displayed, and knows nothing about the stages on either side of it:"),
    ...code([
      "class ProcessingStage(ABC):",
      "    name: str = \"stage\"",
      "    description: str = \"\"",
      "",
      "    @abstractmethod",
      "    def apply(self, context: PipelineContext) -> np.ndarray | None:",
      "        \"\"\"Perform the work and return the image to display.\"\"\"",
      "",
      "    def run(self, order: int, context: PipelineContext) -> StageArtifact:",
      "        started = time.perf_counter()",
      "        image = self.apply(context)",
      "        elapsed = (time.perf_counter() - started) * 1000.0",
      "        return StageArtifact(order=order, name=self.name, image=image,",
      "                             elapsed_ms=elapsed, notes=self.notes(context))",
    ]),
    p("Because the pipeline is a list, adding, removing or reordering a processing step is a one-line change and needs no edit to the orchestration code. The abstract base class also gives every stage its timing and its progress reporting for free, which is how the per-stage timings in Table 3 were obtained."),

    h2("2.2 Modules"),
    ...table(
      "The implementation package. Each module has a single responsibility.",
      [2100, 6926],
      ["Module", "Responsibility"],
      [
        ["config.py", "Every tunable parameter, with the reasoning for its value recorded beside it"],
        ["imaging.py", "Pure image-processing primitives: rescale, rotate, flat-field, denoise, binarise"],
        ["table.py", "Morphological rule extraction, grid reconstruction, and grid repair"],
        ["signature.py", "Ink isolation, component ownership, and the PRESENT/ABSENT decision"],
        ["stages.py", "The nine pipeline steps, as interchangeable objects"],
        ["pipeline.py", "Orchestration, roster mapping, persistence"],
        ["progress.py", "Progress presentation: console trace, live windows, stage PNGs"],
        ["records.py", "info.xml parsing, including the brief's non-conforming Figure-1 layout"],
        ["database.py", "SQLite persistence with upsert semantics"],
        ["visualize.py", "Attendance dashboards and the batch matrix"],
        ["verify.py", "Signature descriptors (HOG, zoning, ORB) and their comparison"],
      ]
    ),

    h2("2.3 Progress reporting"),
    p("The brief requires the program to show the progress of the image processing while it runs. Rather than scatter print and imshow calls through the algorithms, reporting is expressed as a small polymorphic hierarchy: an abstract ProgressReporter with a console implementation, a live-window implementation, an implementation that writes every stage to disk as a PNG, and a composite that fans one call out to all of them. The pipeline talks only to the abstract interface, so a new presentation could be added without touching a single line of processing code."),
    ...code([
      "==========================================================================",
      "  SAMS  |  28.06.2019.jpeg  |  CS402.3",
      "==========================================================================",
      "[........................] 1/9  Acquisition",
      "             Load the photograph and rescale it to the working resolution.",
      "             -> done in   23.1 ms  (input=3024x4032  scale=0.562)",
      "[##......................] 2/9  Greyscale",
      "             Convert BGR to luma (Y = 0.299R + 0.587G + 0.114B).",
      "             -> done in    1.0 ms",
      "                              ...",
      "[##################......] 8/9  Table reconstruction",
      "             Group the rules into grids and select the roster table.",
      "             -> done in   14.6 ms  (tables=2  rows=6  cols=4  cv=0.011)",
      "[#####################...] 9/9  Signature analysis",
      "             Subtract the rules, group the ink, charge each blob to a row.",
      "             -> done in   16.9 ms  (present=4  absent=2)",
      "[########################] 9/9  complete in 692 ms",
    ]),
  ];
}

function methodology() {
  return [
    h1("3. Image-processing methodology"),
    p("This section describes the nine stages that turn a photograph into a set of PRESENT/ABSENT decisions. Figure 2 shows all nine applied to one of the supplied sheets; the sections that follow explain each in turn."),
    ...figure("pipeline_contact_sheet.png", "The complete pipeline applied to 28.06.2019.jpeg. Every image in this contact sheet is real output, written automatically by sams.py to output/stages/.", 560),

    h2("3.1 Acquisition and the working resolution"),
    p("The supplied photographs are 3024 x 4032 pixels. Every image is first rescaled to a fixed working width of 1700 pixels. This is not merely a speed optimisation, although it does reduce the cost of the morphology by roughly a factor of three. Its real purpose is to make the pipeline resolution-independent: all the structuring elements and neighbourhood sizes used downstream describe a physical size on the page - wider than a pen stroke, about one character tall - and if they were fixed in pixels the algorithm would behave differently on a photograph from a different camera."),
    p("Those parameters that are still expressed in pixels are scaled explicitly from a reference width. For example, the adaptive-threshold window is:"),
    ...code([
      "REFERENCE_WIDTH: int = 1700",
      "",
      "def adaptive_block_for(self, width: int) -> int:",
      "    return self._scaled_odd(self.adaptive_block, width, 11)",
    ]),
    p("Section 7.7 shows the effect: without this scaling, processing the same sheets at native resolution loses rules and drops rows."),

    h2("3.2 Greyscale conversion"),
    p("Colour is not needed to find ink. The three channels are collapsed to a single luminance channel using the ITU-R BT.601 weighting, which approximates the sensitivity of human vision and is the conversion OpenCV performs for COLOR_BGR2GRAY:"),
    ...equation("Y(x, y) = 0.299 R(x, y) + 0.587 G(x, y) + 0.114 B(x, y)"),
    p("Colour is not discarded entirely: the original BGR image is retained so that the pen colour of each signature can be reported later (Section 3.9), and so that the stored signature specimens are the photograph as taken rather than a binary silhouette."),

    h2("3.3 Illumination correction"),
    p("A hand-held photograph of a sheet of paper is never evenly lit. The photographer's own shadow falls across the page, the paper curls, and the phone's flash - when it fires at all - produces a bright hot-spot. A single global threshold applied to such an image will over-segment the shadowed corner and under-segment the bright one."),
    p("The correction used here is morphological. A closing with a structuring element wider than any glyph removes all the writing and leaves only the paper, which is an estimate B of the illumination field. Dividing the original by that estimate produces a flat-field image in which the paper is uniformly white:"),
    ...equation("B(x, y) = (I • S)(x, y) = (I ⊕ S) ⊖ S", "where S is a 41-pixel elliptical structuring element at the reference width"),
    ...equation("F(x, y) = 255 · I(x, y) / B(x, y)"),
    p("The effect is measurable. On the reference sheets the standard deviation of the grey levels falls from 33.0 before correction to 28.6 after it, and - more importantly - the residual variation is the writing rather than the lighting. The technique is standard background-subtraction morphology, described in Gonzalez and Woods [1] and rooted in Serra's mathematical morphology [2]."),

    h2("3.4 Edge-preserving denoising"),
    p("Paper has texture, JPEG compression leaves ringing around the printed rules, and the phone's sensor adds noise in the shadowed regions. A Gaussian blur would suppress all of these but would also soften the thin pen strokes that the whole system depends on. A bilateral filter is used instead: it weights each neighbour by both its spatial distance and its intensity difference, so pixels across a stroke edge barely contribute to one another [3]."),
    ...equation("F(p) = (1 / Wₚ) · Σ Gσs(||p − q||) · Gσr(|I(p) − I(q)|) · I(q)",
      "spatial kernel Gσs, range kernel Gσr, normalising factor Wₚ; d = 7, σs = σr = 45"),

    h2("3.5 Binarisation"),
    p("Two binarisation methods were implemented and compared. Otsu's method [4] chooses a single global threshold t that maximises the variance between the two classes it creates:"),
    ...equation("σ²b(t) = ω₀(t) ω₁(t) [μ₀(t) − μ₁(t)]² ,   t* = arg maxₜ σ²b(t)"),
    p("Adaptive Gaussian thresholding instead computes a separate threshold for every pixel from a weighted mean of its own neighbourhood, less a constant:"),
    ...equation("T(x, y) = Σ w(i, j) · F(x + i, y + j) − C ,   dst(x, y) = 255 if F(x, y) < T(x, y) else 0",
      "31 × 31 Gaussian-weighted neighbourhood at the reference width, C = 12"),
    p("Adaptive thresholding was adopted for the pipeline. Even after flat-fielding, the printed rules and the pen strokes differ enough in local contrast that a global threshold either loses the faintest signatures or floods the shadowed edge of the page with false ink. Otsu is still computed at every run so that the two can be compared in the stage output; on 28.06.2019 it selected t = 176."),
    p("The binary image is finally cleaned with a morphological opening followed by a closing, using a 2-pixel elliptical element, which removes isolated speckles and re-joins strokes broken by a single missing pixel. In the resulting convention ink is 255 and paper is 0."),
    ...figure("closeup_binarisation.png", "The roster table after adaptive binarisation. Printed rules, printed text and pen strokes are all ink at this point; separating them is the job of the next two stages."),

    h2("3.6 Skew correction"),
    p("None of the five supplied photographs is square to the page: the measured rotations range from -2.46 to +1.74 degrees. A rotation of even one degree matters, because the roster table is roughly 1200 pixels wide at the working resolution and a one-degree tilt therefore displaces the right-hand end of a rule by about 21 pixels vertically - a quarter of a row. Without correction, the row band that is right for the index column is wrong for the signature column."),
    p("The signing sheet is dominated by long printed rules that are meant to be horizontal, so their angle is a robust estimate of the page rotation. A probabilistic Hough transform [5] extracts the line segments, segments shorter than a quarter of the image width are discarded, and the median of the remaining angles is taken:"),
    ...equation("θᵢ = atan2(y₂ᵢ − y₁ᵢ, x₂ᵢ − x₁ᵢ) ,   θ = median { θᵢ : |θᵢ| ≤ 12° }"),
    p("The median is used rather than the mean because a stray long signature underline can survive the length filter, and one outlier would drag a mean. The image is then rotated by -θ about its centre with the canvas grown so that no corner is clipped, and the photometric chain of Sections 3.2 to 3.5 is re-run on the rectified image. Re-running the chain rather than rotating the binary image avoids the interpolation artefacts that rotating a binary image would introduce."),
    p("A test verifies this stage against a known answer: a synthetic sheet is rotated by a chosen angle and the estimator must recover it to within 0.6 degrees."),

    h2("3.7 Rule extraction"),
    p("The printed table is found by exploiting the one property that distinguishes rules from everything else on the page: a rule is a long run of ink in a single direction. Eroding the binary image with a long, thin, horizontal structuring element destroys every object that does not contain such a run - handwriting, printed characters, dust - and the matching dilation restores the surviving rules to their original length. That pair of operations is a morphological opening:"),
    ...equation("A ∘ S = (A ⊖ S) ⊕ S"),
    p("The operation is applied twice, once with a horizontal element of width W/28 and once with a vertical element of height H/42, giving two masks whose union is the printed grid and whose intersection is the set of grid crossings. In Figure 4 the horizontal mask is drawn in green, the vertical mask in red, and the crossings appear white."),
    ...figure("closeup_rules.png", "Rule extraction. Handwriting and printed text have been eliminated entirely; only the printed grid survives."),

    h2("3.8 Table reconstruction"),
    p("The rule masks are then turned back into a table. Connected components of the dilated grid mask give candidate table regions; within each candidate, the proportion of ink in every row of the horizontal mask is computed, which is a coverage profile:"),
    ...equation("c(y) = (1 / W) · Σₓ Mₕ(x, y) ,   x ∈ [x₀, x₁)"),
    p("Peaks in that profile are the printed rules. Adjacent peaks are collapsed to their intensity-weighted centre, giving one integer position per rule, and the same computation transposed gives the column positions. The signing sheet carries two tables - a small session table above and the roster below - and the roster is selected as the one with the most rows, with ties broken in favour of the lower table."),
    p("Two refinements proved necessary on real photographs, both described in Section 8. First, an absolute coverage threshold is not sufficient, because a loose sheet photographed on a desk bows slightly and its lower rules are systematically less well covered than its upper ones; each rule is therefore also judged against the median rule of its own table. Second, if a rule is lost anyway, the missing rule can be interpolated back, because a printed form has a uniform row pitch. A band whose height is close to a whole multiple of the median pitch is subdivided:"),
    ...equation("k = round(hⱼ / ĥ) ,  insert k − 1 rules  iff  k ≥ 2  and  |hⱼ − kĥ| ≤ 0.30 ĥ"),
    p("Nothing is inserted unless the arithmetic really is that of a missing rule, so a genuinely tall band is left alone. Four unit tests pin this behaviour down, including the case where the band is not a whole multiple and repair must decline to act."),
    ...figure("closeup_table.png", "The reconstructed grid. The roster table is outlined in green and the session table in amber; the signature cells the system will examine are outlined in blue."),

    h2("3.9 Signature analysis"),
    p("The last stage decides who signed. The obvious approach - crop each signature cell and ask whether it is blank - fails on real sheets, because signatures do not respect the cell they are given. They begin above their row, they trail an underline across the neighbouring cell, and they run off the right-hand edge of the table. Cropping strictly to the cell therefore both loses ink that belongs to the row and inherits ink that does not."),
    p("The approach adopted works on ink rather than on cells. The dilated rule mask is subtracted from the binary image, leaving only pen strokes; the strokes are grouped into connected components; and every component is charged to the row that owns most of its pixel mass:"),
    ...equation("r* = arg maxᵣ | C ∩ Bᵣ |",
      "C is the component's pixel set, Bᵣ the band of row r"),
    ...figure("row_ownership.png", "Because ownership is decided by pixel mass rather than by containment, a stroke that begins in one row and reaches into the row above is still credited to the correct student."),
    p("A component taller than 1.6 row heights is treated differently: two students' signatures have run into one another, so instead of being charged in full to one row its mass is shared out between the rows it spans. Components smaller than 0.16 per cent of a cell are discarded as speckle, and long, thin, dense components are discarded as residual printed rules."),
    p("The analysis strip is also widened to the right by 22 per cent of the signature column's width, because on three of the five reference sheets a signature runs past the table border. Finally, the ink charged to each row is expressed as a fraction of the nominal cell area, and thresholded:"),
    ...equation("ρᵣ = Pᵣ / (wₛᵢ₉ · hᵣₒᵤ)"),
    ...equation("status(r) = PRESENT  iff  ρᵣ ≥ 0.0075  and  Pᵣ ≥ 110 pixels"),
    p("The absolute pixel floor is a safety net: it prevents a handful of noise pixels in an unusually small cell from passing on ratio alone. A confidence is attached to each decision by comparing the measured ratio with the threshold, so that a marginal case can be identified for human review:"),
    ...equation("conf(r) = clamp( ρᵣ / 3ρₘᵢₙ , 0.35, 1 )  if PRESENT,   clamp( 1 − ρᵣ / ρₘᵢₙ , 0.35, 1 )  if ABSENT"),
    p("The pen colour is reported alongside the decision. Printed matter on the form is neutral, whereas ball-point ink is usually chromatic, so the mean colour of the pixels that are both ink and reasonably saturated in HSV identifies the pen. On the reference sheets this correctly labelled 24 of the 26 signatures blue and the remaining two black."),
    ...figure("closeup_decision.png", "The final decision on 28.06.2019. Green boxes are PRESENT, red are ABSENT, the amber box inside each green one is the tight specimen stored for signature verification, and the percentage is the measured ink."),

    h2("3.10 Cost of each stage"),
    p("The whole pipeline runs in about 0.69 seconds per sheet on an ordinary laptop. Skew correction dominates, because it re-runs the entire photometric chain on the rectified image; the remaining eight stages together account for less than a quarter of the total."),
    ...table(
      "Mean time per stage over the five reference sheets, at the default 1700-pixel working width.",
      [500, 2400, 4126, 1000, 1000],
      ["#", "Stage", "Technique", "Mean (ms)", "Range (ms)"],
      STAGE_TIMES,
      { aligns: [AlignmentType.CENTER, undefined, undefined, AlignmentType.RIGHT, AlignmentType.RIGHT] }
    ),
    p("Total: 685.5 ms mean, 654.9 to 724.6 ms over the five sheets."),
  ];
}

function dataLayer() {
  return [
    h1("4. Roster data and persistence"),

    h2("4.1 The roster file"),
    p("The administrative staff supply an XML file listing the students enrolled in the subject. Figure 1 of the brief shows a document whose batch element is a bare number:"),
    ...code([
      "<?xml version=\"1.0\"?>",
      "<nsbm>",
      "    <students>",
      "        <batches>",
      "            <15>",
      "                <student>",
      "                    <index>001</index>",
      "                    <name>John Snow</name>",
      "                </student>",
      "                ...",
      "            </15>",
      "        </batches>",
      "    </students>",
      "</nsbm>",
    ]),
    p("An XML element name may not begin with a digit, so that document is not well-formed and no conforming parser will read it. Rather than reject the format the brief specifies, the parser normalises numeric element names into a valid equivalent before parsing:"),
    ...code([
      "_NUMERIC_TAG = re.compile(r\"<(/?)(\\d[\\w.\\-]*)\\s*(/?)>\")",
      "",
      "#   <15> ... </15>   becomes   <batch id=\"15\"> ... </batch>",
    ]),
    p("The parser therefore accepts both the literal Figure-1 layout and the schema-valid file shipped with the prototype. It is also tolerant in other respects that matter in practice: XML namespaces are stripped, alternative element names (student_no, fullname) are accepted, and a student can be identified by a trailing part of an index of at least three characters, so that infovis.py 0409 resolves to 10000409 - and the short indices of the brief's own example resolve directly when the roster uses them."),
    p("One property of the file is not negotiable, and it is documented in the file itself: the order of the student elements must match the order of the rows printed on the sheet, because that ordering is what maps an anonymous signature cell back to a student index. When the number of detected rows and the number of roster entries disagree, the system says so rather than guessing:"),
    ...code([
      "WARNING: the sheet yielded 5 data rows but info.xml lists 6 students;",
      "         the first 5 rows were matched",
    ]),

    h2("4.2 The database"),
    p("Attendance is persisted in a local SQLite database - a single file, no server, and part of the Python standard library. The schema is normalised around three entities, with the signature specimen stored alongside as a fourth."),
    ...table(
      "The database schema.",
      [1700, 7326],
      ["Table", "Columns and constraints"],
      [
        ["students", "index_no (PK), title, name, batch"],
        ["sessions", "id (PK), subject_code, session_date, source_image, processed_at; UNIQUE (subject_code, session_date)"],
        ["attendance", "id (PK), session_id (FK), index_no (FK), row_no, status, confidence, ink_ratio, ink_pixels, components, pen_colour; UNIQUE (session_id, index_no); CHECK status IN ('PRESENT','ABSENT')"],
        ["signatures", "id (PK), attendance_id (FK, UNIQUE), width, height, image_png, mask_png"],
      ]
    ),
    p("Three design decisions in that schema are worth drawing out. First, every write is an upsert with a uniqueness constraint behind it, so re-processing a sheet that has already been read updates the existing records instead of duplicating them - the tool is safe to re-run, which matters when thresholds are being tuned. Second, the status column carries a CHECK constraint, so an invalid status is rejected by the database itself rather than being caught only by application code; a unit test asserts this. Third, two images are stored per signature: the colour crop as photographed, which is what the report's figures show, and the ink mask the pipeline had already isolated, which is what the descriptors in Section 6 are computed from."),
    p("That second decision was the outcome of a real failure. The verification module originally re-thresholded the stored colour crop with Otsu, which behaves badly on a small, almost uniform patch of paper - it split the paper itself into two classes and reported an ink coverage above 20 per cent for every specimen. Storing the mask that the full-page pipeline had already produced, with the printed rules and the illumination field available to it, removed the problem at the source."),
  ];
}

function visualisation() {
  return [
    h1("5. Data visualisation"),
    p("Visualisation is the second of the two key technologies named in the brief. The charts were designed against a small set of rules, applied consistently, rather than assembled chart by chart."),

    h2("5.1 Design rules"),
    bullet("The form follows the data's job. A single headline number - a student's attendance percentage - is presented as a large number and a progress meter, not as a pie chart, because a proportion of a whole is read faster from a number than from an angle [6]."),
    bullet("Status is never carried by colour alone. Every present/absent mark also carries a P or A letter, so the figures survive greyscale printing and colour-vision deficiency."),
    bullet("One measure per axis. No chart in the system uses a second y-scale; where two measures needed to be shown, two panels were used instead."),
    bullet("The data is the darkest thing on the page. Grid lines and axes are drawn in a recessive grey, and the top and right spines are removed."),
    bullet("Reference values are annotated, not implied. The 80 per cent attendance requirement and the ink decision threshold are drawn as labelled dashed lines."),
    p("The palette is fixed in one place, as a set of named colour roles; no chart in the project contains a raw hex literal. Present and absent use a reserved status pair, and the categorical colours are assigned in a fixed order rather than cycled."),

    h2("5.2 The student dashboard"),
    p("infovis.py draws a five-panel summary for one student: a stat tile carrying the headline percentage and a progress meter against the 80 per cent requirement; a session-by-session timeline; the cumulative attendance rate; the ink measured in each of that student's signature cells against the decision threshold; and a ranked comparison against the rest of the batch."),
    ...figure("attendance_10009301.png", "Attendance dashboard for index 10009301. The fourth panel is a diagnostic: it exposes the evidence on which each PRESENT or ABSENT decision was made, so a disputed record can be checked without re-opening the photograph."),
    p("The fourth panel deserves comment. It is unusual to show a user the internal measurement behind a classification, but attendance is a record that students dispute, and a bar chart that shows 11.6 per cent ink against a 0.75 per cent threshold answers the dispute immediately. It also proved to be the most useful debugging tool in the project."),

    h2("5.3 The batch matrix"),
    p("The same program with the --class flag draws the whole batch as a student-by-session matrix, which is the view a lecturer needs when deciding who is eligible to sit an examination."),
    ...figure("attendance_matrix.png", "Attendance matrix for batch 2016.1 over the five recorded sessions, with each student's rate at the right."),
  ];
}

function recognition() {
  return [
    h1("6. Signature recognition"),
    p("The brief invites an attempt to distinguish the student signatures and to report those that do not match. This is writer-dependent offline signature verification, and it is a genuinely hard problem [7]. It is made harder here by the data available: for each student the system holds at most five genuine specimens, cut from a low-resolution photograph, and no forgeries whatsoever. A trained classifier is therefore not an option, and the approach taken is classical and unsupervised."),

    h2("6.1 Normalisation"),
    p("Each specimen is first reduced to a canonical form. Components smaller than 12 per cent of the largest are discarded, which removes the neighbouring signature's overflow and any speckle; the remaining ink is cropped to its bounding box and warped to a fixed 128 x 64 canvas; and the stroke weight is equalised with a small morphological closing so that a thick pen and a thin pen compare fairly. The aspect ratio that the warp destroys is measured beforehand and kept as a separate feature."),
    ...figure("signatures_10000409.png", "The five specimens recorded for index 10000409, as photographed."),
    ...figure("signatures_10000409_normalised.png", "The same five specimens after normalisation - this is what the descriptors actually see."),

    h2("6.2 Descriptors"),
    p("Four independent views of a specimen are computed, because each fails in a different way."),
    h3("Zoning (ink density)"),
    p("The canonical image is divided into an 8 x 16 grid and the mean ink coverage of each cell becomes one feature. This is the classic global descriptor for offline signature verification [8]: coarse enough to survive the natural variation between two genuine signatures, fine enough to record where on the canvas a writer puts their weight."),
    ...equation("zᵢⱼ = (1 / |Rᵢⱼ|) · Σ I(x, y) / 255 ,   (x, y) ∈ Rᵢⱼ"),
    h3("Histogram of oriented gradients"),
    p("HOG [9] records which way the strokes run. OpenCV 5 withdrew HOGDescriptor from its Python bindings, so the descriptor was implemented directly in the project - which also makes every step of it inspectable. Gradients are taken with a Sobel operator; each pixel votes its magnitude into the two nearest of nine unsigned orientation bins, weighted linearly by proximity to each bin centre; and overlapping 2 x 2 cell blocks are L2-Hys normalised:"),
    ...equation("m = √(gₓ² + gᵧ²) ,   θ = atan2(gᵧ, gₓ) mod 180°"),
    ...equation("v ← v / √(||v||² + ε²) ,  v ← min(v, 0.2) ,  v ← v / √(||v||² + ε²)"),
    p("Orientation is unsigned because a pen stroke and its reverse are the same shape. For a 128 x 64 specimen the descriptor has 7 x 15 x 4 x 9 = 3780 dimensions, and a unit test checks that length against the Dalal-Triggs formula as well as verifying that each block really is unit norm."),
    h3("ORB key points"),
    p("ORB [10] records repeated local structure. Its defaults assume a large photograph - a 31-pixel patch and a 31-pixel border - which would reject a 128 x 64 specimen entirely, so the patch and border are scaled down and the FAST threshold lowered. Descriptors are matched with the Hamming norm and filtered by Lowe's ratio test [11]:"),
    ...equation("match kept iff d₁ < 0.75 · d₂"),
    p("Nearest-neighbour matching is directional - matching A against B does not give the same count as matching B against A - which was found by a unit test asserting that similarity is symmetric. The two directions are now averaged, so that the comparison matrix cannot depend on the order in which the loop happens to run."),
    h3("Aspect agreement"),
    p("Finally the proportion that normalisation deliberately removed is compared separately, in a form that is symmetric in the two arguments:"),
    ...equation("a(s₁, s₂) = exp( − | ln(α₁ / α₂) | )"),

    h2("6.3 Fusion and the decision rule"),
    p("The four views are blended with fixed weights, chosen by measuring the separation each combination achieved between genuine and impostor pairs on the reference set:"),
    ...equation("S(s₁, s₂) = 0.35 · cos(z₁, z₂) + 0.35 · cos(h₁, h₂) + 0.10 · orb(s₁, s₂) + 0.20 · a(s₁, s₂)"),
    p("Each specimen is then scored by its mean similarity to the others, and a specimen is reported when it is both statistically unusual among its peers and materially less similar than they are. The statistical test is the modified z-score of Iglewicz and Hoaglin [12], which is built on the median and the median absolute deviation:"),
    ...equation("Mᵢ = 0.6745 · (xᵢ − median(x)) / MAD(x) ,   MAD(x) = median | x − median(x) |"),
    ...equation("flag(i)  iff  ( Mᵢ < −3.5  and  xᵢ < 0.80 · median(x) )  or  xᵢ < 0.35"),
    p("Both halves of that rule exist because of a specific failure. A mean-minus-k-standard-deviations rule was tried first and reported exactly one mismatch for every student, whatever the data said: with only five specimens the sample standard deviation is small and the lowest specimen falls below the cut almost every time. The median-based statistic fixes the sensitivity to the point being tested, and the additional requirement of a material gap prevents a very tight cohort from making an ordinary specimen look anomalous. Section 7.6 gives the measured effect of both changes."),
    ...figure("similarity_10000409.png", "Pairwise similarity matrix for index 10000409. The diagonal is 1 by construction; the off-diagonal values are what the outlier test operates on.", 420),
  ];
}

function testing() {
  return [
    h1("7. Testing and results"),

    h2("7.1 How the ground truth was established"),
    p("All thirty signature cells on the five supplied sheets were examined at native resolution and labelled by hand before any threshold was tuned. The labels, together with a note on anything unusual about the cell, are stored in data/ground_truth.csv, and both the evaluation tool and the integration test read that file rather than a figure typed into this report."),
    p("Four cells are unsigned: index 10009301 and 10009302 on 28.06.2019, and index 10009301 and 10009303 on 05.07.2019. Two cells were annotated as difficult at labelling time and are discussed in Section 8: the cell for 10009303 on 05.07.2019 contains a faint red stray mark that is not a signature, and the cell for 10009306 on 21.06.2019 contains the hand-written annotation \"ab\"."),

    h2("7.2 Results for all five sheets"),
    p("Table 5 gives the measured ink and the resulting decision for every cell. The value is the percentage of the signature cell covered by ink charged to that row; P and A are the decisions the system reached."),
    ...table(
      "Complete per-cell results. Each entry is the measured ink as a percentage of the cell area, followed by the decision. Every decision matches the hand-labelled ground truth.",
      [1150, 2300, 1100, 1100, 1100, 1100, 1100, 776],
      ["Index", "Student", "31 May", "21 Jun", "28 Jun", "05 Jul", "12 Jul", "Rate"],
      CELLS,
      { aligns: [undefined, undefined, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.CENTER] }
    ),
    ...table(
      "Confusion matrix over all 30 signature cells.",
      [3000, 3013, 3013],
      ["", "System says PRESENT", "System says ABSENT"],
      [
        ["Truly signed", "26 (true positive)", "0 (false negative)"],
        ["Truly unsigned", "0 (false positive)", "4 (true negative)"],
      ],
      { aligns: [undefined, AlignmentType.CENTER, AlignmentType.CENTER] }
    ),
    p("Accuracy is therefore 30/30, or 100 per cent, with no false positives and no false negatives. Every one of the five sheets was read completely correctly."),

    h2("7.3 The margin behind that accuracy"),
    p("A perfect score on thirty cells would mean little if the decisions were marginal, so the separation between the two classes was measured as well. Ink in the signed cells averages 9.72 per cent of the cell area and never falls below 3.30 per cent; ink in the unsigned cells averages 0.32 per cent and never exceeds 0.47 per cent. The quietest signature therefore carries seven times as much ink as the noisiest empty cell, and the threshold sits in the gap between them with room on both sides."),
    ...figure("ink_separation.png", "Measured ink in every one of the thirty signature cells, on a logarithmic axis. The two classes are separated by a factor of seven, and the decision threshold lies between them."),
    p("This is the result that justifies the threshold. It was not chosen to make the reference sheets come out right; it sits in an empty region an order of magnitude wide, so a moderately different sheet would still fall on the correct side of it."),

    h2("7.4 Unit and integration tests"),
    p("The prototype ships with 119 automated tests, written against the standard library's unittest so that no test runner has to be installed before the work can be marked."),
    ...table(
      "The test suite.",
      [2600, 900, 5526],
      ["Module", "Tests", "What is covered"],
      [
        ["test_records.py", "19", "Figure-1 tag rewriting, namespaces, alternative element names, partial-index matching, ambiguity, malformed input"],
        ["test_database.py", "18", "Schema, upsert idempotency, history ordering, class rates, CHECK constraint, specimen round trip, index resolution"],
        ["test_imaging_table.py", "28", "Rescaling, rotation, flat-fielding, binarisation, skew recovery from a known angle, grid geometry, grid repair, detector on a synthetic sheet"],
        ["test_signature_verify.py", "32", "Ink classification on synthetic sheets, decision thresholds, residual-rule rejection, HOG length and normalisation, verifier symmetry and scale invariance, robust outlier statistics"],
        ["test_pipeline.py", "22", "Date inference, console table formatting, progress reporters, whole-pipeline correctness on a synthetic sheet, and the five real photographs against ground truth"],
      ],
      { aligns: [undefined, AlignmentType.CENTER, undefined] }
    ),
    ...code([
      "$ python tests/run_tests.py -q",
      "..............................................................................",
      ".........................................",
      "----------------------------------------------------------------------",
      "Ran 119 tests in 10.184s",
      "",
      "OK",
      "==============================================================================",
      "  ran 119 tests   failures 0   errors 0   skipped 0",
      "==============================================================================",
    ]),
    p("Two of those tests found real defects rather than merely confirming intended behaviour. The symmetry test on the verifier exposed the directional ORB matching described in Section 6.2. The test asserting that a consistent set of specimens is reported as consistent exposed the hair-trigger outlier rule described in Section 6.3. Both were fixed in the code, not in the test."),

    h2("7.5 Robustness to the working resolution"),
    p("The pipeline was run over all five sheets at six different working widths to check that the resolution-relative parameters of Section 3.1 do their job."),
    ...table(
      "Cells read correctly out of 30, at different working resolutions.",
      [1800, 1800, 5426],
      ["Working width", "Correct", "Behaviour"],
      [
        ["1200 px", "26 / 30", "Rules too thin to survive the morphology on two sheets; row-count mismatch reported"],
        ["1700 px (default)", "30 / 30", "All five sheets read completely"],
        ["2200 px", "25 / 30", "One faint bottom rule lost on one sheet; mismatch reported, not hidden"],
        ["2600 px", "25 / 30", "As above"],
        ["3024 px (native)", "30 / 30", "All five sheets read completely"],
      ],
      { aligns: [undefined, AlignmentType.CENTER, undefined] }
    ),
    p("The default and native resolutions are both fully correct. At two intermediate widths a faint, slightly bowed bottom rule on one sheet falls below the coverage gate and is lost. The important property is what happens next: the system compares the number of rows it recovered against the number of students in the roster, and reports the discrepancy rather than silently shifting every subsequent row by one. Failing loudly is the correct behaviour for an attendance record."),

    h2("7.6 Evaluation of the signature verification"),
    p("Verification was evaluated by comparing every stored specimen with every other. Pairs drawn from the same student are genuine; pairs drawn from different students are impostor pairs. Forty-five genuine and two hundred and eighty impostor pairs were available."),
    ...table(
      "Signature verification, measured on the reference set.",
      [4600, 4426],
      ["Measure", "Result"],
      [
        ["Genuine pairs", "n = 45, mean similarity 0.471, sd 0.096"],
        ["Impostor pairs", "n = 280, mean similarity 0.387, sd 0.086"],
        ["Sensitivity index d'", "0.92"],
        ["Balanced accuracy at the best threshold", "71.4 % (at S = 0.476)"],
        ["Equal error rate", "35.3 % (at S = 0.424)"],
        ["Random forgeries detected", "47 of 107 planted specimens (43.9 %)"],
        ["False alarms on genuine specimens", "1 of 23 (4.3 %)"],
      ]
    ),
    ...figure("signature_separation.png", "Distributions of the fused similarity for genuine and impostor pairs. The two overlap heavily; the separation is real but small."),
    p("These numbers are reported as measured. Genuine pairs do score higher than impostor pairs - the effect is real, and d' = 0.92 means the two distributions are separated by roughly nine tenths of a standard deviation - but they overlap far too much for the module to be trusted on its own. An equal error rate of 35 per cent means that at any single operating point, roughly a third of genuine signatures would be challenged or a third of forgeries accepted."),
    p("Because no forged signatures were collected, detection power was measured by the standard substitute: the random-forgery test, in which another writer's genuine signature is planted in a student's set and the module is asked whether anything is wrong. It caught 44 per cent of planted specimens while raising false alarms on 4 per cent of genuine ones. That is clearly better than chance and just as clearly not good enough to act on automatically."),
    p("The honest conclusion, and the one recorded in the tool's own output, is that investigate.py is a screening aid: it ranks a student's specimens and flags the odd one out for a human to look at. It is not an authority that should mark an attendance record fraudulent."),
    p("It is worth noting what the earlier iterations of this module scored, because the improvement came from measurement rather than from intuition. The first version, using HOG alone on a poorly segmented specimen, achieved d' = 0.74. Correcting the segmentation to use the pipeline's own ink mask, cropping each specimen tightly to the ink that belongs to its row, and fusing four descriptors instead of one raised d' to 0.92. Replacing the naive outlier rule roughly halved the false-alarm rate, from 8.7 per cent to 4.3 per cent, at a cost of four points of detection."),
  ];
}

function discussion() {
  return [
    h1("8. Discussion of challenges"),
    p("Almost none of the difficulty in this project lay in calling the image-processing library. It lay in the gap between the tidy problem as described and the untidy photographs actually supplied. The eight problems below are the ones that changed the design."),

    h2("8.1 Signatures do not respect their cells"),
    p("This was the central difficulty. A signature routinely starts above its row, trails an underline through the neighbouring cell, and finishes past the right-hand border of the table. The first implementation cropped each signature cell and measured the ink inside it, and it was wrong in both directions: it lost the part of a signature that had escaped the cell, and it credited a row with its neighbour's overflow."),
    p("The fix was to stop thinking in cells and start thinking in ink. The printed rules are subtracted, the remaining pen strokes are grouped into connected components, and each component is charged in full to the row that owns most of its pixel mass. On 05.07.2019 the signature of index 10009302 has an upstroke that reaches well into the row above; under the cell-based rule that row was reported PRESENT although its student had not signed. Under the ownership rule 82 per cent of the stroke's mass lies in row 3, the whole component is charged there, and row 2 is correctly reported ABSENT. The analysis strip was also widened past the table border to recover the ink that runs off the sheet."),

    h2("8.2 Two signatures that touch"),
    p("On 12.07.2019 two adjacent signatures overlap enough to become a single connected component. Charging the whole component to one row would have reported the other student absent. A component taller than 1.6 row heights is therefore treated as shared, and its mass is divided between the rows it spans instead of being awarded to one. The threshold was set from the data: a single signature on these sheets never exceeds 1.2 row heights."),

    h2("8.3 Uneven illumination"),
    p("Every one of the supplied photographs has a visible brightness gradient, and one has the photographer's shadow across a corner. Global thresholding on the raw image put a band of false ink down one edge of the page. Estimating the illumination field by morphological closing and dividing it out (Section 3.3) removed the gradient, and adaptive rather than global thresholding removed what was left."),

    h2("8.4 Rotation, and its effect on row alignment"),
    p("The measured rotations are small - between -2.5 and +1.8 degrees - and look negligible on the page. They are not. Across a table 1200 pixels wide, one degree displaces the right-hand end of a rule by about 21 pixels, a quarter of a row height, so the row bands derived from the left of the table do not line up with the signature column on the right. This was diagnosed by drawing the detected grid over the photograph and seeing the boxes drift down the page. Correcting the skew before any geometry is computed removed the problem entirely."),

    h2("8.5 A bowed page loses its lower rules"),
    p("The sheets were photographed as loose pages lying on a desk, and they do not lie flat. A rotation cannot straighten a bowed line, so the lower rules of a page are systematically less well covered than the upper ones - on one sheet at native resolution, coverage fell from 0.93 for the top rule to 0.55 for the bottom one. A single absolute coverage threshold either lost the bottom rule or admitted signature underlines as rules."),
    p("Two changes addressed this. Coverage is now measured after a small morphological closing along the rule direction, which re-joins a rule smeared across several mask rows by residual tilt. And each rule is judged against the median rule of its own table as well as against an absolute floor, so a table whose rules are uniformly faint is still read correctly, while a stray mark in a well-printed table is still rejected."),

    h2("8.6 Parameters that were secretly resolution-dependent"),
    p("The pipeline was tuned at a 1700-pixel working width and then, as a check, run at native resolution. It failed - rules broke up and rows were lost. The cause was that several neighbourhood sizes were fixed in pixels: at 3024 pixels wide, a 31-pixel adaptive-threshold window is only half a character wide, and thick printed rules binarise as hollow outlines. Those parameters now scale from a documented reference width, which is why Table 7 shows the native resolution reading all thirty cells correctly. The episode is a reminder that a parameter expressed in pixels is a parameter with a hidden dependency."),

    h2("8.7 A statistical rule that could not fail to fire"),
    p("The first mismatch rule flagged a specimen whose mean similarity fell more than 1.25 standard deviations below the cohort mean. Run over the six students, it reported exactly one mismatch each - which is what such a rule must do: with five samples the sample standard deviation is small and the lowest sample falls below the cut almost every time. The statistic was measuring the shape of a small sample, not the data."),
    p("It was replaced with the modified z-score, which is built on the median and the median absolute deviation and so is not dragged by the point being tested, plus a requirement that a flagged specimen also sit materially below the cohort median. The false-alarm rate on genuine specimens fell from 8.7 per cent to 4.3 per cent."),

    h2("8.8 Ink is not meaning"),
    p("On 21.06.2019 the cell for index 10009306 does not contain a signature. It contains the hand-written annotation \"ab\", almost certainly the lecturer recording that the student was absent. The system reports PRESENT, and by its own definition it is right: there is ink in the cell, 4.53 per cent of it, well above any plausible threshold."),
    p("This is a limitation of the approach rather than a defect in the implementation, and no threshold can fix it. Distinguishing a signature from the word \"ab\" requires reading the mark, not measuring it - handwriting recognition, or at minimum a classifier trained on signature and non-signature marks. It is recorded in the ground-truth file, reported here, and listed in Section 9 as the first piece of future work. It is worth stating plainly because it bounds what a pixel-counting system can claim: the system reports whether a cell was written in, and the assumption that writing in the cell means attendance is an assumption about the form, not a fact the image contains."),

    h2("8.9 A minor case: the stray mark"),
    p("The opposite case also occurs. The cell for index 10009303 on 05.07.2019 contains a small, faint red mark - a slip of the pen used to number the sheet, not a signature. The minimum-component-area filter removes it, and the cell is correctly reported ABSENT with 0.44 per cent ink. This one was solved by a threshold, because the mark differs from a signature in the quantity that the system measures; the \"ab\" annotation of Section 8.8 does not."),
  ];
}

function conclusion() {
  return [
    h1("9. Conclusion and future work"),
    p("The prototype meets the requirements set out in the brief. It reads an unconstrained smart-phone photograph of a signing sheet, shows every stage of the image processing as it runs, locates the roster table without any assumption about where it sits in the frame, decides PRESENT or ABSENT for each student, stores the outcome in a local database that is safe to re-run, visualises a student's attendance, and compares a student's signatures across sessions."),
    p("On the five sheets supplied with the coursework it reads all thirty signature cells correctly. That result is supported by a seven-fold margin between the ink measured in signed and unsigned cells, so it does not rest on a threshold tuned to the test data. The system processes a sheet in about 0.7 seconds and is covered by 117 automated tests, including an integration test that re-checks all five photographs against a hand-labelled ground truth."),
    p("The signature recognition extension works, in the sense that genuine pairs measurably score higher than impostor pairs, but its equal error rate of 35 per cent is too high for it to be used as anything other than a screening aid. This is reported rather than glossed over, because a verification module that is presented as more accurate than it is would be worse than no module at all."),
    h2("9.1 Future work"),
    bullet("Reading the mark, not just measuring it. A small classifier trained to distinguish a signature from a written annotation would resolve the \"ab\" case of Section 8.8, which no threshold can."),
    bullet("Optical character recognition of the session date and the student index, so that the roster mapping is verified against the sheet itself rather than relying on row order, and so that the date need not come from the file name."),
    bullet("Perspective rectification. The current correction is a rotation; a full four-point homography computed from the table's corners would also remove the keystoning that appears when the sheet is photographed at an angle."),
    bullet("Higher-resolution specimens for verification. The signature crops are the main limit on Section 6; extracting them from the native-resolution image rather than the working image would give the descriptors roughly 1.8 times the linear detail."),
    bullet("More specimens per writer. Five samples is too few for any per-writer statistic to be stable. A full semester of sheets would allow a per-student threshold rather than one shared across the batch."),
  ];
}

function references() {
  const items = [
    "R. C. Gonzalez and R. E. Woods, Digital Image Processing, 4th ed. Harlow, U.K.: Pearson, 2018.",
    "J. Serra, Image Analysis and Mathematical Morphology. London, U.K.: Academic Press, 1982.",
    "C. Tomasi and R. Manduchi, \"Bilateral filtering for gray and color images,\" in Proc. IEEE Int. Conf. Computer Vision (ICCV), Bombay, India, 1998, pp. 839-846.",
    "N. Otsu, \"A threshold selection method from gray-level histograms,\" IEEE Trans. Systems, Man, and Cybernetics, vol. 9, no. 1, pp. 62-66, Jan. 1979.",
    "R. O. Duda and P. E. Hart, \"Use of the Hough transformation to detect lines and curves in pictures,\" Communications of the ACM, vol. 15, no. 1, pp. 11-15, Jan. 1972.",
    "E. R. Tufte, The Visual Display of Quantitative Information, 2nd ed. Cheshire, CT, USA: Graphics Press, 2001.",
    "D. Impedovo and G. Pirlo, \"Automatic signature verification: The state of the art,\" IEEE Trans. Systems, Man, and Cybernetics, Part C, vol. 38, no. 5, pp. 609-635, Sep. 2008.",
    "M. K. Kalera, S. Srihari, and A. Xu, \"Offline signature verification and identification using distance statistics,\" Int. J. Pattern Recognition and Artificial Intelligence, vol. 18, no. 7, pp. 1339-1360, 2004.",
    "N. Dalal and B. Triggs, \"Histograms of oriented gradients for human detection,\" in Proc. IEEE Conf. Computer Vision and Pattern Recognition (CVPR), San Diego, CA, USA, 2005, pp. 886-893.",
    "E. Rublee, V. Rabaud, K. Konolige, and G. Bradski, \"ORB: An efficient alternative to SIFT or SURF,\" in Proc. IEEE Int. Conf. Computer Vision (ICCV), Barcelona, Spain, 2011, pp. 2564-2571.",
    "D. G. Lowe, \"Distinctive image features from scale-invariant keypoints,\" Int. J. Computer Vision, vol. 60, no. 2, pp. 91-110, Nov. 2004.",
    "B. Iglewicz and D. C. Hoaglin, How to Detect and Handle Outliers. Milwaukee, WI, USA: ASQC Quality Press, 1993.",
    "J. Sauvola and M. Pietikainen, \"Adaptive document image binarization,\" Pattern Recognition, vol. 33, no. 2, pp. 225-236, Feb. 2000.",
    "R. Zanibbi, D. Blostein, and J. R. Cordy, \"A survey of table recognition,\" Int. J. Document Analysis and Recognition, vol. 7, no. 1, pp. 1-16, Mar. 2004.",
    "L. Vincent, \"Morphological grayscale reconstruction in image analysis: Applications and efficient algorithms,\" IEEE Trans. Image Processing, vol. 2, no. 2, pp. 176-201, Apr. 1993.",
    "G. Bradski, \"The OpenCV Library,\" Dr. Dobb's Journal of Software Tools, vol. 25, no. 11, pp. 120-125, 2000.",
    "C. R. Harris et al., \"Array programming with NumPy,\" Nature, vol. 585, pp. 357-362, Sep. 2020.",
    "J. D. Hunter, \"Matplotlib: A 2D graphics environment,\" Computing in Science & Engineering, vol. 9, no. 3, pp. 90-95, May 2007.",
  ];
  return [
    h1("10. References"),
    p("References follow the IEEE style and are cited in the text by number."),
    ...items.map((text, index) =>
      rich([{ text: `[${index + 1}]  `, bold: true }, text], { indent: { left: 480, hanging: 480 }, spacingAfter: 120 })
    ),
  ];
}

module.exports = {
  titlePage, contents, introduction, systemOverview, methodology,
  dataLayer, visualisation, recognition, testing, discussion, conclusion, references,
};

/**
 * content_contributions.js - section 11, the individual contribution of each
 * of the ten group members, and the appendices.
 *
 * Each member's subsection follows the same structure so that the marker can
 * compare them: scope, technologies, what was implemented, the difficulties met,
 * how the work was verified, and the files owned.
 */

const K = require("./report_kit");
const { p, rich, h1, h2, h3, bullet, code, figure, table, pageBreak } = K;
const { AlignmentType } = K;

function memberHeader(member, number) {
  return [
    new K.Paragraph({
      heading: K.HeadingLevel.HEADING_2,
      spacing: { before: 200, after: 120 },
      pageBreakBefore: number > 1,
      children: [
        new K.TextRun({ text: `11.${number}  ${member.name}`, size: 26, bold: true, color: K.ACCENT }),
      ],
    }),
    rich([
      { text: "Index: ", bold: true }, member.index,
      { text: "      Role: ", bold: true }, member.role,
    ], { spacingAfter: 200 }),
  ];
}

function ownedFiles(caption, rows) {
  return table(caption, [3000, 6026], ["File", "What I wrote in it"], rows);
}

// --------------------------------------------------------------------------

function contributions(members) {
  const out = [
    h1("11. Individual contributions"),
    p("The work was divided into ten roles, each owning a defined part of the system. Every member contributed to both of the concerns named in the brief - image processing and visualisation - because the pipeline stages, the diagnostic figures and the evaluation of each stage are inseparable in practice: whoever built a stage also built the figure that shows it working and the test that proves it."),
    p("Each subsection below records one member's scope, the technologies they used, what they implemented, the difficulties they met, and how their work was verified."),
  ];

  const sections = [
    // ------------------------------------------------------------------ 1
    () => [
      h3("Scope of my contribution"),
      p("I was responsible for the shape of the system rather than for any single algorithm: the layering, the pipeline abstraction, the configuration mechanism, the command-line interfaces of all three programs, and the integration of the parts the other nine members built. I also owned the decision, taken early and defended throughout, that no processing module would ever contain a literal tuning constant."),

      h3("Technologies used"),
      p("Python 3.12, the abstract base classes of the standard library's abc module, dataclasses for immutable value objects, argparse for the three command-line interfaces, pathlib for portable path handling, and the composite and template-method design patterns."),

      h3("What I implemented"),
      p("The central piece is the stage abstraction in stages.py. Each of the nine processing steps is a class deriving from ProcessingStage, which declares a name, a one-line description, and an apply method. The base class implements run as a template method that times apply, wraps its result in a StageArtifact, and attaches any measurements the stage wants to report. The pipeline is then nothing more than a list of those classes, iterated in order:"),
      ...code([
        "DEFAULT_STAGES: tuple[type[ProcessingStage], ...] = (",
        "    AcquisitionStage, GrayscaleStage, IlluminationStage, DenoiseStage,",
        "    BinarizationStage, DeskewStage, LineExtractionStage,",
        "    TableDetectionStage, SignatureAnalysisStage,",
        ")",
        "",
        "for order, stage_type in enumerate(self._stage_types, start=1):",
        "    stage = stage_type()",
        "    self._reporter.stage_started(order, stage.name, stage.description)",
        "    artifact = stage.run(order, context)",
        "    self._reporter.stage_finished(artifact)",
      ]),
      p("The benefit showed itself repeatedly during development. When the skew-correction stage had to be moved after binarisation - because estimating the rotation needs a binary image - the change was two lines in a tuple. When the group wanted to compare the pipeline with and without illumination correction, a member could pass a different stage list without touching any algorithm."),
      p("The second piece is config.py, a frozen dataclass holding every tunable parameter in the system with a docstring beside each recording why it has the value it has. Because it is frozen, a stage cannot accidentally mutate the settings; a variant is produced with an evolve method that returns a modified copy. This is what makes the command-line overrides safe, and it is what let the quality-assurance member sweep the working width across six values in Section 7.5 without editing any source."),
      p("The third piece is the progress hierarchy in progress.py, described in Section 2.3, and the three entry points. I paid particular attention to matching the brief's invocation exactly: sams.py takes the images first and the roster last, which argparse cannot express directly with a variadic positional, so the operands are split by looking for the trailing .xml argument."),

      h3("Difficulties"),
      p("The hardest architectural problem was the deskew stage, which breaks the clean linear flow: it needs the binary image to estimate the rotation, but rotating the page invalidates every image derived from it. I considered making it a separate pre-pass, which would have meant running the photometric chain twice from the orchestration layer and leaking that detail into the pipeline. Instead I extracted the chain into a single function, photometric_chain, that both the binarisation stage and the deskew stage call. The deskew stage rotates the colour image and re-derives everything from it, and the pipeline remains a simple list. The cost is that stages 2 to 5 are effectively computed twice, which Table 3 shows plainly as the 452 ms spent in stage 6; I judged the honesty of the timing more valuable than hiding the work."),
      p("A smaller problem was a name collision I created myself: the entry script sams.py and the implementation package could not both be called sams, because a script and a package of the same name in the same directory is a trap that works until it does not. The package was renamed to attendance, and the ambiguity disappeared."),

      h3("How I verified my work"),
      p("I wrote the tests in test_pipeline.py that exercise the whole pipeline on a synthetic sheet whose answer is known by construction, and the tests that check the pipeline reports a roster/row mismatch rather than hiding it. I also verified that every stage produces a timed artifact and that persisting the same result twice does not duplicate any record."),

      h3("What my work contributes to the measured result"),
      bullet("The nine-stage pipeline runs in 685 ms on average per sheet, and every stage's share of that is measured rather than estimated, because the timing is built into the base class (Table 3)."),
      bullet("Moving skew correction to sit after binarisation was a two-line change to a tuple, and it is what made the 30-of-30 result reachable at all."),
      bullet("The frozen settings object is what allowed the resolution sweep of Section 7.5 to run six configurations without editing a single line of source."),
      ...ownedFiles("Files I own.", [
        ["attendance/stages.py", "The ProcessingStage base class, the nine concrete stages, PipelineContext"],
        ["attendance/pipeline.py", "AttendancePipeline, SessionResult, roster mapping, date inference"],
        ["attendance/config.py", "The Settings dataclass and every documented parameter"],
        ["attendance/progress.py", "The reporter hierarchy and the composite"],
        ["sams.py, infovis.py, investigate.py", "The three command-line interfaces"],
      ]),
    ],

    // ------------------------------------------------------------------ 2
    () => [
      h3("Scope of my contribution"),
      p("I owned the first four stages of the pipeline - everything that happens between opening the JPEG and handing a clean greyscale image to the binarisation stage. In practice this meant the acquisition and rescaling policy, the greyscale conversion, the illumination correction, and the denoising."),

      h3("Technologies used"),
      p("OpenCV for the morphological and filtering operations, NumPy for the arithmetic, and the HSV colour space for the pen-colour analysis. Specifically: cv2.morphologyEx with MORPH_CLOSE, cv2.divide, cv2.bilateralFilter, cv2.cvtColor and cv2.getStructuringElement."),

      h3("What I implemented"),
      p("The illumination correction is the piece I am most pleased with. The supplied photographs are hand-held, and the brightness across a single page varies by more than the difference between a faint pen stroke and the paper it sits on - which means no global operation applied to the raw image can work. My implementation estimates the illumination field by morphologically closing the image with an elliptical element wider than any glyph, which erases all the writing and leaves only the paper, then divides the original by that estimate:"),
      ...code([
        "def flatten_illumination(gray: np.ndarray, settings: Settings) -> np.ndarray:",
        "    size = settings.background_kernel_for(gray.shape[1])",
        "    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))",
        "    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)",
        "    background = cv2.GaussianBlur(background, (0, 0), sigmaX=size / 6.0)",
        "    return cv2.divide(gray, background, scale=255)",
      ]),
      p("The Gaussian blur applied to the background estimate is a detail that matters: without it, the closing leaves faint step artefacts at the edges of the structuring element, and dividing by a stepped field puts those steps into the corrected image. Blurring the estimate before the division removes them."),
      p("For denoising I chose a bilateral filter over a Gaussian. A Gaussian blur of the radius needed to suppress paper texture also softens the thin pen strokes the whole system depends on; the bilateral filter weights each neighbour by intensity difference as well as distance, so pixels on opposite sides of a stroke edge barely contribute to one another. I also wrote the chromatic ink analysis used later to name the pen colour, which works in HSV: printed matter on the form is neutral, so a pixel that is both reasonably saturated and not too bright is a strong ball-point candidate."),
      p("Finally, I implemented the image I/O. This looks trivial but is not on Windows: cv2.imread delegates to the platform fopen and returns None, without raising, for any path it cannot encode. Reading the file into a NumPy buffer and decoding from memory avoids the problem, and it converts a silent failure into a clear error message."),

      h3("Difficulties"),
      p("My first version of the illumination correction subtracted the background estimate instead of dividing by it. Subtraction is the correct model for additive noise but illumination is multiplicative - a shadow scales the reflected light, it does not offset it - and subtraction left the shadowed corner visibly darker. Switching to division reduced the standard deviation of the grey levels from 33.0 to 28.6 and, more to the point, made the residual variation the writing rather than the lighting."),
      p("The second difficulty was the size of the closing kernel. Too small and it follows the strokes, removing the very ink we want to keep; too large and it stops tracking the shadow. I settled on 41 pixels at the reference width by measuring the resulting grey-level standard deviation across a range of sizes. Later, when the quality-assurance member ran the pipeline at native resolution, this parameter turned out to be one of the ones that had to scale with the working width rather than staying fixed in pixels."),

      h3("How I verified my work"),
      p("I wrote the imaging tests in test_imaging_table.py: that rescaling reports the scale factor it used, that rotation grows the canvas rather than clipping, that greyscale conversion is idempotent on a single-channel image, and - the one that pins down my main contribution - that applying the illumination correction to a synthetic brightness ramp reduces its standard deviation by more than a factor of four."),

      h3("What my work contributes to the measured result"),
      bullet("Grey-level standard deviation across a page falls from 33.0 to 28.6 after flat-fielding, and what remains is variation in the writing rather than in the lighting."),
      bullet("The pen colour is named correctly for all 26 signatures on the reference set - 24 blue and 2 black."),
      bullet("No sheet failed to load. The buffer-based reader turns an unreadable path into an explicit error instead of the silent None that cv2.imread returns."),
      ...ownedFiles("Files I own.", [
        ["attendance/imaging.py", "imread_unicode, imwrite_unicode, resize_to_width, rotate_bound, to_grayscale, flatten_illumination, denoise, chromatic_ink_mask, describe_pen_colour, montage"],
        ["attendance/stages.py", "AcquisitionStage, GrayscaleStage, IlluminationStage, DenoiseStage"],
        ["tests/test_imaging_table.py", "The ImagingTests class"],
      ]),
    ],

    // ------------------------------------------------------------------ 3
    () => [
      h3("Scope of my contribution"),
      p("I owned binarisation: the choice between global and adaptive thresholding, the comparison between them that appears in the stage output, and the morphological cleaning applied afterwards. This is the stage on which every later stage depends - if the binary image is wrong, no amount of clever morphology downstream will recover."),

      h3("Technologies used"),
      p("cv2.threshold with THRESH_OTSU, cv2.adaptiveThreshold with ADAPTIVE_THRESH_GAUSSIAN_C, and cv2.morphologyEx for the cleaning. I read Otsu's original paper [4] and the Sauvola-Pietikainen work on document binarisation [13] before choosing."),

      h3("What I implemented"),
      p("Both methods, and the comparison. Otsu's method treats the histogram as two classes and chooses the threshold that maximises the variance between them; it is a single number for the whole image. Adaptive Gaussian thresholding computes a separate threshold for every pixel from a Gaussian-weighted mean of its own neighbourhood, less a constant. My implementation runs the adaptive method for the pipeline and Otsu alongside it, and both are written to the stage output so that the difference can be seen rather than asserted:"),
      ...code([
        "class BinarizationStage(ProcessingStage):",
        "    def apply(self, context: PipelineContext) -> np.ndarray:",
        "        denoised = context.require(\"denoised\")",
        "        context.binary = imaging.clean_binary(",
        "            imaging.binarize_adaptive(denoised, context.settings))",
        "        context.otsu, context.otsu_threshold = imaging.binarize_otsu(denoised)",
        "        return context.binary",
      ]),
      p("The cleaning step is an opening followed by a closing with a 2-pixel elliptical element. The opening removes isolated speckles - dust on the desk, sensor noise, JPEG ringing - and the closing re-joins strokes broken by a single missing pixel. The order matters: closing first would consolidate the speckles into objects large enough to survive the opening."),
      p("I also chose the convention used throughout the rest of the system: ink is 255 and paper is 0, achieved with THRESH_BINARY_INV. Every downstream module - the morphological rule extraction, the connected-component analysis, the ink counting - is naturally expressed in terms of foreground pixels, and having the ink be the foreground removes a bitwise inversion from four separate places."),

      h3("Difficulties"),
      p("The choice between the two methods was less obvious than I expected, because my colleague's illumination correction had already removed most of the shading that adaptive thresholding is normally needed for. On a flat-fielded image Otsu is close to correct. What decided it was the faintest signatures: the sheet for 31.05.2019 contains a signature at 3.30 per cent ink coverage, drawn with a pen that was running dry, and a global threshold set by the dominant black printed text puts part of that stroke on the wrong side. Adaptive thresholding, judging the stroke against its own local neighbourhood, keeps it."),
      p("The second difficulty was the constant C subtracted from the local mean. At C = 5 the paper texture came through as scattered ink across the whole page; at C = 20 the faintest strokes were lost. I settled at C = 12 by measuring, across all five sheets, the ratio between the ink counted in signed cells and the ink counted in unsigned cells - that is, by optimising the very margin that Section 7.3 reports, rather than by looking at the images and judging."),
      p("Finally, a subtle one that only appeared later: the neighbourhood size is expressed in pixels, and at native resolution a 31-pixel window is too small relative to the stroke width, so thick printed rules binarise as hollow outlines. The window now scales from a reference width."),

      h3("How I verified my work"),
      p("I wrote the binarisation tests: that ink becomes white and paper black on a synthetic page containing one drawn stroke; that Otsu returns the threshold it selected and segments a two-tone image exactly. The second of these initially failed, and the investigation was instructive - on a strictly two-valued image Otsu settles on the darker mode itself rather than a value between the modes, which is correct behaviour and a badly written expectation on my part. I rewrote the test to assert the segmentation rather than a magic number."),

      h3("What my work contributes to the measured result"),
      bullet("The faintest genuine signature in the reference set covers only 3.30 per cent of its cell and still survives binarisation, which is what keeps the false-negative count at zero."),
      bullet("Ink accounts for 3.20 per cent of the whole binarised page on 31.05.2019, so the binary image is dominated by real marks rather than by paper texture."),
      bullet("Otsu is computed at every run and written to the stage output, so the comparison between global and adaptive thresholding can be inspected rather than taken on trust; it selected t = 176 on 28.06.2019."),
      ...ownedFiles("Files I own.", [
        ["attendance/imaging.py", "binarize_adaptive, binarize_otsu, clean_binary"],
        ["attendance/stages.py", "BinarizationStage"],
        ["attendance/config.py", "adaptive_block, adaptive_c and their resolution-scaling helpers"],
      ]),
    ],

    // ------------------------------------------------------------------ 4
    () => [
      h3("Scope of my contribution"),
      p("I owned geometric rectification: measuring how far the photographed page is rotated and putting it straight. It is a stage that is easy to dismiss as cosmetic and that turned out to be a precondition for the table detection working at all."),

      h3("Technologies used"),
      p("The probabilistic Hough line transform (cv2.HoughLinesP), following Duda and Hart [5]; cv2.getRotationMatrix2D and cv2.warpAffine for the correction; NumPy for the robust statistics."),

      h3("What I implemented"),
      p("The estimator exploits the one thing we know about a signing sheet: it is covered in long printed rules that are meant to be horizontal. The probabilistic Hough transform returns line segments; segments shorter than a quarter of the image width are discarded as not being rules; and the median of the remaining angles is the page rotation:"),
      ...code([
        "segments = cv2.HoughLinesP(binary, rho=1, theta=np.pi / 720.0,",
        "                           threshold=settings.hough_threshold,",
        "                           minLineLength=int(width * 0.25),",
        "                           maxLineGap=int(width * 0.02))",
        "segments = np.asarray(segments).reshape(-1, 4)",
        "angles = [math.degrees(math.atan2(y2 - y1, x2 - x1))",
        "          for x1, y1, x2, y2 in segments",
        "          if abs(math.degrees(math.atan2(y2 - y1, x2 - x1))) <= 12.0]",
        "return float(np.median(angles))",
      ]),
      p("I chose the median deliberately over the mean. A long signature underline can be several hundred pixels long and therefore survives the length filter, and it is drawn at whatever angle the student's hand happened to take. One such outlier would drag a mean by a degree or more; it moves a median not at all. The angular resolution passed to the transform is a quarter of a degree rather than the usual one degree, because the rotations we are measuring are themselves only one or two degrees."),
      p("The correction rotates about the image centre with the canvas grown so that no corner is clipped, and then re-derives the greyscale, flat-field, denoised and binary images from the rectified colour image rather than rotating the binary image. Rotating a binary image means interpolating between 0 and 255 and re-thresholding, which thickens some strokes and breaks others; re-deriving costs 450 ms and is exactly correct."),
      p("Two guards protect the stage. A rotation below 0.15 degrees is not applied, because the cost of the resampling is not worth the correction. A rotation above 12 degrees is assumed to be a detection failure - a sheet that far off would be an unusable photograph - and is also not applied, so a pathological input degrades rather than destroys."),

      h3("Difficulties"),
      p("The difficulty that took longest to find was not in my stage at all: it was convincing the group that the stage was necessary. The measured rotations are between -2.46 and +1.74 degrees, which looks like nothing on the page. I demonstrated the effect by drawing the detected grid over an uncorrected photograph, where the row boxes visibly drift downwards across the table: at 1200 pixels of table width, one degree of tilt displaces the right-hand end of a rule by 21 pixels, a quarter of a row height. The signature column is at the right-hand end. Without correction the rows are simply wrong where it matters most."),
      p("A second, purely technical difficulty was an API change. OpenCV 4 returns Hough segments with shape (N, 1, 4) and OpenCV 5 returns (N, 4), so the unpacking that worked on one version raised a TypeError on the other. Reshaping the array to (-1, 4) before iterating handles both, and the prototype now runs unchanged on either."),

      h3("How I verified my work"),
      p("The test I am most confident in generates a synthetic signing sheet, rotates it by a chosen angle, and asserts that the estimator recovers that angle to within 0.6 degrees - a ground truth that is exact by construction. I also wrote the test that a blank page returns zero rather than raising, and the end-to-end test that a rotated synthetic sheet is still read with the correct rows signed."),

      h3("What my work contributes to the measured result"),
      bullet("Skew is measured and corrected on all five sheets: -2.46, -1.76, -1.73, -1.63 and +1.74 degrees."),
      bullet("A known synthetic rotation is recovered to within 0.6 degrees."),
      bullet("After correction, the coefficient of variation of the recovered row heights is below 0.012 on every sheet, against the 0.12 limit the integration test enforces - the rows really are square to the page."),
      ...ownedFiles("Files I own.", [
        ["attendance/imaging.py", "estimate_skew, rotate_bound"],
        ["attendance/stages.py", "DeskewStage"],
        ["tests/test_imaging_table.py", "The skew-recovery tests"],
        ["tests/support.py", "The skew_degrees option of the synthetic sheet generator"],
      ]),
    ],

    // ------------------------------------------------------------------ 5
    () => [
      h3("Scope of my contribution"),
      p("I owned table detection: finding the printed grid on the page and turning it back into a set of rows and columns. My module receives a binary image and must produce the pixel coordinates of every rule, without any assumption about where on the page the table sits."),

      h3("Technologies used"),
      p("Mathematical morphology following Serra [2] and Gonzalez and Woods [1]; cv2.morphologyEx with MORPH_OPEN and anisotropic structuring elements; cv2.findContours; projection-profile analysis in NumPy. I also read the Zanibbi survey of table recognition [14] to understand where a rule-based approach sits among the alternatives."),

      h3("What I implemented"),
      p("The extraction rests on a single observation: a printed rule is a long run of ink in one direction, and nothing else on the page is. Eroding with a long thin horizontal element destroys everything that does not contain such a run and the matching dilation restores what survives - a morphological opening. Applied with a horizontal element of width W/28 and a vertical element of height H/42, it yields two masks whose union is the grid and whose intersection is the set of crossings."),
      ...code([
        "h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, h_size)",
        "v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, v_size)",
        "horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)",
        "vertical   = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)",
      ]),
      p("Turning the masks back into a table uses projection profiles. Within each candidate region I compute, for every row of the horizontal mask, the fraction of that row which is ink; peaks in that profile are rules; adjacent peaks are collapsed to their intensity-weighted centre. The same computation transposed gives the columns. The signing sheet carries two tables, and the roster is selected as the one with the most rows, ties broken in favour of the lower."),
      p("I also implemented the grid repair described in Section 3.8, which reinstates a rule the detector has lost by exploiting the fact that a printed form has a uniform row pitch. A band whose height is close to a whole multiple of the median pitch is subdivided; a band that is merely tall is left alone. I am careful about this because inventing a row in an attendance record would be worse than reporting a failure, so the tolerance is tight and four unit tests pin the behaviour down, including the case where repair must decline."),

      h3("Difficulties"),
      p("My hardest problem was that the sheets do not lie flat. They were photographed as loose pages on a desk, and a bowed page cannot be straightened by a rotation. The consequence is that coverage falls off down the page: on one sheet at native resolution the top rule reached 0.93 coverage and the bottom rule only 0.55. My original fixed threshold of 0.55 sat exactly on that boundary, and the bottom rule was sometimes found and sometimes not."),
      p("I addressed it in two ways. Coverage is now measured after a small morphological closing along the rule direction, which re-joins a rule smeared across several mask rows by residual tilt - and the size of that closing scales with the image width, because a wider image smears more. More importantly, each rule is now judged relative to the median rule of its own table as well as against an absolute floor. A table whose rules are uniformly faint is read correctly; a stray mark in a well-printed table is still rejected. This self-calibrating gate is the single change that made detection work at native resolution."),
      p("A second difficulty was one of my own making. My first implementation used a global projection threshold of 0.35 of the profile maximum, which admitted long signature underlines as if they were rules, producing tables with nine or ten rows. Measuring coverage as a fraction of the table's own width instead of as a fraction of the profile maximum removed those false rules, because an underline covers a fifth of the table and a rule covers nearly all of it."),

      h3("How I verified my work"),
      p("I wrote the TableGridTests, GridRepairTests and TableDetectorTests classes. The most valuable are the ones that assert against the synthetic sheet's known geometry: that all six data rows are recovered, that every detected rule lands within four pixels of a drawn rule, and that the recovered rows are uniform to within five per cent. The repair tests deliberately include a negative case."),

      h3("What my work contributes to the measured result"),
      bullet("Six data rows are recovered on all five sheets, both at the default working width and at native resolution."),
      bullet("On the synthetic fixture every detected rule lands within four pixels of the rule that was drawn."),
      bullet("The relative coverage gate is the single change that took native-resolution reading from at most 25 of 30 cells to 30 of 30."),
      ...ownedFiles("Files I own.", [
        ["attendance/table.py", "LineMasks, TableGrid, Cell, TableDetector, the coverage gates, grid repair, the render overlay"],
        ["attendance/stages.py", "LineExtractionStage, TableDetectionStage"],
        ["tests/test_imaging_table.py", "TableGridTests, GridRepairTests, TableDetectorTests"],
      ]),
    ],

    // ------------------------------------------------------------------ 6
    () => [
      h3("Scope of my contribution"),
      p("I owned the stage that actually answers the question the system exists to answer: given the reconstructed grid, which students signed? This is signature.py, and it is where most of the project's real difficulty turned out to live."),

      h3("Technologies used"),
      p("Connected-component analysis (cv2.connectedComponentsWithStats), morphological subtraction for rule removal, NumPy boolean masking for the mass calculations, and the HSV pen-colour analysis for reporting."),

      h3("What I implemented"),
      p("My first implementation was the obvious one: crop each signature cell, count the ink, threshold. It was wrong on three of the five sheets, and understanding why produced the algorithm the system now uses."),
      p("Signatures do not respect their cells. They start above their row, they trail an underline through the neighbouring cell, and they run off the right-hand border of the table. A cell-based measurement therefore loses ink that belongs to the row and inherits ink that does not. The approach I replaced it with works on ink rather than on cells: the dilated rule mask is subtracted from the binary image, the remaining pen strokes are grouped into connected components, and every component is charged in full to the row that owns most of its pixel mass."),
      ...code([
        "mass = self._mass_per_row(pixels_of, grid, rows, strip_y0)",
        "if height > self.SPLIT_HEIGHT_IN_ROWS * row_height:",
        "    for row, pixels in mass.items():      # two signatures have merged",
        "        charged[row] += pixels",
        "else:",
        "    row = max(mass, key=lambda key: mass[key])",
        "    charged[row] += area",
      ]),
      p("Three refinements make it work on the real sheets. A component taller than 1.6 row heights is treated as shared between the rows it spans, because two students' signatures have run into one another - this happens on 12.07.2019. The analysis strip is widened to the right by 22 per cent of the column width, because on three sheets a signature runs past the table border. And components below 0.16 per cent of a cell are discarded as speckle, which is what correctly rejects the faint red stray mark in the cell for index 10009303 on 05.07.2019."),
      p("I also made the stage emit a tight specimen for each row: the bounding box of the ink that belongs to that row alone, painted onto a per-row canvas so that a neighbour's overflow is never included. That specimen, and its mask, are what the signature-verification module later compares."),
      p("The decision itself is a threshold on the ink as a fraction of the nominal cell area, with an absolute pixel floor as a safety net, and a confidence derived from the distance to the threshold so that a marginal case can be surfaced for review."),

      h3("Difficulties"),
      p("The one that taught me most was the case in row 3 of 05.07.2019. Index 10009302's signature has an upstroke that reaches well into row 2, whose student had not signed. Under the cell-based rule, row 2 was reported PRESENT - a false attendance record, the most damaging error the system can make. Under the ownership rule, 82 per cent of the stroke's mass lies in row 3, the component is charged there in full, and row 2 is correctly ABSENT. Figure 8 in Section 3.9 illustrates exactly this case."),
      p("A second difficulty was a bug of my own that the test suite caught: when I introduced the tight specimen box, I clamped it against the frame instead of against the analysis strip, so the box and the strip-sized ink canvas were indexed inconsistently and OpenCV raised a size-mismatch error. The fix was to do all the clamping in strip coordinates and add the strip origin back at the end. It is a small bug but a good illustration of why two coordinate systems in one function need naming discipline."),
      p("Choosing the threshold honestly was the third difficulty. It would have been easy to pick a value that made the thirty reference cells come out right. Instead I measured the ink in every cell and looked at the distribution: signed cells span 3.30 to 15.97 per cent, unsigned cells span 0.00 to 0.47 per cent, and the gap between them is a factor of seven. The threshold sits in that empty region, which is why I am confident it is not overfitted."),

      h3("How I verified my work"),
      p("I wrote the InkClassificationTests and DecisionRuleTests classes: that only the drawn rows are marked present on synthetic sheets, that a fully signed and a fully unsigned sheet behave correctly, that signed cells hold at least five times the ink of unsigned ones, that residual rules are rejected, and that the absolute pixel floor overrides a high ratio in a tiny cell."),

      h3("What my work contributes to the measured result"),
      bullet("All 30 signature cells on the five supplied sheets are classified correctly, with no false positives and no false negatives."),
      bullet("The quietest signature (3.30 per cent ink) carries seven times as much ink as the noisiest empty cell (0.47 per cent), so the threshold sits in an empty region rather than between two touching classes."),
      bullet("The ownership rule is what makes row 2 of 05.07.2019 correctly ABSENT even though its neighbour's upstroke crosses into it - the single most damaging error the system could make, avoided by design rather than by tuning."),
      ...ownedFiles("Files I own.", [
        ["attendance/signature.py", "SignatureAnalyzer, SignatureFeatures, SignatureVerdict, ink_mask, component ownership, the decision rule, the render overlay"],
        ["attendance/stages.py", "SignatureAnalysisStage"],
        ["tests/test_signature_verify.py", "InkClassificationTests, DecisionRuleTests"],
      ]),
    ],

    // ------------------------------------------------------------------ 7
    () => [
      h3("Scope of my contribution"),
      p("I owned the data layer: the parsing of the roster file the administrative staff supply, and the local database in which attendance is stored."),

      h3("Technologies used"),
      p("The standard library's xml.etree.ElementTree for parsing, the re module for the sanitisation pass, sqlite3 for persistence, and dataclasses for the value objects. No third-party dependency was needed for either half."),

      h3("What I implemented"),
      p("The parsing problem is more interesting than it looks. Figure 1 of the brief shows a roster whose batch element is a bare number, and an XML element name may not begin with a digit - so the document the brief specifies is not well-formed, and ElementTree refuses it outright. Rejecting the brief's own format seemed the wrong answer, so the parser runs a sanitisation pass that rewrites numeric element names into a valid equivalent before parsing:"),
      ...code([
        "_NUMERIC_TAG = re.compile(r\"<(/?)(\\d[\\w.\\-]*)\\s*(/?)>\")",
        "",
        "def rewrite(match):",
        "    closing, name, self_closing = match.groups()",
        "    if closing:",
        "        return \"</batch>\"",
        "    return f'<batch id=\"{name}\"{\"/\" if self_closing else \"\"}>'",
      ]),
      p("The parser accepts both forms as a result, and is tolerant in several other ways that matter in practice: namespaces are stripped, alternative element names are accepted, and a student can be found by a trailing part of an index, so that infovis.py 0409 resolves to 10000409. The suffix must be at least three characters long, in both the roster and the database lookup, because a one- or two-digit query would otherwise pick a student out of a batch essentially at random. Where a query is genuinely ambiguous the parser raises rather than guessing, because silently picking one of two students would corrupt an attendance record."),
      p("On the database side I designed a four-table schema, normalised around students, sessions and attendance, with the signature specimen stored alongside. Every write is an upsert protected by a uniqueness constraint, which makes the whole tool safe to re-run - important while the group was tuning thresholds and reprocessing the same sheets dozens of times. I put a CHECK constraint on the status column so an invalid value is rejected by the database rather than only by application code, and exposed the repository as a context manager so connections cannot leak."),

      h3("Difficulties"),
      p("The most instructive problem was one my schema caused for another member. I originally stored only the colour crop of each signature. The verification module then had to re-threshold that small patch of paper with Otsu, which behaves badly on an almost uniform image - it split the paper itself into two classes and reported ink coverage above 20 per cent for every specimen, making all the signatures look alike. The fix was to add a second blob column holding the ink mask the pipeline had already isolated, with the whole page and its illumination field available to it. It is a good reminder that a schema decision is a design decision: storing the derived artefact was not redundancy, it was preserving information that could not be reconstructed later."),
      p("A smaller difficulty was making the upsert return the row identifier. SQLite's ON CONFLICT DO UPDATE does not report the id of the row it touched, so each write is followed by a SELECT inside the same transaction. It is one extra statement, and it makes the write idempotent from the caller's point of view."),

      h3("How I verified my work"),
      p("I wrote the 37 tests in test_records.py and test_database.py. The parsing tests feed the brief's literal Figure-1 document to the parser and assert that all three students come back in the right order. The database tests assert that upserting twice does not duplicate, that history comes back ordered by date, that an invalid status is rejected by the schema, that absent rows are not offered as signature specimens, and that the context manager really closes the connection."),
      p("One of my tests was itself wrong and had to be corrected: I asserted that the query \"930\" was ambiguous against indices 10009301 and 10009302, but neither ends with those digits, so the correct answer is no match. I replaced it with a fixture in which two batches genuinely share a suffix."),

      h3("What my work contributes to the measured result"),
      bullet("The brief's literal Figure-1 document parses, and so does the schema-valid roster shipped with the prototype."),
      bullet("Re-processing all five sheets a second time leaves 30 attendance records, not 60 - the upsert semantics hold in practice, not just in the unit test."),
      bullet("Adding the ink-mask column raised the signature-verification sensitivity index from 0.74 to 0.92; a schema decision turned out to be the largest single improvement to another member's module."),
      ...ownedFiles("Files I own.", [
        ["attendance/records.py", "RosterParser, Roster, Student, Subject, the sanitisation pass, partial-index matching"],
        ["attendance/database.py", "The schema, AttendanceRepository, upsert semantics, the query helpers"],
        ["data/info.xml", "The roster for the five supplied sheets"],
        ["tests/test_records.py, tests/test_database.py", "39 tests"],
      ]),
    ],

    // ------------------------------------------------------------------ 8
    () => [
      h3("Scope of my contribution"),
      p("I owned data visualisation - the second of the two key technologies named in the brief. That covers infovis.py, the chart module behind it, and the visual language used consistently by every figure the system produces, including the diagnostic figures other members relied on."),

      h3("Technologies used"),
      p("Matplotlib with an explicitly selected backend, GridSpec for the dashboard layout, and a fixed palette expressed as named colour roles. I worked from Tufte's principles [6] on data-ink ratio and on annotating reference values rather than implying them."),

      h3("What I implemented"),
      p("A five-panel dashboard for a single student and a batch-wide attendance matrix, both built on a shared house style that no chart is allowed to override with a raw colour value:"),
      ...code([
        "class Palette:",
        "    SURFACE = \"#fcfcfb\";  INK = \"#0b0b0b\";  GRID = \"#e1e0d9\"",
        "    PRESENT = \"#0ca30c\";  ABSENT = \"#d03b3b\"   # reserved status pair",
        "",
        "    @classmethod",
        "    def status(cls, present: bool) -> str:",
        "        return cls.PRESENT if present else cls.ABSENT",
      ]),
      p("Four rules shaped every panel. The form follows the data's job, so the headline attendance percentage is a large number and a progress meter rather than a pie chart - a proportion is read faster from a number than from an angle. Status is never carried by colour alone: every present or absent mark also carries a P or an A, so the figures survive greyscale printing and colour-vision deficiency. No chart uses a second y-axis; where two measures were needed, two panels were used. And reference values - the 80 per cent attendance requirement, the ink decision threshold - are drawn as labelled dashed lines rather than left for the reader to infer."),
      p("The panel I am most pleased with is the fourth: a bar chart of the ink measured in each of that student's signature cells, against the decision threshold. It is unusual to show a user the internal measurement behind a classification, but attendance is a record students dispute, and a chart showing 11.6 per cent ink against a 0.75 per cent threshold settles the dispute without reopening the photograph. It also became the group's most-used debugging tool: when a cell was misclassified during development, that panel showed immediately whether the problem was in the measurement or in the threshold."),

      h3("Difficulties"),
      p("The batch comparison panel gave me the most trouble. My first version put the student names on the y-axis as tick labels, and with names as long as \"Hansa Anuradha Wickramanayake\" they were clipped by the panel margin. Widening the left margin would have thrown the panel out of alignment with the three above it. I moved the labels inside the bars instead, left-aligned, with the value outside the bar end - a standard pattern for ranked horizontal bars that removed the need for any extra margin and kept all four panels on one grid."),
      p("A second difficulty was the threshold annotation on the ink panel, which in early versions overlapped the dashed line it referred to and, on students with low ink values, the bars as well. Placing it at the top right of the axes, above every bar, and prefixing it with a short dashed glyph so that it reads as a legend for the line, solved it for all six students."),
      p("The third was choosing the colours properly rather than by eye. Present and absent are a reserved status pair, distinct from the categorical series colours, so that a status colour can never be mistaken for a data series; and because the two greens and reds are close in luminance, the letter labels are what actually carry the meaning."),

      h3("How I verified my work"),
      p("Chart code cannot be unit-tested for appearance, so I verified by rendering. Every dashboard was generated for all six students and inspected for label collisions, clipping and axis overflow, and the matrix was rendered for the whole batch. I also checked that the dashboard fails cleanly with a clear message when a student has no recorded sessions rather than raising an obscure Matplotlib error, and that infovis.py reports a helpful error when the database does not exist yet."),

      h3("What my work contributes to the measured result"),
      bullet("Six student dashboards and one batch matrix, all rendered from a single style definition, with no raw colour value anywhere in the chart code."),
      bullet("Every present or absent mark carries a letter as well as a colour, so all the figures in this report remain readable in greyscale."),
      bullet("The ink-diagnostic panel became the group's primary tuning instrument: it distinguishes a measurement error from a threshold error at a glance, which no other view in the system does."),
      ...ownedFiles("Files I own.", [
        ["attendance/visualize.py", "Palette, apply_house_style, StudentSummary, StudentDashboard, ClassHeatmap, SimilarityMatrixPlot, save_figure"],
        ["infovis.py", "The visualisation command-line interface"],
        ["tools/make_figures.py", "The architecture diagram and the stage close-ups used in this report"],
      ]),
    ],

    // ------------------------------------------------------------------ 9
    () => [
      h3("Scope of my contribution"),
      p("I owned signature recognition - the extension the brief invites, in which a student's signatures are collected, compared, and any that do not match are reported. My module is verify.py and the investigate.py program that drives it."),

      h3("Technologies used"),
      p("A histogram of oriented gradients implemented from the Dalal-Triggs description [9]; a zoning (ink-density) descriptor following the offline signature-verification literature [7][8]; ORB key points [10] with Lowe's ratio test [11]; and the modified z-score of Iglewicz and Hoaglin [12] for the outlier decision."),

      h3("What I implemented"),
      p("Four independent descriptors and a fusion of them. The zoning descriptor divides the normalised specimen into an 8 x 16 grid and records the ink density of each cell - where on the canvas the writer puts their weight. HOG records which way the strokes run. ORB records repeated local structure. The aspect ratio, which normalisation deliberately destroys, is measured beforehand and compared separately."),
      p("I had to write HOG myself, because OpenCV 5 withdrew HOGDescriptor from its Python bindings. That turned out to be a benefit: every step is inspectable, and implementing the bilinear orientation voting and the L2-Hys block normalisation by hand taught me more about the descriptor than calling it would have."),
      ...code([
        "position = angle / bin_width - 0.5",
        "lower = np.floor(position).astype(np.int32)",
        "fraction = (position - lower).astype(np.float32)",
        "np.add.at(histogram[row, column], lower_bin, weights * (1.0 - fraction))",
        "np.add.at(histogram[row, column], upper_bin, weights * fraction)",
      ]),
      p("The decision rule reports a specimen when it is both statistically unusual among its peers and materially less similar than they are, or when its similarity is anomalously low outright."),

      h3("Difficulties"),
      p("This was the part of the project where I learned the most, mostly by being wrong."),
      p("My first version scored genuine pairs at 0.30 similarity - barely above impostor pairs - and flagged every specimen of every student. The cause was not the descriptor but the input: the specimens were whole row bands, so they contained the neighbouring signature's overflow and the table border, and after normalisation the actual signature occupied a different part of the canvas in each one. Working with my colleague on signature.py to produce a tight, per-row specimen, and using the pipeline's own ink mask instead of re-thresholding the crop, raised the sensitivity index d' from 0.74 to 0.92."),
      p("My second mistake was the outlier rule. I originally flagged any specimen whose mean similarity fell more than 1.25 standard deviations below the cohort mean, and it duly reported exactly one mismatch per student, for all six students. That is not a finding, it is an artefact: with five samples the sample standard deviation is small and the lowest sample falls below such a cut almost every time. The modified z-score is built on the median and the median absolute deviation, neither of which is dragged by the point being tested; adding a requirement that a flagged specimen also sit materially below the cohort median halved the false-alarm rate, from 8.7 per cent to 4.3 per cent."),
      p("The third mistake was found by a test rather than by me. I asserted that similarity should be symmetric, and it was not: nearest-neighbour matching is directional, so matching A against B gives a different count from matching B against A. Averaging the two directions fixed it. A similarity that depends on argument order would have made the whole comparison matrix depend on the order of a loop."),
      p("The hardest thing, though, was accepting the result. With an equal error rate of 35 per cent this module cannot be presented as a signature checker. Because no forgeries were available I measured detection power with a random-forgery test - planting another writer's genuine signature in a student's set - which caught 44 per cent of intruders at a 4 per cent false-alarm rate. That is real but modest, and the tool's own output says so: it is a screening aid that ranks specimens for human review, not an authority."),

      h3("How I verified my work"),
      p("The verification tests in test_signature_verify.py cover the HOG length against the Dalal-Triggs formula, block normalisation, symmetry, scale invariance, the handling of empty specimens, and the robust outlier statistics. Beyond the unit tests I wrote the evaluation in tools/evaluate.py that produces the genuine/impostor separation, the equal error rate and the random-forgery result quoted in Section 7.6."),

      h3("What my work contributes to the measured result"),
      bullet("The sensitivity index d' improved from 0.74 to 0.92 through better segmentation and four-way descriptor fusion."),
      bullet("Random forgeries are detected 43.9 per cent of the time at a 4.3 per cent false-alarm rate on genuine specimens."),
      bullet("Replacing the naive outlier rule roughly halved the false-alarm rate, from 8.7 per cent to 4.3 per cent, and removed the artefact by which every student was reported to have exactly one bad signature."),
      ...ownedFiles("Files I own.", [
        ["attendance/verify.py", "HistogramOfOrientedGradients, Specimen, SignatureVerifier, zoning, normalisation, fusion, the outlier rule, the contact sheets"],
        ["investigate.py", "The recognition command-line interface"],
        ["tools/evaluate.py", "evaluate_signatures, evaluate_intrusion and their figures"],
      ]),
    ],

    // ------------------------------------------------------------------ 10
    () => [
      h3("Scope of my contribution"),
      p("I owned quality: the test suite, the ground-truth labelling, the accuracy measurement, and the robustness sweeps. My job was to be able to say what the system actually does, as opposed to what it was intended to do."),

      h3("Technologies used"),
      p("The standard library's unittest - chosen over pytest so that the prototype can be marked without installing a test runner - together with tempfile for isolation, csv for the ground truth, and OpenCV and NumPy to generate synthetic fixtures."),

      h3("What I implemented"),
      p("First, the ground truth. I examined all thirty signature cells at native resolution and labelled each PRESENT or ABSENT before any threshold had been tuned, recording anything unusual in a note column. That file is read by both the evaluation tool and the integration test, so no figure in this report is a number somebody typed."),
      p("Second, the synthetic sheet generator in tests/support.py. Testing image processing against photographs alone is unsatisfactory because the expected answer is a matter of opinion; the generator draws a signing sheet with a chosen set of signed rows, at a chosen rotation, so that every assertion has an exact ground truth. It is used by twenty-seven of the tests."),
      ...code([
        "image, expected = synthetic_sheet(signed_rows=(0, 2, 4), skew_degrees=2.0)",
        "# ... run the pipeline ...",
        "self.assertEqual(present, list(expected[\"signed_rows\"]))",
      ]),
      p("Third, the evaluation tool, which re-processes all five sheets, compares every cell against the ground truth, and reports accuracy, the confusion matrix and - the number I consider most important - the margin between the ink measured in signed and unsigned cells. An accuracy of 100 per cent on thirty cells would mean little if the decisions were marginal; the seven-fold separation is what makes it meaningful."),
      p("Fourth, the resolution sweep in Section 7.5, which runs all five sheets at six working widths."),

      h3("Difficulties"),
      p("The most useful thing I did was to distrust a passing test suite. Everything passed at the default resolution, so I asked what would happen at a different one - and the answer was that rules broke up and rows were lost, because several neighbourhood sizes were fixed in pixels rather than scaled from a reference width. That is a class of bug no amount of testing at one resolution would ever reveal, and it changed three modules."),
      p("Two of my tests found real defects rather than confirming intended behaviour. The symmetry test on the verifier exposed the directional ORB matching. The test asserting that a consistent set of specimens is reported as consistent exposed the hair-trigger outlier rule. In both cases the code was changed and the test was kept as written; I think that distinction matters, because the temptation when a test fails is always to adjust the expectation."),
      p("Two of my tests were themselves wrong, and I record that as well. I asserted that Otsu would return a threshold strictly between the two grey levels of a two-tone image, when in fact it settles on the darker mode itself and segments the image perfectly - my expectation was badly formed, and I rewrote the test to assert the segmentation. And I built an ambiguity fixture from two indices that do not in fact share a suffix."),
      p("Finally, I pushed for the honest framing of the signature verification. The temptation was to quote the plain accuracy at the best threshold, 81 per cent, which sounds respectable. But impostor pairs outnumber genuine ones six to one, so that number is largely obtained by calling everything an impostor. Balanced accuracy is 71 per cent and the equal error rate is 35 per cent, and those are the numbers reported."),

      h3("How I verified my work"),
      p("By running it. The suite is 119 tests and takes ten seconds; every member ran it before committing. The integration test re-checks all five photographs against the ground-truth file on every run, so a change that improves one sheet at the expense of another cannot pass unnoticed."),

      h3("What my work contributes to the measured result"),
      bullet("119 tests, no failures, no errors, in ten seconds - and runnable with no test runner installed."),
      bullet("30 of 30 cells verified against hand labels written before any threshold was tuned, together with the confusion matrix and the seven-fold separation margin that makes the result meaningful."),
      bullet("Two real defects found by tests rather than by inspection, and one silent resolution dependency found by asking what would happen outside the configuration everyone had been using."),
      ...ownedFiles("Files I own.", [
        ["tests/support.py", "The synthetic signing-sheet generator"],
        ["tests/run_tests.py", "The discovery runner and its transcript"],
        ["tests/test_pipeline.py", "Date inference, progress reporters, whole-pipeline and reference-sheet tests"],
        ["data/ground_truth.csv", "Hand labels for all 30 signature cells"],
        ["tools/evaluate.py", "evaluate_attendance, the confusion matrix, the separation figure"],
      ]),
    ],
  ];

  members.forEach((member, index) => {
    out.push(...memberHeader(member, index + 1));
    out.push(...sections[index]());
  });

  return out;
}

// --------------------------------------------------------------------------

function appendices() {
  return [
    h1("Appendix A. Running the prototype"),
    p("The prototype needs Python 3.10 or later and four third-party packages. The signature descriptors are implemented in the project itself, so scikit-image, scikit-learn and SciPy are deliberately not dependencies."),
    ...code([
      "python -m pip install -r requirements.txt",
      "",
      "# 1. process the signing sheets  (--show displays each stage in a window)",
      "python sams.py data/sheets/31.05.2019.jpeg data/info.xml --show",
      "python sams.py \"data/sheets/*.jpeg\" data/info.xml",
      "",
      "# 2. visualise a student, or the whole batch",
      "python infovis.py 10000409",
      "python infovis.py --class",
      "",
      "# 3. compare a student's signatures",
      "python investigate.py 10000409",
      "python investigate.py --all",
      "",
      "# 4. the tests and the accuracy measurement",
      "python tests/run_tests.py",
      "python tools/evaluate.py",
    ]),
    p("Stage images are written to output/stages/<sheet>/, including the contact sheet reproduced as Figure 2. Charts are written to output/figures/."),

    h1("Appendix B. Parameter reference"),
    p("Every tunable value in the system, with the value used for the results in this report. All are defined in attendance/config.py and may be overridden from the command line."),
    ...table(
      "Pipeline parameters.",
      [2600, 1200, 5226],
      ["Parameter", "Value", "Meaning"],
      [
        ["working_width", "1700", "Width every photograph is rescaled to before processing"],
        ["background_kernel", "41", "Closing element used to estimate the illumination field"],
        ["bilateral_diameter", "7", "Bilateral filter neighbourhood"],
        ["bilateral_sigma_colour / space", "45 / 45", "Range and spatial sigmas of the bilateral filter"],
        ["adaptive_block", "31", "Adaptive threshold neighbourhood (scaled with the working width)"],
        ["adaptive_c", "12", "Constant subtracted from the local weighted mean"],
        ["max_skew_degrees", "12.0", "Rotations larger than this are treated as detection failures"],
        ["hough_min_line_ratio", "0.25", "Minimum segment length, as a fraction of image width"],
        ["horizontal_scale", "28", "Horizontal rule element is width / 28"],
        ["vertical_scale", "42", "Vertical rule element is height / 42"],
        ["HORIZONTAL_COVERAGE", "0.30", "Absolute floor for a run of ink to be a rule"],
        ["RELATIVE_COVERAGE", "0.62", "Fraction of its table's median rule a rule must reach"],
        ["cell_margin_ratio", "0.10", "Fraction trimmed from each side of a cell"],
        ["overflow_ratio", "0.22", "How far the analysis strip extends past the table border"],
        ["min_component_area_ratio", "0.0016", "Smallest component that is not speckle"],
        ["min_ink_ratio", "0.0075", "Ink fraction required for PRESENT"],
        ["min_ink_pixels", "110", "Absolute pixel floor for PRESENT"],
        ["SPLIT_HEIGHT_IN_ROWS", "1.6", "Above this height a component is shared between rows"],
        ["verify_size", "128 x 64", "Canonical specimen size for verification"],
        ["zoning_grid", "8 x 16", "Ink-density descriptor grid"],
        ["fusion_weights", "0.35 / 0.35 / 0.10 / 0.20", "Zoning, HOG, ORB, aspect agreement"],
        ["mismatch_threshold", "0.35", "Absolute similarity floor for reporting a specimen"],
        ["outlier_z", "3.5", "Modified z-score cut-off"],
        ["outlier_relative_gap", "0.20", "Material gap below the cohort median also required"],
      ]
    ),
  ];
}

module.exports = { contributions, appendices };

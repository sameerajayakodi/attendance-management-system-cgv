# SAMS — Student Attendance Management System

Coursework prototype for **CS402.3 Computer Graphics and Visualization**, NSBM Green
University Town, School of Computing.

The system reads a smart-phone photograph of a paper signing sheet, works out who
signed and who did not, stores the result in a local database, visualises a
student's attendance, and compares a student's signatures across sessions to flag
specimens that do not match.

---

## Quick start

```bash
python -m pip install -r requirements.txt
```

```bash
python sams.py data/sheets/31.05.2019.jpeg data/info.xml
```

```bash
python infovis.py 10000409
```

```bash
python investigate.py 10000409
```

## The three programs

| Program | What it does |
|---|---|
| `sams.py` | Image processing. Reads a sheet plus `info.xml`, shows every processing stage, decides PRESENT/ABSENT per student, writes to SQLite. |
| `infovis.py` | Data visualisation. Draws an attendance dashboard for one student, or `--class` for the whole batch. |
| `investigate.py` | Recognition. Compares a student's stored signatures and reports any that do not match the rest. |

### `sams.py`

```bash
python sams.py "data/sheets/*.jpeg" data/info.xml --show
```

| Option | Meaning |
|---|---|
| `--show` | Display each processing stage in a window as it completes |
| `--delay N` | Milliseconds each stage window is held (default 700) |
| `--date YYYY-MM-DD` | Override the session date (otherwise read from the file name) |
| `--db PATH` | SQLite file (default `data/attendance.db`) |
| `--width N` | Working resolution (default 1700; see *Known limitations*) |
| `--ink-threshold F` | Minimum fraction of a cell that must be ink for PRESENT |
| `--save-crops` | Also export every signature cell as a PNG |
| `--no-stages` | Do not write stage images |
| `--dry-run` | Process without touching the database |

Stage images are written to `output/stages/<sheet>/`, including a contact sheet
that tiles all nine stages onto one page.

### `infovis.py`

```bash
python infovis.py 10000409
python infovis.py 0409         # a trailing part of an index also works
python infovis.py --class      # batch-wide attendance matrix
python infovis.py 10000409 --save-only
```

### `investigate.py`

```bash
python investigate.py 10000409
python investigate.py --all
```

Exit status is `1` when a specimen is flagged, so the tool can be used from a
script.

## Repository layout

```
prototype/
├── sams.py                     entry point: image processing
├── infovis.py                  entry point: visualisation
├── investigate.py              entry point: signature recognition
├── attendance/                 the implementation package
│   ├── config.py               every tunable parameter, in one place
│   ├── imaging.py              pure image-processing primitives
│   ├── table.py                morphological table and grid reconstruction
│   ├── signature.py            ink analysis and the PRESENT/ABSENT decision
│   ├── stages.py               the nine pipeline steps, as objects
│   ├── pipeline.py             orchestration and roster mapping
│   ├── progress.py             progress presentation (console / windows / PNG)
│   ├── records.py              info.xml parsing
│   ├── database.py             SQLite persistence
│   ├── visualize.py            attendance charts
│   └── verify.py               signature descriptors and comparison
├── tools/evaluate.py           accuracy measurement against ground truth
├── tests/                      119 unit and integration tests
└── data/
    ├── info.xml                roster and subject metadata
    ├── ground_truth.csv        hand-labelled status of all 30 signature cells
    └── sheets/                 the five reference photographs
```

## The processing pipeline

| # | Stage | Technique |
|---|---|---|
| 1 | Acquisition | Rescale to the working width so every kernel size is resolution-independent |
| 2 | Greyscale | BT.601 luma |
| 3 | Illumination correction | Estimate the shading field by morphological closing, divide it out |
| 4 | Denoise | Bilateral filter (edge-preserving) |
| 5 | Binarisation | Adaptive Gaussian threshold; Otsu computed alongside for comparison |
| 6 | Skew correction | Median angle of the long Hough segments, then rotate |
| 7 | Rule extraction | Morphological opening with long thin kernels |
| 8 | Table reconstruction | Projection profiles → rule positions → grid; repair missing rules from the uniform row pitch |
| 9 | Signature analysis | Subtract rules, group ink into components, charge each component to the row that owns most of its mass |

## Testing

```bash
python tests/run_tests.py
```

```bash
python tools/evaluate.py
```

`run_tests.py` uses only the standard library's `unittest`. The suite covers the
XML parser, the database, the imaging primitives, the table detector and its
repair rule, the ink classifier, the HOG implementation and the verifier, the
FastAPI layer (upload handling, the media path-traversal guard, session
deletion, student-index disambiguation), plus an integration test that runs
all five reference photographs against `data/ground_truth.csv`.

`test_web_api.py` imports the FastAPI app, so `web/api/requirements.txt` must
also be installed before running the full suite:

```bash
python -m pip install -r ../web/api/requirements.txt
```

Measured on the five supplied sheets:

| Measure | Result |
|---|---|
| Attendance accuracy | **100 %** (30/30 cells) |
| Ink in signed cells | mean 9.72 %, min 3.30 % of cell area |
| Ink in unsigned cells | mean 0.32 %, max 0.47 % |
| Separation margin | **7.0×** between the two classes |
| Signature verification | d′ = 0.92, equal error rate 35 % |
| Random-forgery detection | 44 % of planted specimens caught, 4 % false alarms |

## `info.xml`

The brief's Figure 1 writes the batch as a bare number, `<15>`. An XML element
name may not begin with a digit, so that document is not well-formed and no
conforming parser will read it. `RosterParser` rewrites numeric element names to
`<batch id="15">` before parsing, and therefore accepts both the literal Figure-1
layout and the schema-valid equivalent shipped in `data/info.xml`.

A student may be named by a full index or by a trailing part of one (at least
three characters), so `infovis.py 0409` resolves to `10000409`. The brief's short
indices such as `001` work directly when the roster itself uses them.

**The order of the `<student>` elements is significant** — it must match the order
of the rows printed on the sheet, because that is what maps an anonymous
signature cell back to a student index.

## Known limitations

* **Working resolution.** The default (1700 px wide) and native resolution
  (3024 px) both give 100 % on the reference set. At some intermediate widths a
  faint bottom rule on one sheet is lost; the system detects the row-count
  mismatch and warns rather than silently mis-assigning rows.
* **Semantics versus pixels.** On 21.06.2019 a lecturer wrote `ab` in one
  signature cell. Ink is present, so the system reports PRESENT; reading that
  mark as "absent" needs handwriting recognition, which is out of scope.
* **Signature verification is a screening aid.** Genuine and impostor similarity
  distributions overlap heavily (EER ≈ 35 %). `investigate.py` ranks specimens
  for human review; it is not accurate enough to declare attendance fraudulent
  on its own.
* **No OCR.** The session date comes from the file name (as the brief's own
  example implies) or `--date`, not from the date cell on the sheet.

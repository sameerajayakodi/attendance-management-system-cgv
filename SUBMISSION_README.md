# CS402.3 Coursework — what is here and what you must edit

## Ready to submit

| File | What it is |
|---|---|
| `CS402.3_Coursework_Submission.zip` | **The upload.** Contains `prototype.zip` and the report `.docx`, exactly as the brief specifies. |
| `prototype.zip` | The working prototype — the three command-line programs plus the web interface (63 files, 7.1 MB, includes the five sheets and a populated database). |
| `report/CS402.3_CGV_Coursework_Report.docx` | The report: 56 pages, 14 figures, 20 tables, 22 numbered equations, 18 IEEE references. |

The prototype ships in two forms, sharing one implementation:

- **`prototype/`** — the command-line system the brief asks for: `sams.py`,
  `infovis.py`, `investigate.py`, 119 tests and the evaluation tool.
- **`web/`** — a browser interface over the same package: a FastAPI server and a
  React + MUI front end. It reimplements nothing; see `web/README.md`.

## ⚠ Before you submit — fill in the group

The report's front page and its ten individual-contribution sections carry
placeholders (`<< Member 1 - full name >>`, `<< index >>`) because I do not know
your group. **Edit them, then rebuild:**

1. Open `report/build_report.js` and replace the ten lines in the `MEMBERS`
   array with the real names, index numbers and the role each person took.
2. Rebuild the document:

```bash
cd report && node build_report.js
```

3. Open the `.docx` in Word, right-click the Contents table and choose
   *Update Field* so the page numbers are correct, then save.

Then rebuild the submission zips:

```bash
cd "C:/Users/samee/Desktop/CGV Assignment" && python package.py
```

You can of course edit the names directly in Word instead — but if you do,
change them in **both** the front-page table and each `11.n` heading, and do not
rebuild afterwards or your edits will be overwritten.

The ten roles were assigned to match the work that actually exists in the code,
so each contribution section describes real modules, real difficulties and real
measurements. Reassign the roles between members if your split was different;
the text follows the role, not the person.

## What the prototype does

```bash
cd prototype
python -m pip install -r requirements.txt
python sams.py "data/sheets/*.jpeg" data/info.xml --show
python infovis.py 10000409
python investigate.py 10000409
python tests/run_tests.py
python tools/evaluate.py
```

## Running the web interface

Two processes — the API first, then the front end. Full detail in `web/README.md`.

```bash
python -m pip install -r web/api/requirements.txt && python web/api/main.py
```

```bash
npm install --prefix web/frontend && npm run dev --prefix web/frontend
```

Then open **http://localhost:5180**. You can upload a signing sheet, watch the
nine processing stages, read the attendance, and compare a student's signatures
— all driven by the same `attendance` package the command-line tools use.

Measured on the five supplied signing sheets:

- **100 % attendance accuracy** — all 30 signature cells correct, no false
  positives, no false negatives, verified against hand labels in
  `data/ground_truth.csv`.
- **7.0× separation** between the ink in signed and unsigned cells, so the
  decision threshold is not tuned to the test data.
- **119 automated tests**, no failures.
- Signature verification: d′ = 0.92, equal error rate 35 %, random forgeries
  detected 44 % of the time at a 4 % false-alarm rate. Reported honestly in the
  report as a screening aid rather than an authority.

## Regenerating the report's figures

Every figure in the report is real program output. To rebuild them:

```bash
cd prototype
python sams.py "data/sheets/*.jpeg" data/info.xml
python tools/evaluate.py
python tools/make_figures.py --copy-to-report
```

Then rebuild the document with `node build_report.js`.

## Note on 21.06.2019

One cell on that sheet contains the hand-written annotation `ab` rather than a
signature. The system reports PRESENT because there is ink in the cell, which is
correct by its own definition. This is recorded in the ground-truth file and
discussed in Section 8.8 of the report as a limitation of any pixel-counting
approach. Do not treat it as a bug to be fixed with a threshold.

# SAMS web interface

A browser front end for the CS402.3 prototype: upload a photograph of a signing
sheet, watch what the pipeline did to it, and read the attendance it recovered.

```
web/
├── api/          FastAPI server — a thin REST layer over prototype/attendance
└── frontend/     React 19 + MUI 7 + TanStack Query + Recharts (Vite)
```

The API **reimplements nothing**. The image processing, the roster parsing, the
database and the signature verification all live in `prototype/attendance`; the
server only turns HTTP requests into calls on that package. The command-line
programs and the web interface therefore cannot disagree about what the system
does — they are the same code.

---

## Running it

Two processes. Start the API first.

```bash
python -m pip install -r web/api/requirements.txt
```

```bash
python web/api/main.py
```

```bash
npm install --prefix web/frontend && npm run dev --prefix web/frontend
```

Then open **http://localhost:5180**. Vite proxies `/api` to the Python process
on port 8000, so the browser never leaves one origin and CORS never applies.

If the database is empty, the dashboard says so — process a sheet from the
**Signing sheets** page, or seed it from the command line first:

```bash
python prototype/sams.py "prototype/data/sheets/*.jpeg" prototype/data/info.xml
```

## The pages

| Page | What it shows |
|---|---|
| **Dashboard** | Attendance per session against the 80% requirement, who is below it, and the student × session matrix |
| **Signing sheets** | Every processed photograph, with a thumbnail, the counts and the attendance rate; upload a new one from here |
| **Session detail** | Three tabs — the per-student decision table (with the signature crop and the measured ink), the nine pipeline stage images, and the original photograph |
| **Students** | Attendance rate per student, with the number of stored signature specimens |
| **Student detail** | Timeline, cumulative-rate line, ink-per-session bars against the decision threshold, full history, and a batch comparison |
| **Signatures** | Every specimen a student has left, captured and normalised, with the pairwise similarity matrix and the outlier statistics |
| **Pipeline** | What each of the nine stages does, and the live parameter values read from the running system |

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service and database status |
| `GET` | `/api/settings` | The live pipeline parameters |
| `GET` | `/api/overview` | Everything the dashboard needs, in one round trip |
| `GET` | `/api/sessions` | All processed sheets |
| `GET` | `/api/sessions/{date}` | One session with its outcomes and stage images |
| `POST` | `/api/sessions` | Upload a photograph and process it (multipart) |
| `DELETE` | `/api/sessions/{date}` | Remove a session's records |
| `GET` | `/api/students` | Roster with attendance rates |
| `GET` | `/api/students/{index}` | History, cumulative rates, batch comparison |
| `GET` | `/api/students/{index}/verify` | Signature comparison report and similarity matrix |
| `GET` | `/api/media/sheet/{date}` | The original photograph, rescaled |
| `GET` | `/api/media/stage/{stem}/{slug}` | One pipeline stage image |
| `GET` | `/api/media/signature/{index}/{date}` | A signature specimen (add `/normalised` for the descriptor's view) |

Interactive documentation is at **http://127.0.0.1:8000/docs** while the API runs.

### Two decisions worth knowing about

**Stage images are re-encoded per request.** The stage PNGs on disk are up to
3.4 MB — far too heavy for a gallery. They are rescaled and the format is chosen
from the *source* content: a near-two-tone image (a binary mask, the rule masks)
stays PNG, because JPEG puts ringing around exactly the strokes the mask exists
to show; everything else becomes JPEG. That takes a 3.4 MB PNG to 11–126 KB.

**Absent rows carry no signature URL and no pen colour.** The pipeline stores a
crop for every row, signed or not, and the HSV analysis will happily name a
colour for the noise in an empty cell. Reporting either would imply a signature
that is not there, so both are suppressed for `ABSENT` rows.

## Design

The visual language is the LeadFlow design system, ported wholesale:

- `src/theme/tokens.ts` — every colour, font and metric. **No page contains a
  hex literal.** The domain maps are SAMS's own: attendance status, verification
  verdict, pen colour, pipeline phase.
- `src/theme.ts` — `createAppTheme(mode)` (compact controls, flat cards, radius
  10/14/16, black/white contained buttons, emerald accents) plus `tintSx`, the
  single formula every status chip uses.
- `src/components/common/` — the chip family, `DrawerShell`, `PageHeader`,
  `StatTile`, `EmptyState`, `TableSkeleton`, `DebouncedSearchInput`.

Rules carried over: create/edit flows are **right-side drawers, not dialogs**;
list pages get a search toolbar and `TablePagination`; a live state renders as a
solid tinted chip and a label as a neutral `MetaChip`; charts use the validated
categorical order and assign colour by the entity's fixed index.

Two rules are specific to this product:

- **Present/absent never depends on colour alone.** Green and red are exactly
  the pair red-green colour blindness collapses, so every attendance mark also
  carries a tick/cross glyph or a `P`/`A` letter.
- **The measurement is shown, not just the verdict.** Attendance is a record
  students dispute; the ink percentage behind each decision is visible next to
  it, with the threshold drawn on the chart.

## Notes

- Charts have entry animation disabled — on a dense dashboard the data should
  appear, not arrive. It also means the charts render correctly when printed or
  captured.
- Routes are code-split, so the initial payload is the shell plus one page
  rather than the whole application including Recharts.
- Processing is synchronous: a sheet takes about 0.7 s, so the request simply
  waits. A production deployment with many sheets would want a job queue and a
  progress stream instead.

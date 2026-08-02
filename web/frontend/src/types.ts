/** Shapes returned by the SAMS API (web/api/main.py). */

export type AttendanceStatus = "PRESENT" | "ABSENT";

export interface Stage {
  order: number;
  slug: string;
  name: string;
  description: string;
  url: string;
}

export interface StageTiming {
  order: number;
  name: string;
  description: string;
  elapsedMs: number;
  notes: Record<string, string>;
}

export interface Outcome {
  indexNo: string;
  name: string;
  title: string;
  row: number;
  status: AttendanceStatus;
  confidence: number;
  inkRatio: number;
  inkPixels: number;
  components: number;
  /** null when the row was unsigned — a pen colour there would be noise. */
  penColour: string | null;
  signatureUrl: string | null;
}

export interface Session {
  date: string;
  subjectCode: string;
  sourceImage: string;
  sheetUrl: string;
  processedAt: string;
  present: number;
  absent: number;
  total: number;
  rate: number;
  stages: Stage[];
  outcomes: Outcome[];
  /** Only present on the response to a fresh upload. */
  warnings?: string[];
  elapsedMs?: number;
  skewDegrees?: number;
  stageTimings?: StageTiming[];
}

export interface StudentRow {
  indexNo: string;
  name: string;
  title: string;
  batch: string;
  present: number;
  total: number;
  rate: number;
  specimens: number;
  lastSession: string | null;
  lastStatus: AttendanceStatus | null;
}

export interface HistoryEntry {
  date: string;
  status: AttendanceStatus;
  inkRatio: number;
  confidence: number;
  cumulativeRate: number;
  sheet: string;
  signatureUrl: string | null;
}

export interface StudentDetail {
  indexNo: string;
  name: string;
  present: number;
  total: number;
  rate: number;
  required: number;
  history: HistoryEntry[];
  classRates: { indexNo: string; name: string; rate: number }[];
}

export interface MatrixRow {
  indexNo: string;
  name: string;
  rate: number;
  cells: { date: string; status: AttendanceStatus; inkRatio: number }[];
}

export interface Overview {
  sessionCount: number;
  studentCount: number;
  recordCount: number;
  overallRate: number;
  presentCount: number;
  absentCount: number;
  dates: string[];
  trend: { date: string; present: number; absent: number; rate: number }[];
  matrix: MatrixRow[];
  atRisk: { indexNo: string; name: string; rate: number }[];
}

export interface Specimen {
  label: string;
  date: string;
  inkRatio: number;
  aspect: number;
  keypoints: number;
  meanSimilarity: number;
  modifiedZ: number;
  verdict: string;
  url: string;
  normalisedUrl: string;
}

export interface VerifyReport {
  indexNo: string;
  name: string;
  threshold: number;
  cohortMean: number;
  cohortSd: number;
  consistent: boolean;
  summary: string;
  flagged: number[];
  specimens: Specimen[];
  matrix: number[][];
}

export interface Settings {
  workingWidth: number;
  inkThreshold: number;
  minInkPixels: number;
  adaptiveBlock: number;
  adaptiveC: number;
  maxSkewDegrees: number;
  overflowRatio: number;
  mismatchThreshold: number;
  outlierZ: number;
}

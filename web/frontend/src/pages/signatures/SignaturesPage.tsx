import { useEffect, useState } from "react";
import {
  Box, Card, CardContent, Divider, MenuItem, Select, Stack, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, ToggleButton, ToggleButtonGroup,
  Tooltip, Typography, useTheme,
} from "@mui/material";
import { useNavigate, useParams } from "react-router-dom";
import { useStudents, useVerify } from "../../api/queries";
import {
  EmptyState, ErrorState, FieldRow, MetaChip, PageHeader, SectionLabel,
  TableSkeleton, VerdictChip,
} from "../../components/common";
import { SEQUENTIAL_BLUE, SEMANTIC } from "../../theme/tokens";
import { shortDate } from "../../lib/format";

/** Step of the one-hue sequential ramp for a similarity in [0, 1]. */
function rampColor(value: number): string {
  const index = Math.min(SEQUENTIAL_BLUE.length - 1, Math.max(0, Math.round(value * (SEQUENTIAL_BLUE.length - 1))));
  return SEQUENTIAL_BLUE[index];
}

export default function SignaturesPage() {
  const { indexNo } = useParams<{ indexNo?: string }>();
  const navigate = useNavigate();
  const theme = useTheme();
  const { data: students } = useStudents();
  const [selected, setSelected] = useState(indexNo ?? "");
  const [view, setView] = useState<"captured" | "normalised">("captured");

  useEffect(() => {
    if (indexNo) setSelected(indexNo);
    else if (!selected && students?.length) setSelected(students[0].indexNo);
  }, [indexNo, students, selected]);

  const { data, isLoading, error, refetch } = useVerify(selected || undefined);

  const choose = (value: string) => {
    setSelected(value);
    navigate(`/signatures/${value}`, { replace: true });
  };

  return (
    <>
      <PageHeader
        title="Signature investigation"
        subtitle="Every specimen a student has left, compared with the others to surface any that do not match"
        actions={
          <Select
            value={students?.some((s) => s.indexNo === selected) ? selected : ""}
            onChange={(e) => choose(String(e.target.value))}
            displayEmpty
            sx={{ minWidth: 260 }}
          >
            <MenuItem value="" disabled>Choose a student…</MenuItem>
            {(students ?? []).map((s) => (
              <MenuItem key={s.indexNo} value={s.indexNo}>
                {s.name} · {s.specimens} specimen{s.specimens === 1 ? "" : "s"}
              </MenuItem>
            ))}
          </Select>
        }
      />

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading || !data ? (
        <TableSkeleton rows={6} />
      ) : data.specimens.length === 0 ? (
        <Card>
          <CardContent>
            <EmptyState
              message="No signature specimens are on record for this student"
              hint="Specimens are stored whenever a sheet is read and the student has signed it."
            />
          </CardContent>
        </Card>
      ) : (
        <>
          {/*Verdict banner*/}
          <Card
            sx={{
              mb: 2.5,
              borderLeft: "4px solid",
              borderColor: data.consistent ? SEMANTIC.success : SEMANTIC.warning,
            }}
          >
            <CardContent>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                justifyContent="space-between"
                alignItems={{ sm: "center" }}
                spacing={1.5}
              >
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 0.25 }}>{data.name}</Typography>
                  <Typography variant="body2" color="text.secondary">{data.summary}</Typography>
                </Box>
                <Stack direction="row" spacing={1}>
                  <MetaChip label={`${data.specimens.length} specimens`} />
                  <MetaChip
                    label={data.consistent ? "Consistent" : `${data.flagged.length} to review`}
                    tone={data.consistent ? "success" : "warning"}
                  />
                </Stack>
              </Stack>
            </CardContent>
          </Card>

          {/*Specimens*/}
          <Card sx={{ mb: 2.5 }}>
            <CardContent>
              <Stack
                direction="row"
                justifyContent="space-between"
                alignItems="flex-start"
                spacing={2}
                sx={{ mb: 1.5 }}
              >
                <Box>
                  <SectionLabel sx={{ mb: 0.5 }}>Specimens</SectionLabel>
                  <Typography variant="body2" color="text.secondary">
                    {view === "captured"
                      ? "The signature cells as photographed, cropped to the ink that belongs to the row."
                      : "The same specimens after normalisation — cropped, warped to a fixed canvas and binarised. This is what the descriptors actually compare."}
                  </Typography>
                </Box>
                <ToggleButtonGroup
                  size="small"
                  exclusive
                  value={view}
                  onChange={(_, v) => v && setView(v)}
                >
                  <ToggleButton value="captured" sx={{ textTransform: "none", px: 1.5 }}>Captured</ToggleButton>
                  <ToggleButton value="normalised" sx={{ textTransform: "none", px: 1.5 }}>Normalised</ToggleButton>
                </ToggleButtonGroup>
              </Stack>

              <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
                {data.specimens.map((s, i) => {
                  const flagged = data.flagged.includes(i);
                  return (
                    <Box key={s.label} sx={{ flex: "1 1 240px", minWidth: 210, maxWidth: 320 }}>
                      <Box
                        sx={{
                          border: "2px solid",
                          borderColor: flagged ? SEMANTIC.warning : "divider",
                          borderRadius: 2,
                          bgcolor: "#fff",
                          height: 120,
                          display: "grid",
                          placeItems: "center",
                          overflow: "hidden",
                          p: 1,
                        }}
                      >
                        <Box
                          component="img"
                          src={view === "captured" ? s.url : s.normalisedUrl}
                          alt={`Signature dated ${s.label}`}
                          loading="lazy"
                          sx={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }}
                        />
                      </Box>
                      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mt: 1 }}>
                        <Typography variant="caption" sx={{ fontWeight: 700 }}>{shortDate(s.label)}</Typography>
                        <VerdictChip verdict={s.verdict} />
                      </Stack>
                      <Typography variant="caption" color="text.secondary">
                        similarity {s.meanSimilarity.toFixed(3)} · {s.keypoints} key points
                      </Typography>
                    </Box>
                  );
                })}
              </Stack>
            </CardContent>
          </Card>

          {/*Similarity matrix*/}
          <Stack direction={{ xs: "column", lg: "row" }} spacing={2.5}>
            <Card sx={{ flex: 1, minWidth: 0 }}>
              <CardContent>
                <SectionLabel>Pairwise similarity</SectionLabel>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Each cell blends four descriptors: an ink-density grid, a histogram of oriented gradients,
                  ORB key points and the aspect ratio. One hue, light to dark — and every cell carries its
                  number, so the reading never depends on colour alone.
                </Typography>

                <Box sx={{ overflowX: "auto" }}>
                  <Box sx={{ display: "inline-block", minWidth: 0 }}>
                    <Stack direction="row" spacing={0.5} sx={{ mb: 0.5 }}>
                      <Box sx={{ width: 64, flexShrink: 0 }} />
                      {data.specimens.map((s) => (
                        <Box key={s.label} sx={{ width: 56, textAlign: "center", flexShrink: 0 }}>
                          <Typography variant="caption" color="text.secondary">{shortDate(s.label)}</Typography>
                        </Box>
                      ))}
                    </Stack>
                    {data.matrix.map((row, r) => (
                      <Stack key={r} direction="row" spacing={0.5} sx={{ mb: 0.5 }} alignItems="center">
                        <Box sx={{ width: 64, flexShrink: 0, textAlign: "right", pr: 0.5 }}>
                          <Typography variant="caption" color="text.secondary">
                            {shortDate(data.specimens[r].label)}
                          </Typography>
                        </Box>
                        {row.map((value, c) => (
                          <Tooltip
                            key={c}
                            title={`${shortDate(data.specimens[r].label)} vs ${shortDate(data.specimens[c].label)}: ${value.toFixed(3)}`}
                          >
                            <Box
                              sx={{
                                width: 56, height: 40, flexShrink: 0, borderRadius: 1,
                                display: "grid", placeItems: "center",
                                bgcolor: rampColor(value),
                                color: value > 0.55 ? "#fff" : "#0b0b0b",
                                fontSize: "0.72rem",
                                fontWeight: r === c ? 800 : 600,
                                fontVariantNumeric: "tabular-nums",
                              }}
                            >
                              {value.toFixed(2)}
                            </Box>
                          </Tooltip>
                        ))}
                      </Stack>
                    ))}
                  </Box>
                </Box>
              </CardContent>
            </Card>

            <Card sx={{ flex: 1, minWidth: 300 }}>
              <CardContent>
                <SectionLabel>Per-specimen measurements</SectionLabel>
                <TableContainer sx={{ mt: 1 }}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Specimen</TableCell>
                        <TableCell align="right">Aspect</TableCell>
                        <TableCell align="right">Mean sim.</TableCell>
                        <TableCell align="right">Mod. z</TableCell>
                        <TableCell align="center">Verdict</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.specimens.map((s) => (
                        <TableRow key={s.label} hover>
                          <TableCell>{shortDate(s.label)}</TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {s.aspect.toFixed(2)}
                          </TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {s.meanSimilarity.toFixed(3)}
                          </TableCell>
                          <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {s.modifiedZ.toFixed(2)}
                          </TableCell>
                          <TableCell align="center"><VerdictChip verdict={s.verdict} /></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>

                <Divider sx={{ my: 2 }} />
                <FieldRow label="Cohort mean similarity" value={data.cohortMean.toFixed(3)} />
                <FieldRow label="Cohort standard deviation" value={data.cohortSd.toFixed(3)} />
                <FieldRow label="Absolute floor" value={data.threshold.toFixed(3)} />

                <Box
                  sx={{
                    mt: 2, p: 1.75, borderRadius: 2,
                    bgcolor: theme.palette.mode === "dark" ? "rgba(255,255,255,0.04)" : "rgba(15,23,42,0.03)",
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    A specimen is reported only when it is both statistically unusual among its peers (a
                    modified z-score below −3.5, built on the median so the point being tested cannot inflate
                    its own baseline) <em>and</em> materially below the cohort median. Measured on the reference
                    set the module separates genuine from impostor pairs with d′ = 0.92 and an equal error rate
                    of 35 per cent, so it is a screening aid for human review — not an authority.
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Stack>
        </>
      )}
    </>
  );
}

import {
  Box, Button, Card, CardContent, Divider, LinearProgress, Stack, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Typography, useTheme,
} from "@mui/material";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip as ReTooltip, XAxis, YAxis,
} from "recharts";
import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import DrawRoundedIcon from "@mui/icons-material/DrawRounded";
import { useSettings, useStudent } from "../../api/queries";
import {
  AttendanceChip, ErrorState, FieldRow, MetaChip, SectionLabel,
  StatusSquare, TableSkeleton,
} from "../../components/common";
import { avatarColor, initials, CHART, METRIC, SEMANTIC } from "../../theme/tokens";
import { inkPercent, shortDate } from "../../lib/format";

export default function StudentDetailPage() {
  const { indexNo } = useParams<{ indexNo: string }>();
  const navigate = useNavigate();
  const theme = useTheme();
  const { data, isLoading, error, refetch } = useStudent(indexNo);
  const { data: settings } = useSettings();

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;

  const threshold = (settings?.inkThreshold ?? 0.0075) * 100;
  const short = (data?.rate ?? 100) < METRIC.requiredRate;
  const inkChart = (data?.history ?? []).map((h) => ({
    date: shortDate(h.date),
    ink: +(h.inkRatio * 100).toFixed(2),
    status: h.status,
  }));
  const rateChart = (data?.history ?? []).map((h) => ({ date: shortDate(h.date), rate: h.cumulativeRate }));
  const maxInk = Math.max(...inkChart.map((d) => d.ink), threshold * 2);

  return (
    <>
      <Button
        startIcon={<ArrowBackRoundedIcon />}
        size="small"
        onClick={() => navigate("/students")}
        sx={{ mb: 1.5, ml: -1 }}
      >
        All students
      </Button>

      {isLoading || !data ? (
        <TableSkeleton rows={8} />
      ) : (
        <>
          {/* ── Header ──────────────────────────────────────── */}
          <Card sx={{ mb: 2.5 }}>
            <CardContent>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={2.5}
                alignItems={{ sm: "center" }}
                justifyContent="space-between"
              >
                <Stack direction="row" spacing={2} alignItems="center" sx={{ minWidth: 0 }}>
                  <Box
                    sx={{
                      width: 52, height: 52, borderRadius: "50%", flexShrink: 0,
                      display: "grid", placeItems: "center",
                      bgcolor: avatarColor(data.name), color: "#fff", fontSize: 18, fontWeight: 700,
                    }}
                  >
                    {initials(data.name)}
                  </Box>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="h5" noWrap>{data.name}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Index {data.indexNo} · {data.total} recorded session{data.total === 1 ? "" : "s"}
                    </Typography>
                  </Box>
                </Stack>

                <Stack alignItems={{ xs: "flex-start", sm: "flex-end" }} sx={{ minWidth: 210 }}>
                  <Stack direction="row" alignItems="baseline" spacing={0.75}>
                    <Typography
                      variant="h3"
                      sx={{ lineHeight: 1, color: short ? SEMANTIC.error : SEMANTIC.success }}
                    >
                      {data.rate}%
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      attended {data.present} of {data.total}
                    </Typography>
                  </Stack>
                  <Box sx={{ width: "100%", mt: 1.25, position: "relative" }}>
                    <LinearProgress
                      variant="determinate"
                      value={data.rate}
                      sx={{
                        height: 8,
                        "& .MuiLinearProgress-bar": { bgcolor: short ? SEMANTIC.error : SEMANTIC.success },
                      }}
                    />
                    <Box
                      sx={{
                        position: "absolute", top: -3, bottom: -3,
                        left: `${data.required}%`, width: 2, bgcolor: "text.secondary", borderRadius: 1,
                      }}
                    />
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                    {data.required}% required to sit the examination
                  </Typography>
                </Stack>
              </Stack>
            </CardContent>
          </Card>

          {/* ── Timeline ────────────────────────────────────── */}
          <Card sx={{ mb: 2.5 }}>
            <CardContent>
              <SectionLabel>Session by session</SectionLabel>
              <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                {data.history.map((h) => (
                  <Stack key={h.date} alignItems="center" spacing={0.75} sx={{ minWidth: 74 }}>
                    <StatusSquare status={h.status} size={40} title={`${inkPercent(h.inkRatio)} ink`} />
                    <Typography variant="caption" color="text.secondary">{shortDate(h.date)}</Typography>
                  </Stack>
                ))}
              </Stack>
            </CardContent>
          </Card>

          {/* ── Charts ──────────────────────────────────────── */}
          <Stack direction={{ xs: "column", lg: "row" }} spacing={2.5} sx={{ mb: 2.5 }}>
            <Card sx={{ flex: 1, minWidth: 0 }}>
              <CardContent>
                <SectionLabel>Cumulative attendance rate</SectionLabel>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  How the running average moved as the term went on.
                </Typography>
                <Box sx={{ height: 230 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={rateChart} margin={{ top: 8, right: 14, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} vertical={false} />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: theme.palette.text.secondary }} axisLine={false} tickLine={false} />
                      <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 11, fill: theme.palette.text.secondary }} axisLine={false} tickLine={false} />
                      <ReTooltip
                        contentStyle={{
                          borderRadius: 10, border: `1px solid ${theme.palette.divider}`,
                          background: theme.palette.background.paper, fontSize: "0.8rem",
                        }}
                        formatter={(v) => [`${v}%`, "Cumulative"]}
                      />
                      <ReferenceLine
                        y={data.required}
                        stroke={CHART.thresholdLine}
                        strokeDasharray="5 4"
                        label={{
                          value: `${data.required}% requirement`, position: "insideBottomRight",
                          fontSize: 11, fill: theme.palette.text.secondary,
                        }}
                      />
                      <Line
                        isAnimationActive={false}
                        type="monotone"
                        dataKey="rate"
                        stroke={CHART.primarySeries}
                        strokeWidth={2}
                        dot={{ r: 3, strokeWidth: 2, fill: theme.palette.background.paper }}
                        activeDot={{ r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>

            <Card sx={{ flex: 1, minWidth: 0 }}>
              <CardContent>
                <SectionLabel>Ink measured in the signature cell</SectionLabel>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  The evidence behind each decision, against the {threshold.toFixed(2)}% threshold.
                </Typography>
                <Box sx={{ height: 230 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={inkChart} margin={{ top: 8, right: 14, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} vertical={false} />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: theme.palette.text.secondary }} axisLine={false} tickLine={false} />
                      <YAxis domain={[0, Math.ceil(maxInk * 1.15)]} unit="%" tick={{ fontSize: 11, fill: theme.palette.text.secondary }} axisLine={false} tickLine={false} />
                      <ReTooltip
                        cursor={{ fill: theme.palette.action.hover }}
                        contentStyle={{
                          borderRadius: 10, border: `1px solid ${theme.palette.divider}`,
                          background: theme.palette.background.paper, fontSize: "0.8rem",
                        }}
                        formatter={(v) => [`${v}%`, "Ink coverage"]}
                      />
                      <ReferenceLine
                        y={threshold}
                        stroke={CHART.thresholdLine}
                        strokeDasharray="5 4"
                        label={{
                          value: "decision threshold", position: "insideTopRight",
                          fontSize: 11, fill: theme.palette.text.secondary,
                        }}
                      />
                      {/* minPointSize keeps a visible stub for a cell that
                          measured 0.00% ink, so an absent session reads as
                          "measured, and empty" rather than as missing data. */}
                      <Bar
                        isAnimationActive={false}
                        dataKey="ink"
                        radius={[4, 4, 0, 0]}
                        barSize={26}
                        minPointSize={3}
                      >
                        {inkChart.map((entry) => (
                          <Cell
                            key={entry.date}
                            fill={entry.status === "PRESENT" ? CHART.presentSeries : CHART.absentSeries}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Stack>

          {/* ── History table ───────────────────────────────── */}
          <Card sx={{ mb: 2.5 }}>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              sx={{ px: 2, py: 1.75, borderBottom: "1px solid", borderColor: "divider" }}
            >
              <Typography variant="subtitle2">Attendance history</Typography>
              <Button
                size="small"
                startIcon={<DrawRoundedIcon sx={{ fontSize: 16 }} />}
                component={RouterLink}
                to={`/signatures/${data.indexNo}`}
              >
                Compare signatures
              </Button>
            </Stack>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Session</TableCell>
                    <TableCell>Signature</TableCell>
                    <TableCell align="right">Ink</TableCell>
                    <TableCell align="center">Decision</TableCell>
                    <TableCell align="right">Running rate</TableCell>
                    <TableCell>Sheet</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.history.map((h) => (
                    <TableRow key={h.date} hover sx={{ cursor: "pointer" }} onClick={() => navigate(`/sessions/${h.date}`)}>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{shortDate(h.date)}</Typography>
                      </TableCell>
                      <TableCell>
                        {h.signatureUrl ? (
                          <Box
                            component="img"
                            src={h.signatureUrl}
                            alt=""
                            loading="lazy"
                            sx={{
                              height: 38, maxWidth: 220, objectFit: "contain", borderRadius: 1,
                              bgcolor: "#fff", border: "1px solid", borderColor: "divider",
                            }}
                          />
                        ) : (
                          <Typography variant="caption" color="text.disabled">no ink in the cell</Typography>
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {inkPercent(h.inkRatio)}
                        </Typography>
                      </TableCell>
                      <TableCell align="center"><AttendanceChip status={h.status} /></TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {h.cumulativeRate}%
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">{h.sheet}</Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>

          {/* ── Batch comparison ────────────────────────────── */}
          <Card>
            <CardContent>
              <SectionLabel>How this student compares with the batch</SectionLabel>
              <Stack spacing={1} sx={{ mt: 1.5 }}>
                {data.classRates.map((c) => {
                  const isSelf = c.indexNo === data.indexNo;
                  return (
                    <Stack
                      key={c.indexNo}
                      direction="row"
                      alignItems="center"
                      spacing={1.5}
                      sx={{ cursor: isSelf ? "default" : "pointer" }}
                      onClick={() => !isSelf && navigate(`/students/${c.indexNo}`)}
                    >
                      <Typography
                        variant="body2"
                        noWrap
                        sx={{ width: 220, flexShrink: 0, fontWeight: isSelf ? 700 : 500 }}
                      >
                        {c.name}
                      </Typography>
                      <Box sx={{ flex: 1, minWidth: 80 }}>
                        <LinearProgress
                          variant="determinate"
                          value={c.rate}
                          sx={{
                            height: isSelf ? 9 : 7,
                            "& .MuiLinearProgress-bar": {
                              bgcolor: isSelf ? CHART.primarySeries : theme.palette.action.selected,
                            },
                          }}
                        />
                      </Box>
                      <Typography
                        variant="body2"
                        sx={{ width: 46, textAlign: "right", fontWeight: isSelf ? 700 : 500, fontVariantNumeric: "tabular-nums" }}
                      >
                        {c.rate}%
                      </Typography>
                    </Stack>
                  );
                })}
              </Stack>
              <Divider sx={{ my: 2 }} />
              <FieldRow label="Batch mean" value={
                <MetaChip label={`${(data.classRates.reduce((a, c) => a + c.rate, 0) / (data.classRates.length || 1)).toFixed(0)}%`} />
              } />
            </CardContent>
          </Card>
        </>
      )}
    </>
  );
}

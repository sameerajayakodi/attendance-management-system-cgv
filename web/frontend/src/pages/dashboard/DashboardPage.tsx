import { Box, Card, CardContent, Divider, Skeleton, Stack, Tooltip, Typography, useTheme } from "@mui/material";
import { useNavigate } from "react-router-dom";
import {
  Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip as ReTooltip, XAxis, YAxis,
} from "recharts";
import EventAvailableRoundedIcon from "@mui/icons-material/EventAvailableRounded";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import PercentRoundedIcon from "@mui/icons-material/PercentRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import { useOverview } from "../../api/queries";
import {
  EmptyState, ErrorState, MetaChip, PageHeader, SectionLabel, StatTile, StatusSquare,
} from "../../components/common";
import { ACCENT, CHART, METRIC, SEMANTIC, initials, avatarColor } from "../../theme/tokens";
import { shortDate } from "../../lib/format";

export default function DashboardPage() {
  const theme = useTheme();
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useOverview();

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;

  const dates = data?.dates ?? [];
  const hasData = (data?.recordCount ?? 0) > 0;

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Attendance read from photographed signing sheets by the CS402.3 image-processing pipeline"
      />

      <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap sx={{ mb: 3 }}>
        <StatTile
          title="Sessions processed"
          value={data?.sessionCount ?? 0}
          icon={<EventAvailableRoundedIcon />}
          color={ACCENT.indigo}
          loading={isLoading}
          hint={dates.length ? `${shortDate(dates[0])} – ${shortDate(dates[dates.length - 1])}` : undefined}
          onClick={() => navigate("/sessions")}
        />
        <StatTile
          title="Students on roll"
          value={data?.studentCount ?? 0}
          icon={<GroupsRoundedIcon />}
          color={ACCENT.teal}
          loading={isLoading}
          hint={`${data?.recordCount ?? 0} signature cells read`}
          onClick={() => navigate("/students")}
        />
        <StatTile
          title="Overall attendance"
          value={data?.overallRate ?? 0}
          unit="%"
          icon={<PercentRoundedIcon />}
          color={SEMANTIC.success}
          loading={isLoading}
          hint={`${data?.presentCount ?? 0} present · ${data?.absentCount ?? 0} absent`}
        />
        <StatTile
          title="Below requirement"
          value={data?.atRisk.length ?? 0}
          icon={<WarningAmberRoundedIcon />}
          color={SEMANTIC.warning}
          loading={isLoading}
          hint={`Under ${METRIC.requiredRate}% attendance`}
          onClick={() => navigate("/students")}
        />
      </Stack>

      {!isLoading && !hasData && (
        <Card>
          <CardContent>
            <EmptyState
              message="No signing sheets have been processed yet"
              hint="Upload a photograph of a signing sheet to read its attendance."
            />
          </CardContent>
        </Card>
      )}

      {hasData && (
        <Stack direction={{ xs: "column", lg: "row" }} spacing={2.5} alignItems="stretch">
          {/* ── Attendance per session ─────────────────────────── */}
          <Card sx={{ flex: 2, minWidth: 0 }}>
            <CardContent>
              <SectionLabel>Attendance per session</SectionLabel>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Share of the roster that signed, against the {METRIC.requiredRate}% requirement.
              </Typography>
              <Box sx={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data!.trend} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
                    <defs>
                      <linearGradient id="rateFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={CHART.areaSeries} stopOpacity={0.28} />
                        <stop offset="100%" stopColor={CHART.areaSeries} stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} vertical={false} />
                    <XAxis
                      dataKey="date"
                      tickFormatter={shortDate}
                      tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      domain={[0, 100]}
                      tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                      axisLine={false}
                      tickLine={false}
                      unit="%"
                    />
                    <ReTooltip
                      contentStyle={{
                        borderRadius: 10,
                        border: `1px solid ${theme.palette.divider}`,
                        background: theme.palette.background.paper,
                        fontSize: "0.8rem",
                      }}
                      labelFormatter={(v) => shortDate(String(v))}
                      formatter={(value, name) =>
                        name === "rate" ? [`${value}%`, "Attendance"] : [value, String(name)]
                      }
                    />
                    <ReferenceLine
                      y={METRIC.requiredRate}
                      stroke={CHART.thresholdLine}
                      strokeDasharray="5 4"
                      label={{
                        value: `${METRIC.requiredRate}% required`,
                        position: "insideBottomRight",
                        fontSize: 11,
                        fill: theme.palette.text.secondary,
                      }}
                    />
                    <Area
                      isAnimationActive={false}
                      type="monotone"
                      dataKey="rate"
                      stroke={CHART.areaSeries}
                      strokeWidth={2}
                      fill="url(#rateFill)"
                      dot={{ r: 3, strokeWidth: 2, fill: theme.palette.background.paper }}
                      activeDot={{ r: 5 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>

          {/* ── Below requirement ──────────────────────────────── */}
          <Card sx={{ flex: 1, minWidth: 260 }}>
            <CardContent>
              <SectionLabel>Below the requirement</SectionLabel>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Students under {METRIC.requiredRate}% across the recorded sessions.
              </Typography>
              {data!.atRisk.length === 0 ? (
                <Stack alignItems="center" sx={{ py: 4 }} spacing={1}>
                  <MetaChip label="Everyone is above the requirement" tone="success" />
                </Stack>
              ) : (
                <Stack divider={<Divider flexItem />}>
                  {data!.atRisk.map((s) => (
                    <Stack
                      key={s.indexNo}
                      direction="row"
                      alignItems="center"
                      spacing={1.5}
                      sx={{ py: 1.25, cursor: "pointer" }}
                      onClick={() => navigate(`/students/${s.indexNo}`)}
                    >
                      <Box
                        sx={{
                          width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
                          display: "grid", placeItems: "center",
                          bgcolor: avatarColor(s.name), color: "#fff", fontSize: 12, fontWeight: 700,
                        }}
                      >
                        {initials(s.name)}
                      </Box>
                      <Box sx={{ minWidth: 0, flex: 1 }}>
                        <Typography variant="body2" noWrap sx={{ fontWeight: 600 }}>{s.name}</Typography>
                        <Typography variant="caption" color="text.secondary">{s.indexNo}</Typography>
                      </Box>
                      <MetaChip label={`${s.rate}%`} tone="warning" />
                    </Stack>
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>
        </Stack>
      )}

      {/* ── Attendance matrix ─────────────────────────────────── */}
      {hasData && (
        <Card sx={{ mt: 2.5 }}>
          <CardContent>
            <SectionLabel>Attendance matrix</SectionLabel>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Every student against every session. Each square carries its own letter, so the reading never
              depends on colour alone.
            </Typography>

            <Box sx={{ overflowX: "auto", pb: 1 }}>
              <Box sx={{ minWidth: 120 + dates.length * 52 + 90 }}>
                {/* header */}
                <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                  <Box sx={{ width: 210, flexShrink: 0 }} />
                  {dates.map((d) => (
                    <Box key={d} sx={{ width: 44, flexShrink: 0, textAlign: "center" }}>
                      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                        {shortDate(d)}
                      </Typography>
                    </Box>
                  ))}
                  <Box sx={{ width: 64, flexShrink: 0, textAlign: "right" }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>Rate</Typography>
                  </Box>
                </Stack>

                {data!.matrix.map((row) => (
                  <Stack
                    key={row.indexNo}
                    direction="row"
                    alignItems="center"
                    spacing={1}
                    sx={{
                      mb: 0.75, borderRadius: 1.5, cursor: "pointer", px: 0.5,
                      "&:hover": { bgcolor: "action.hover" },
                    }}
                    onClick={() => navigate(`/students/${row.indexNo}`)}
                  >
                    <Box sx={{ width: 210, flexShrink: 0, minWidth: 0 }}>
                      <Typography variant="body2" noWrap sx={{ fontWeight: 600 }}>{row.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{row.indexNo}</Typography>
                    </Box>
                    {dates.map((d) => {
                      const cell = row.cells.find((c) => c.date === d);
                      return (
                        <Box key={d} sx={{ width: 44, flexShrink: 0, display: "grid", placeItems: "center" }}>
                          {cell ? (
                            <Tooltip title={`${shortDate(d)} · ${(cell.inkRatio * 100).toFixed(2)}% ink`}>
                              <span><StatusSquare status={cell.status} size={34} /></span>
                            </Tooltip>
                          ) : (
                            <Box sx={{ width: 34, height: 34, borderRadius: 1.5, border: "1px dashed", borderColor: "divider" }} />
                          )}
                        </Box>
                      );
                    })}
                    <Box sx={{ width: 64, flexShrink: 0, textAlign: "right" }}>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{row.rate}%</Typography>
                    </Box>
                  </Stack>
                ))}
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {isLoading && (
        <Card sx={{ mt: 2.5 }}>
          <CardContent>
            <Skeleton height={30} width={220} />
            <Skeleton height={220} />
          </CardContent>
        </Card>
      )}
    </>
  );
}

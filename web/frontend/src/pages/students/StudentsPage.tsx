import { useMemo, useState } from "react";
import {
  Box, Card, CardContent, LinearProgress, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TablePagination, TableRow, Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import { useStudents } from "../../api/queries";
import {
  AttendanceChip, DebouncedSearchInput, EmptyState, ErrorState, MetaChip,
  PageHeader, TableSkeleton,
} from "../../components/common";
import { avatarColor, initials, METRIC, SEMANTIC } from "../../theme/tokens";
import { shortDate } from "../../lib/format";

export default function StudentsPage() {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useStudents();

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const filtered = useMemo(() => {
    const rows = data ?? [];
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((s) => s.name.toLowerCase().includes(q) || s.indexNo.includes(q));
  }, [data, search]);

  const paged = filtered.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);
  const belowRequirement = (data ?? []).filter((s) => s.rate < METRIC.requiredRate).length;

  return (
    <>
      <PageHeader
        title="Students"
        subtitle="Attendance for every student on the roster, across all processed sheets"
      />

      <Card>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1.5}
          alignItems={{ sm: "center" }}
          justifyContent="space-between"
          sx={{ px: 2, py: 1.75, borderBottom: "1px solid", borderColor: "divider" }}
        >
          <DebouncedSearchInput
            value={search}
            onChange={(v) => { setSearch(v); setPage(0); }}
            placeholder="Search by name or index…"
            width={300}
          />
          <Stack direction="row" spacing={1}>
            <MetaChip label={`${filtered.length} student${filtered.length === 1 ? "" : "s"}`} />
            {belowRequirement > 0 && (
              <MetaChip label={`${belowRequirement} below ${METRIC.requiredRate}%`} tone="warning" />
            )}
          </Stack>
        </Stack>

        {error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : isLoading ? (
          <TableSkeleton rows={6} />
        ) : filtered.length === 0 ? (
          <CardContent>
            <EmptyState
              message={search ? "No student matches that search" : "No students have been recorded yet"}
              hint={search ? undefined : "Process a signing sheet and its roster will appear here."}
            />
          </CardContent>
        ) : (
          <>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Student</TableCell>
                    <TableCell align="center">Attended</TableCell>
                    <TableCell sx={{ width: 210 }}>Attendance rate</TableCell>
                    <TableCell align="center">Specimens</TableCell>
                    <TableCell>Last session</TableCell>
                    <TableCell align="right" sx={{ width: 44 }} />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {paged.map((s) => {
                    const short = s.rate < METRIC.requiredRate;
                    return (
                      <TableRow
                        key={s.indexNo}
                        hover
                        sx={{ cursor: "pointer" }}
                        onClick={() => navigate(`/students/${s.indexNo}`)}
                      >
                        <TableCell>
                          <Stack direction="row" spacing={1.5} alignItems="center">
                            <Box
                              sx={{
                                width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
                                display: "grid", placeItems: "center",
                                bgcolor: avatarColor(s.name), color: "#fff", fontSize: 12, fontWeight: 700,
                              }}
                            >
                              {initials(s.name)}
                            </Box>
                            <Box sx={{ minWidth: 0 }}>
                              <Typography variant="body2" sx={{ fontWeight: 600 }} noWrap>
                                {s.title} {s.name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {s.indexNo}{s.batch ? ` · batch ${s.batch}` : ""}
                              </Typography>
                            </Box>
                          </Stack>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2" sx={{ fontVariantNumeric: "tabular-nums" }}>
                            {s.present} / {s.total}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Box sx={{ flex: 1, minWidth: 80 }}>
                              <LinearProgress
                                variant="determinate"
                                value={s.rate}
                                sx={{
                                  "& .MuiLinearProgress-bar": {
                                    bgcolor: short ? SEMANTIC.warning : SEMANTIC.success,
                                  },
                                }}
                              />
                            </Box>
                            <Typography
                              variant="caption"
                              sx={{ fontWeight: 700, minWidth: 38, textAlign: "right", fontVariantNumeric: "tabular-nums" }}
                            >
                              {s.rate}%
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell align="center">
                          <MetaChip label={s.specimens} />
                        </TableCell>
                        <TableCell>
                          {s.lastSession ? (
                            <Stack direction="row" spacing={1} alignItems="center">
                              <Typography variant="body2" color="text.secondary">
                                {shortDate(s.lastSession)}
                              </Typography>
                              {s.lastStatus && <AttendanceChip status={s.lastStatus} withIcon={false} />}
                            </Stack>
                          ) : (
                            <Typography variant="caption" color="text.disabled">—</Typography>
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <ChevronRightRoundedIcon sx={{ fontSize: 18, color: "text.disabled" }} />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>

            <TablePagination
              component="div"
              count={filtered.length}
              page={page}
              onPageChange={(_, p) => setPage(p)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
              rowsPerPageOptions={[10, 25, 50]}
            />
          </>
        )}
      </Card>
    </>
  );
}

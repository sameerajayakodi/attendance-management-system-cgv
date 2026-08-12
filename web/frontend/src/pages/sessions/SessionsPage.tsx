import { useEffect, useMemo, useState } from "react";
import {
  Alert, Box, Card, CardContent, IconButton, LinearProgress, Stack, Table, TableBody,
  TableCell, TableContainer, TableHead, TablePagination, TableRow, Tooltip, Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import { useDeleteSession, useSessions } from "../../api/queries";
import {
  ConfirmDialog, DebouncedSearchInput, EmptyState, ErrorState, MetaChip,
  PageHeader, PrimaryButton, TableSkeleton,
} from "../../components/common";
import { UploadDrawer } from "./UploadDrawer";
import { dateTime, longDate } from "../../lib/format";
import { SEMANTIC } from "../../theme/tokens";

export default function SessionsPage() {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useSessions();
  const remove = useDeleteSession();

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const rows = data ?? [];
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (s) => s.date.includes(q) || s.sourceImage.toLowerCase().includes(q) || s.subjectCode.toLowerCase().includes(q),
    );
  }, [data, search]);

  const paged = filtered.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  useEffect(() => {
    const maxPage = Math.max(0, Math.ceil(filtered.length / rowsPerPage) - 1);
    if (page > maxPage) setPage(maxPage);
  }, [filtered.length, rowsPerPage, page]);

  return (
    <>
      <PageHeader
        title="Signing sheets"
        subtitle="Every photograph the pipeline has read, and the attendance it recovered"
        actions={
          <PrimaryButton startIcon={<AddRoundedIcon />} onClick={() => setUploadOpen(true)}>
            Process a sheet
          </PrimaryButton>
        }
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
            placeholder="Search by date or file name…"
            width={300}
          />
          <Stack direction="row" spacing={1} alignItems="center">
            <MetaChip label={`${filtered.length} session${filtered.length === 1 ? "" : "s"}`} />
          </Stack>
        </Stack>

        {remove.isPending && <LinearProgress />}

        {error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : isLoading ? (
          <TableSkeleton rows={6} />
        ) : filtered.length === 0 ? (
          <CardContent>
            <EmptyState
              message={search ? "No sheet matches that search" : "No signing sheets have been processed yet"}
              hint={search ? undefined : "Upload a photograph and the pipeline will read it."}
              action={
                !search && (
                  <PrimaryButton startIcon={<AddRoundedIcon />} onClick={() => setUploadOpen(true)}>
                    Process a sheet
                  </PrimaryButton>
                )
              }
            />
          </CardContent>
        ) : (
          <>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Session</TableCell>
                    <TableCell>Photograph</TableCell>
                    <TableCell align="center">Present</TableCell>
                    <TableCell align="center">Absent</TableCell>
                    <TableCell sx={{ width: 190 }}>Attendance</TableCell>
                    <TableCell>Processed</TableCell>
                    <TableCell align="right" sx={{ width: 90 }} />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {paged.map((s) => (
                    <TableRow
                      key={s.date}
                      hover
                      sx={{ cursor: "pointer" }}
                      onClick={() => navigate(`/sessions/${s.date}`)}
                    >
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{longDate(s.date)}</Typography>
                        <Typography variant="caption" color="text.secondary">{s.subjectCode}</Typography>
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={1.25} alignItems="center">
                          <Box
                            component="img"
                            src={`${s.sheetUrl}?width=90`}
                            alt=""
                            loading="lazy"
                            sx={{
                              width: 34, height: 44, objectFit: "cover", borderRadius: 1,
                              border: "1px solid", borderColor: "divider", bgcolor: "action.hover",
                            }}
                          />
                          <Typography variant="body2" noWrap sx={{ maxWidth: 210 }}>{s.sourceImage}</Typography>
                        </Stack>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" sx={{ fontWeight: 700, color: SEMANTIC.success }}>
                          {s.present}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography
                          variant="body2"
                          sx={{ fontWeight: 700, color: s.absent ? SEMANTIC.error : "text.disabled" }}
                        >
                          {s.absent}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Box sx={{ flex: 1, minWidth: 70 }}>
                            <LinearProgress
                              variant="determinate"
                              value={s.rate}
                              sx={{
                                "& .MuiLinearProgress-bar": {
                                  bgcolor: s.rate >= 80 ? SEMANTIC.success : SEMANTIC.warning,
                                },
                              }}
                            />
                          </Box>
                          <Typography variant="caption" sx={{ fontWeight: 700, minWidth: 38, textAlign: "right" }}>
                            {s.rate}%
                          </Typography>
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">{dateTime(s.processedAt)}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={0.25} justifyContent="flex-end">
                          <Tooltip title="Remove this session">
                            <IconButton
                              size="small"
                              onClick={(e) => { e.stopPropagation(); setPendingDelete(s.date); }}
                            >
                              <DeleteOutlineRoundedIcon sx={{ fontSize: 17 }} />
                            </IconButton>
                          </Tooltip>
                          <ChevronRightRoundedIcon sx={{ fontSize: 18, color: "text.disabled", alignSelf: "center" }} />
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
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

      {remove.isError && (
        <Alert severity="error" sx={{ mt: 2 }}>{(remove.error as Error).message}</Alert>
      )}

      <UploadDrawer open={uploadOpen} onClose={() => setUploadOpen(false)} />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Remove this session?"
        message={
          `The attendance records and signature specimens for ${pendingDelete ? longDate(pendingDelete) : ""} ` +
          "will be deleted. The photograph itself is not touched, so the sheet can be processed again."
        }
        confirmLabel="Remove"
        loading={remove.isPending}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => {
          if (!pendingDelete) return;
          remove.mutate(pendingDelete, { onSettled: () => setPendingDelete(null) });
        }}
      />
    </>
  );
}

import { useState } from "react";
import {
  Box, Button, Card, CardContent, Dialog, DialogContent, Divider, IconButton, Stack,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tab, Tabs,
  Tooltip, Typography, useTheme,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import ZoomInRoundedIcon from "@mui/icons-material/ZoomInRounded";
import { useSession, useSettings } from "../../api/queries";
import {
  AttendanceChip, ErrorState, MetaChip, PageHeader, PenChip, PhaseChip,
  SectionLabel, TableSkeleton,
} from "../../components/common";
import { dateTime, inkPercent, longDate } from "../../lib/format";
import { SEMANTIC, stagePhase } from "../../theme/tokens";

/** One stage image, captioned with its number, name and what it does. */
function StageCard({ order, slug, name, description, url, onZoom }: {
  order: number; slug: string; name: string; description: string; url: string; onZoom: () => void;
}) {
  const phase = stagePhase(slug);
  return (
    <Card sx={{ flex: "1 1 300px", minWidth: 260, overflow: "hidden" }}>
      <Box
        onClick={onZoom}
        sx={{
          position: "relative", cursor: "zoom-in", bgcolor: "action.hover",
          borderBottom: "1px solid", borderColor: "divider",
          "&:hover .zoom": { opacity: 1 },
        }}
      >
        <Box
          component="img"
          src={url}
          alt={name}
          loading="lazy"
          sx={{ display: "block", width: "100%", height: 210, objectFit: "contain", p: 1 }}
        />
        <Box
          className="zoom"
          sx={{
            position: "absolute", inset: 0, display: "grid", placeItems: "center",
            bgcolor: "rgba(0,0,0,0.35)", color: "#fff", opacity: 0, transition: "opacity .15s ease",
          }}
        >
          <ZoomInRoundedIcon />
        </Box>
        <Box
          sx={{
            position: "absolute", top: 8, left: 8, width: 24, height: 24, borderRadius: "50%",
            display: "grid", placeItems: "center", fontSize: 12, fontWeight: 800,
            bgcolor: (t) => alpha(phase.color, t.palette.mode === "dark" ? 0.9 : 0.92), color: "#fff",
          }}
        >
          {order}
        </Box>
      </Box>
      <CardContent sx={{ py: 1.5 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
          <Typography variant="subtitle2" sx={{ lineHeight: 1.3 }}>{name}</Typography>
          <PhaseChip slug={slug} />
        </Stack>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
          {description}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function SessionDetailPage() {
  const { date } = useParams<{ date: string }>();
  const navigate = useNavigate();
  const theme = useTheme();
  const { data, isLoading, error, refetch } = useSession(date);
  const { data: settings } = useSettings();
  const [tab, setTab] = useState(0);
  const [zoom, setZoom] = useState<{ url: string; title: string } | null>(null);

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;

  const threshold = settings?.inkThreshold ?? 0.0075;

  return (
    <>
      <Button
        startIcon={<ArrowBackRoundedIcon />}
        size="small"
        onClick={() => navigate("/sessions")}
        sx={{ mb: 1.5, ml: -1 }}
      >
        All signing sheets
      </Button>

      <PageHeader
        title={date ? longDate(date) : "Session"}
        subtitle={
          data
            ? `${data.sourceImage} · ${data.subjectCode} · processed ${dateTime(data.processedAt)}`
            : "Loading…"
        }
        actions={
          data ? (
            <Stack direction="row" spacing={1}>
              <MetaChip label={`${data.present} present`} tone="success" />
              {data.absent > 0 && <MetaChip label={`${data.absent} absent`} tone="error" />}
              <MetaChip label={`${data.rate}%`} />
            </Stack>
          ) : undefined
        }
      />

      {data?.warnings?.map((w) => (
        <Card key={w} sx={{ mb: 2, bgcolor: (t) => alpha(t.palette.warning.main, 0.1) }}>
          <CardContent sx={{ py: 1.5 }}>
            <Typography variant="body2">{w}</Typography>
          </CardContent>
        </Card>
      ))}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2.5, borderBottom: "1px solid", borderColor: "divider" }}>
        <Tab label="Attendance" />
        <Tab label={`Image processing${data ? ` (${data.stages.length})` : ""}`} />
        <Tab label="Photograph" />
      </Tabs>

      {/* ── Attendance ──────────────────────────────────────── */}
      {tab === 0 && (
        <Card>
          {isLoading ? (
            <TableSkeleton rows={6} />
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ width: 48 }}>#</TableCell>
                    <TableCell>Student</TableCell>
                    <TableCell>Signature read from the sheet</TableCell>
                    <TableCell align="right">Ink</TableCell>
                    <TableCell align="center">Blobs</TableCell>
                    <TableCell align="center">Pen</TableCell>
                    <TableCell align="center">Decision</TableCell>
                    <TableCell align="right">Conf.</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data!.outcomes.map((o) => (
                    <TableRow key={o.indexNo} hover>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">{o.row}</Typography>
                      </TableCell>
                      <TableCell>
                        <RouterLink
                          to={`/students/${o.indexNo}`}
                          style={{ textDecoration: "none", color: "inherit" }}
                        >
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>{o.name}</Typography>
                          <Typography variant="caption" color="text.secondary">{o.indexNo}</Typography>
                        </RouterLink>
                      </TableCell>
                      <TableCell>
                        {o.signatureUrl ? (
                          <Box
                            component="img"
                            src={o.signatureUrl}
                            alt={`Signature of ${o.name}`}
                            loading="lazy"
                            onClick={() => setZoom({ url: o.signatureUrl!, title: `${o.name} — ${longDate(date)}` })}
                            sx={{
                              height: 42, maxWidth: 240, objectFit: "contain", cursor: "zoom-in",
                              borderRadius: 1, bgcolor: "#fff", border: "1px solid", borderColor: "divider",
                            }}
                          />
                        ) : (
                          <Typography variant="caption" color="text.disabled">no ink in the cell</Typography>
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title={`${o.inkPixels.toLocaleString()} ink pixels · threshold ${inkPercent(threshold)}`}>
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: 700,
                              fontVariantNumeric: "tabular-nums",
                              color: o.inkRatio >= threshold ? SEMANTIC.success : "text.secondary",
                            }}
                          >
                            {inkPercent(o.inkRatio)}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" color="text.secondary">{o.components}</Typography>
                      </TableCell>
                      <TableCell align="center"><PenChip colour={o.penColour} /></TableCell>
                      <TableCell align="center"><AttendanceChip status={o.status} /></TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {o.confidence.toFixed(2)}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          <Divider />
          <CardContent>
            <Typography variant="caption" color="text.secondary">
              <strong>Ink</strong> is the share of the signature cell covered by pen strokes charged to that
              row; a row is marked present when it reaches {inkPercent(threshold)} of the cell and at least{" "}
              {settings?.minInkPixels ?? 110} pixels. <strong>Blobs</strong> is how many connected components
              of ink the row owns — a signature is often more than one stroke.
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* ── Image processing ────────────────────────────────── */}
      {tab === 1 && (
        <>
          <Card sx={{ mb: 2.5 }}>
            <CardContent>
              <SectionLabel>How this sheet was read</SectionLabel>
              <Typography variant="body2" color="text.secondary">
                Every image below is real output written by the pipeline while it processed this photograph —
                the same nine stages the command-line program displays as it runs. Click any image to enlarge.
              </Typography>
              {data?.stageTimings && (
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
                  {data.stageTimings.map((t) => (
                    <MetaChip key={t.order} label={`${t.order}. ${t.name} · ${t.elapsedMs.toFixed(0)} ms`} />
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>

          {isLoading ? (
            <TableSkeleton rows={4} />
          ) : data!.stages.length === 0 ? (
            <Card>
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  No stage images are stored for this session. Process the sheet again to regenerate them.
                </Typography>
              </CardContent>
            </Card>
          ) : (
            <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
              {data!.stages.map((stage) => (
                <StageCard
                  key={stage.slug}
                  {...stage}
                  onZoom={() => setZoom({ url: stage.url + "?width=1800", title: `${stage.order}. ${stage.name}` })}
                />
              ))}
            </Stack>
          )}
        </>
      )}

      {/* ── Photograph ──────────────────────────────────────── */}
      {tab === 2 && data && (
        <Card>
          <CardContent>
            <SectionLabel>The photograph as supplied</SectionLabel>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Unmodified, straight from the phone: hand-held, unevenly lit and slightly rotated. Everything the
              system reports was recovered from this.
            </Typography>
            <Box
              component="img"
              src={`${data.sheetUrl}?width=1400`}
              alt="Signing sheet"
              sx={{
                display: "block", maxWidth: "100%", maxHeight: "78vh", margin: "0 auto",
                borderRadius: 2, border: "1px solid", borderColor: "divider",
              }}
            />
          </CardContent>
        </Card>
      )}

      {/* ── Lightbox ────────────────────────────────────────── */}
      <Dialog open={Boolean(zoom)} onClose={() => setZoom(null)} maxWidth="lg" fullWidth>
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ px: 2.5, py: 1.5, borderBottom: "1px solid", borderColor: "divider" }}
        >
          <Typography variant="subtitle2">{zoom?.title}</Typography>
          <IconButton size="small" onClick={() => setZoom(null)}><CloseRoundedIcon fontSize="small" /></IconButton>
        </Stack>
        <DialogContent sx={{ p: 2, bgcolor: theme.palette.mode === "dark" ? "#0b0b0c" : "#f4f5f7" }}>
          {zoom && (
            <Box
              component="img"
              src={zoom.url}
              alt={zoom.title}
              sx={{ display: "block", width: "100%", maxHeight: "80vh", objectFit: "contain" }}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

import { Box, Card, CardContent, Divider, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { useSettings } from "../../api/queries";
import { FieldRow, MetaChip, PageHeader, PhaseChip, SectionLabel } from "../../components/common";
import { inkPercent } from "../../lib/format";
import { stagePhase } from "../../theme/tokens";

/** The nine stages, with the technique each one applies. */
const STAGES = [
  { slug: "01_acquisition", name: "Acquisition",
    what: "Rescale the photograph to a fixed working width so that every kernel size downstream describes a physical size on the page rather than a pixel count." },
  { slug: "02_greyscale", name: "Greyscale",
    what: "Collapse BGR to luma with the BT.601 weighting — Y = 0.299R + 0.587G + 0.114B. Colour is kept separately, only to name the pen." },
  { slug: "03_illumination_correction", name: "Illumination correction",
    what: "Estimate the shading field by closing the image with an element wider than any glyph, then divide it out. A shadow scales the reflected light, so the correction is a division, not a subtraction." },
  { slug: "04_edge-preserving_denoise", name: "Edge-preserving denoise",
    what: "A bilateral filter suppresses paper texture and JPEG ringing while leaving the thin pen strokes the whole system depends on." },
  { slug: "05_binarisation", name: "Binarisation",
    what: "Adaptive Gaussian thresholding judges every pixel against its own neighbourhood, which is what keeps the faintest signature. Otsu is computed alongside for comparison." },
  { slug: "06_skew_correction", name: "Skew correction",
    what: "The median angle of the long Hough segments gives the page rotation; the image is rectified and the photometric chain re-run. One degree of tilt moves the far end of a rule by a quarter of a row." },
  { slug: "07_rule_extraction", name: "Rule extraction",
    what: "Morphological opening with a long thin horizontal element destroys everything that is not a horizontal run — handwriting included — and the same in the vertical. What survives is the printed grid." },
  { slug: "08_table_reconstruction", name: "Table reconstruction",
    what: "Coverage profiles turn the rule masks back into rows and columns; the roster is the table with the most rows. A rule the detector lost is interpolated back from the form's uniform row pitch." },
  { slug: "09_signature_analysis", name: "Signature analysis",
    what: "The rules are subtracted, the remaining ink is grouped into connected components, and each component is charged to the row that owns most of its pixel mass — so a signature that strays into the row above is still credited correctly." },
];

export default function PipelinePage() {
  const { data } = useSettings();

  return (
    <>
      <PageHeader
        title="Pipeline"
        subtitle="What the system does to a photograph, and the parameters it does it with"
      />

      <Stack direction={{ xs: "column", lg: "row" }} spacing={2.5} alignItems="flex-start">
        <Card sx={{ flex: 2, minWidth: 0 }}>
          <CardContent>
            <SectionLabel>The nine stages</SectionLabel>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
              Each stage is a small object with one responsibility that reads from and writes to a shared
              context. The pipeline is a list of them, so a step can be added, removed or reordered without
              touching the orchestration code.
            </Typography>

            <Stack>
              {STAGES.map((stage, i) => {
                const phase = stagePhase(stage.slug);
                return (
                  <Stack key={stage.slug} direction="row" spacing={2} sx={{ position: "relative", pb: i === STAGES.length - 1 ? 0 : 2.5 }}>
                    {/* rail */}
                    <Box sx={{ position: "relative", width: 30, flexShrink: 0 }}>
                      <Box
                        sx={{
                          width: 30, height: 30, borderRadius: "50%",
                          display: "grid", placeItems: "center", fontWeight: 800, fontSize: 12,
                          bgcolor: (t) => alpha(phase.color, t.palette.mode === "dark" ? 0.22 : 0.12),
                          color: phase.color,
                        }}
                      >
                        {i + 1}
                      </Box>
                      {i < STAGES.length - 1 && (
                        <Box
                          sx={{
                            position: "absolute", left: 14, top: 34, bottom: -10,
                            width: 2, bgcolor: "divider",
                          }}
                        />
                      )}
                    </Box>
                    <Box sx={{ minWidth: 0 }}>
                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                        <Typography variant="subtitle2">{stage.name}</Typography>
                        <PhaseChip slug={stage.slug} />
                      </Stack>
                      <Typography variant="body2" color="text.secondary">{stage.what}</Typography>
                    </Box>
                  </Stack>
                );
              })}
            </Stack>
          </CardContent>
        </Card>

        <Card sx={{ flex: 1, minWidth: 300, position: { lg: "sticky" }, top: 24 }}>
          <CardContent>
            <SectionLabel>Live parameters</SectionLabel>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              Read from the running system, not typed in here. Every one lives in a single frozen settings
              object, so no algorithm carries a literal constant.
            </Typography>

            {data ? (
              <>
                <FieldRow label="Working width" value={`${data.workingWidth} px`} />
                <FieldRow label="Adaptive block" value={`${data.adaptiveBlock} px`} />
                <FieldRow label="Adaptive constant C" value={data.adaptiveC} />
                <FieldRow label="Max skew accepted" value={`${data.maxSkewDegrees}°`} />
                <FieldRow label="Overflow margin" value={`${Math.round(data.overflowRatio * 100)}% of the column`} />
                <Divider sx={{ my: 1.5 }} />
                <FieldRow
                  label="Ink threshold"
                  value={<MetaChip label={inkPercent(data.inkThreshold)} tone="success" />}
                />
                <FieldRow label="Minimum ink pixels" value={data.minInkPixels} />
                <Divider sx={{ my: 1.5 }} />
                <FieldRow label="Signature floor" value={data.mismatchThreshold.toFixed(2)} />
                <FieldRow label="Outlier z-score" value={`−${data.outlierZ}`} />
              </>
            ) : (
              <Typography variant="body2" color="text.secondary">Loading…</Typography>
            )}

            <Box
              sx={{
                mt: 2.5, p: 1.75, borderRadius: 2,
                bgcolor: (t) => alpha(t.palette.success.main, t.palette.mode === "dark" ? 0.12 : 0.08),
              }}
            >
              <Typography variant="caption" color="text.secondary">
                On the five reference sheets the ink threshold sits in a gap seven times wider than it needs to
                be: signed cells hold 3.30–15.97% ink, unsigned cells at most 0.47%. All 30 cells are read
                correctly.
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Stack>
    </>
  );
}

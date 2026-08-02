import { useRef, useState } from "react";
import {
  Alert, Box, Button, Divider, LinearProgress, Stack, TextField, Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { useNavigate } from "react-router-dom";
import UploadFileRoundedIcon from "@mui/icons-material/UploadFileRounded";
import ImageRoundedIcon from "@mui/icons-material/ImageRounded";
import { useProcessSheet, useSessions } from "../../api/queries";
import { DrawerShell, MetaChip, PrimaryButton, SectionLabel } from "../../components/common";
import { longDate, ms } from "../../lib/format";

const ACCEPT = ".jpg,.jpeg,.png,.bmp,.webp,.tif,.tiff";

/** Pull a date out of the file name, exactly as the pipeline itself does. */
function guessDate(name: string): string {
  const stem = name.replace(/\.[^.]+$/, "");
  let m = stem.match(/(\d{4})[.\-_](\d{1,2})[.\-_](\d{1,2})/);
  if (m) return `${m[1]}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}`;
  m = stem.match(/(\d{1,2})[.\-_](\d{1,2})[.\-_](\d{4})/);
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  return "";
}

export function UploadDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const process = useProcessSheet();
  const { data: sessions } = useSessions();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [date, setDate] = useState("");
  const [dragging, setDragging] = useState(false);

  /** The session this upload would overwrite, if the chosen date is taken. */
  const clash = date ? sessions?.find((s) => s.date === date) : undefined;

  const choose = (chosen: File | null) => {
    if (!chosen) return;
    setFile(chosen);
    setDate(guessDate(chosen.name));
    if (preview) URL.revokeObjectURL(preview);
    setPreview(URL.createObjectURL(chosen));
    process.reset();
  };

  const close = () => {
    if (process.isPending) return;
    if (preview) URL.revokeObjectURL(preview);
    setFile(null); setPreview(null); setDate(""); process.reset();
    onClose();
  };

  const submit = () => {
    if (!file) return;
    process.mutate(
      { file, date: date || undefined },
      { onSuccess: (session) => { close(); navigate(`/sessions/${session.date}`); } },
    );
  };

  return (
    <DrawerShell
      open={open}
      onClose={close}
      title="Process a signing sheet"
      subtitle="The pipeline reads the sheet and records who signed"
      width={{ xs: "100%", sm: 480 }}
      footer={
        <>
          <Button onClick={close} disabled={process.isPending}>Cancel</Button>
          <PrimaryButton onClick={submit} disabled={!file || process.isPending}>
            {process.isPending ? "Processing…" : "Process sheet"}
          </PrimaryButton>
        </>
      }
    >
      <SectionLabel>Photograph</SectionLabel>

      <Box
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); choose(e.dataTransfer.files?.[0] ?? null); }}
        onClick={() => inputRef.current?.click()}
        sx={{
          border: "1.5px dashed",
          borderColor: dragging ? "primary.main" : "divider",
          bgcolor: (t) => (dragging ? alpha(t.palette.primary.main, 0.06) : "transparent"),
          borderRadius: 2,
          p: 3,
          textAlign: "center",
          cursor: "pointer",
          transition: "border-color .15s ease, background .15s ease",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          hidden
          onChange={(e) => choose(e.target.files?.[0] ?? null)}
        />
        {preview ? (
          <Stack alignItems="center" spacing={1.25}>
            <Box
              component="img"
              src={preview}
              alt="Selected sheet"
              sx={{ maxHeight: 200, maxWidth: "100%", borderRadius: 1.5, border: "1px solid", borderColor: "divider" }}
            />
            <Stack direction="row" spacing={1} alignItems="center">
              <ImageRoundedIcon sx={{ fontSize: 16, color: "text.secondary" }} />
              <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>{file?.name}</Typography>
              <MetaChip label={`${Math.round((file?.size ?? 0) / 1024)} KB`} />
            </Stack>
            <Typography variant="caption" color="text.secondary">Click to choose a different photograph</Typography>
          </Stack>
        ) : (
          <Stack alignItems="center" spacing={1}>
            <UploadFileRoundedIcon sx={{ fontSize: 34, color: "text.disabled" }} />
            <Typography variant="body2" sx={{ fontWeight: 600 }}>Drop a photograph here, or click to browse</Typography>
            <Typography variant="caption" color="text.secondary">
              JPEG, PNG, BMP, WebP or TIFF — straight from a phone camera is fine
            </Typography>
          </Stack>
        )}
      </Box>

      <Divider sx={{ my: 2.5 }} />

      <SectionLabel>Session date</SectionLabel>
      <TextField
        type="date"
        fullWidth
        value={date}
        onChange={(e) => setDate(e.target.value)}
        slotProps={{ inputLabel: { shrink: true } }}
        helperText={
          file && guessDate(file.name)
            ? "Read from the file name — change it if the sheet is for another day."
            : "Leave empty to take the date from the file name, as the command-line tool does."
        }
      />

      {/*
        A session is keyed by its date, so processing a sheet for a date that
        already exists replaces it. Phone exports make that easy to do by
        accident — every photo taken on one day carries the same date in its
        file name — so the collision is stated before the button is pressed,
        not discovered afterwards.
      */}
      {clash && (
        <Alert severity="warning" sx={{ mt: 1.5 }}>
          <strong>{longDate(clash.date)}</strong> already holds a session read from{" "}
          <em>{clash.sourceImage}</em> ({clash.present}/{clash.total} present). Processing this sheet
          will replace it. Change the date above to keep both.
        </Alert>
      )}

      {process.isPending && (
        <Box sx={{ mt: 2.5 }}>
          <LinearProgress />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
            Running the nine-stage pipeline: greyscale, illumination correction, denoise, binarisation,
            skew correction, rule extraction, table reconstruction, signature analysis.
          </Typography>
        </Box>
      )}

      {process.isError && (
        <Alert severity="error" sx={{ mt: 2.5 }}>
          {(process.error as Error).message}
        </Alert>
      )}

      {process.isSuccess && process.data && (
        <Alert severity="success" sx={{ mt: 2.5 }}>
          Read {process.data.present} of {process.data.total} in {ms(process.data.elapsedMs)}.
        </Alert>
      )}

      <Box sx={{ mt: 3 }}>
        <SectionLabel>What happens next</SectionLabel>
        <Typography variant="body2" color="text.secondary">
          The sheet is rescaled, flat-fielded and binarised; the printed rules are recovered by morphological
          opening and rebuilt into a grid; then every pen stroke is charged to the row that owns most of its
          pixels. Re-processing a date that already exists updates it rather than duplicating it.
        </Typography>
      </Box>
    </DrawerShell>
  );
}

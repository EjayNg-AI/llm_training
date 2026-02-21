---
name: apex-pdf-target-image-removal
description: Detect and remove known APEX targets from born-digital PDFs — logos, cartoons, and Must Do/Challenging badges — whether rendered as image XObjects or vector paths. Use when users want these recurring elements removed while preserving non-target content.
compatibility: Requires python3 with pymupdf, pillow, numpy, and local tesseract OCR binary.
---

# APEX PDF Target Removal

Use this skill to remove these recurring targets from born-digital APEX PDFs:

- APEX logo variants (`APEX MATH TUITION`)
- Cartoons (squid, donkey, panda variants, old master)
- Slanted bordered badges (`Must Do!`, `Challenging!`) — both image XObject and vector-drawn variants

The bundled script removes targets in two phases:

1. **Phase 1 — Image XObject removal** (`delete_image`): Removes logos, cartoons, and badge images embedded as XObjects.
2. **Phase 2 — Vector badge removal** (content stream editing): Removes "Must Do!" and "Challenging!" badges rendered as vector paths (parallelogram borders + letter outlines drawn with `m/l/c/h/f` operators) by excising their BDC/EMC blocks from the page content stream.

## Bundled Assets

Template images are included in:

- `assets/logos/*.png`
- `assets/cartoons/*.png`
- `assets/badges/*.png`

See `references/targets_manifest.md` for the exact file list.

## Bundled Script

- `scripts/remove_apex_targets.py`

## Preconditions

- Input PDF should be born-digital (not fully scanned raster pages).
- Environment has:
  - `python3`
  - `pymupdf` (`fitz`)
  - `Pillow`
  - `numpy`
  - `tesseract`

## Core Workflow

1. Run detection-only first (`--dry-run`) to inspect target xrefs and pages.
2. If detections are correct, run actual removal (output to ` - cleaned.pdf` by default).
3. Re-run dry-run on cleaned output to confirm `target_xrefs_count: 0` and `vector_badge_count: 0`.
4. Perform the mandatory final safety check against baseline (artifact-only baseline for two-skill pipelines; otherwise the input PDF).
5. If legitimate text/diagrams are missing, apply remedies and regenerate output.
6. Sign off only after the mandatory final safety check passes.

### Detection-only

```bash
python3 .agents/skills/apex-pdf-target-image-removal/scripts/remove_apex_targets.py \
  --dry-run \
  --report /tmp/apex_targets_dryrun.json \
  "path/to/input.pdf"
```

### Removal (new output file)

```bash
python3 .agents/skills/apex-pdf-target-image-removal/scripts/remove_apex_targets.py \
  --report /tmp/apex_targets_removed.json \
  "path/to/input.pdf"
```

### In-place removal

```bash
python3 .agents/skills/apex-pdf-target-image-removal/scripts/remove_apex_targets.py \
  --in-place \
  --report /tmp/apex_targets_removed_inplace.json \
  "path/to/input.pdf"
```

### In-place removal (image targets only; skip vector badge stream edits)

Use this when vector-badge removal risks collateral deletion of nearby vector text/diagram content in a specific PDF.

```bash
python3 .agents/skills/apex-pdf-target-image-removal/scripts/remove_apex_targets.py \
  --in-place \
  --skip-vector-badges \
  --report /tmp/apex_targets_removed_inplace_skip_vector.json \
  "path/to/input.pdf"
```

## Example: Vectors Files

```bash
python3 .agents/skills/apex-pdf-target-image-removal/scripts/remove_apex_targets.py \
  --report apex/Emath/vectors_logo_cartoon_badge_removal_report.json \
  "apex/Emath/16a) Vectors Notes Part 1.pdf" \
  "apex/Emath/16b) Vectors Notes Part 2.pdf"
```

## Threshold Controls (Phase 1 Only)

These thresholds control Phase 1 image XObject matching. Phase 2 vector badge detection is signature-based (specific color values + stroke width + path structure) and has no configurable thresholds.

Defaults are precision-biased:

- `--cartoon-threshold 0.72`
- `--badge-threshold 0.85`
- `--logo-threshold 0.94`

Lower thresholds increase recall but increase false-positive risk.

## Vector Badge Detection

Phase 2 identifies vector-drawn badges by their content stream signature. Each badge consists of two consecutive top-level BDC/EMC blocks:

- **Frame block** (tagged `/P`): Contains stroke width `2.25 w`, a closed parallelogram path (`m l l l h S`), and a badge stroke color — blue `0 .439 .753 RG`/`SCN` for "Must Do!" or red `1 0 0 RG`/`SCN` for "Challenging!". Also contains a white fill of the parallelogram and a degenerate image XObject (`Do`).
- **Text block** (tagged `/Span`): The immediately following BDC/EMC block using the same badge color as fill (`rg`/`scn`), containing hundreds of path operators (`m`/`l`/`c`/`h`/`f`) forming letter outlines, with no `BT`/`ET` text operators.

Both blocks are excised together. The JSON report includes `vector_badges` (list of per-page detections with badge type and color) and `vector_badge_count`.

After excision, the script performs a graphics-state cleanup pass to remove orphan `Q` restore operators that would underflow the stack and trigger parser/viewer repair warnings.
It also applies a conservative span-size guard for vector-block removal; oversized candidate ranges are skipped.

## How Matching Works (Phase 1)

The script combines:

- OCR keyword checks (logo and badge words)
- Enhanced badge OCR (saturation mask + rotation)
- Badge color hue detection (HSV blue/red dominance on saturated pixels, fires even when OCR fails on slanted badges)
- Template similarity with rotation augmentation (7 angles for cartoons and badges)
- SMask dual-variant extraction (see below)

Scale tolerance comes from normalized resizing in similarity scoring.
Rotation tolerance comes from explicit rotated candidate checks at 0/±5/±10/±15°.
Degenerate zero-size/invalid image crops are skipped safely so OCR extraction does not abort the run.

### SMask (Transparency) Handling

Many cartoon images use a separate **SMask** (soft mask) XObject for transparency.
`fitz.Pixmap(doc, xref)` returns raw pixels without the mask applied, so
transparent regions appear black. Some bundled templates were captured with a
white background (e.g. donkey) while others were captured raw with a dark
background (e.g. squid).

To handle both cases, the script extracts **two variants** for every image that
has an SMask:

1. **Raw** — pixmap as-is (black in transparent regions).
2. **White-composited** — raw pixels composited onto a white background using
   the SMask via `Image.composite()`.

Both variants are classified independently; the one with the stronger detection
(higher max similarity score) is kept. Images without an SMask go through a
single classification pass as before.

## Fused Image Protection (Phase 1 Only)

If a Phase 1 detected target lives inside an oversized composite image (both width and height exceed 1.5× the expected standalone maximum for its family), the script marks it as `fused_suspect` and **skips removal** by default to avoid destroying non-target content.

Use `--force-remove-fused` to override this safety check when you are certain the fused image is safe to remove.

## Safety Rules

- Phase 1 removes only matched image XObjects; Phase 2 removes only BDC/EMC blocks matching the badge signature.
- Phase 2 also sanitizes leftover graphics-state restore operators (`Q`) that would otherwise underflow after stream edits.
- Use `--skip-vector-badges` for files where vector stream edits cause collateral removal; this keeps Phase 1 image-target removal only.
- The mandatory final safety check is required before delivery.
- For two-skill pipelines (`pdf-artifact-removal` then APEX target removal), keep an artifact-only baseline file and diff against the final cleaned file before sign-off.
- Keep originals unless user explicitly requests in-place.
- Always emit and review JSON report for page/xref traceability.
- Fused composite images are skipped by default (see above).

## Known Limits

- If a target image is baked into a full-page scan, object-level removal is not possible.
- Fused composites (target + non-target in one XObject) are detected and skipped by default; use `--force-remove-fused` to override at your own risk.
- Phase 2 vector badge detection relies on exact RGB color values (`0 .439 .753` for blue, `1 0 0` for red), stroke width `2.25`, and BDC/EMC structure tags. If badge styling changes in future APEX materials, the signatures may need updating.
- Vector badges inlined without BDC/EMC structure tags would not be detected by Phase 2.
- Bundled cartoon templates have inconsistent backgrounds (some white, some dark) due to varying SMask compositing at capture time. The dual-variant extraction (see *SMask Handling* above) compensates for this at runtime. New templates should ideally be captured both ways, but the dual-variant approach handles either.

## Mandatory Final Safety Check (Required Before Sign-off)

Run this at the end of every removal workflow:

1. Re-run `--dry-run` on the cleaned file and review residual detections.
2. Compare cleaned file against its baseline:
   - two-skill pipeline: baseline is the artifact-only output from `$pdf-artifact-removal`
   - standalone pipeline: baseline is the original input PDF
3. Perform visual checks on first/middle/last pages and every changed page; confirm differences are limited to intended APEX targets (logos/cartoons/badges).
4. Confirm no legitimate diagram lines, labels, question text, or answer text were removed.
5. Run a parser check (`pdftotext`, `pikepdf.open`, or PyMuPDF traversal) and confirm no syntax/repair warnings.

If legitimate content was removed, do not sign off. Apply remedies and re-run the mandatory check:

1. Re-run with `--skip-vector-badges` (first remedy when geometry or vector labels are affected).
2. Reduce false positives in image-target removal by increasing thresholds (`--badge-threshold`, `--cartoon-threshold`, `--logo-threshold`) and retry.
3. If `--force-remove-fused` was used, rerun without it so fused composites are protected.
4. Restore affected pages from baseline while keeping safe cleaned pages:

```python
import pikepdf

baseline = pikepdf.Pdf.open("baseline.pdf")
cleaned = pikepdf.Pdf.open("cleaned.pdf")
for page_num in [16, 33]:  # 1-based pages to restore
    cleaned.pages[page_num - 1] = baseline.pages[page_num - 1]
cleaned.save("cleaned-restored.pdf")
```

5. If no safe automatic remedy exists, deliver the safer baseline output and report affected pages explicitly.

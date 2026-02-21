---
name: pdf-artifact-removal
description: Detect and remove watermarks, headers, and footers from born-digital PDFs by targeting tagged /Artifact BDC/EMC blocks in the content stream. Use when users ask to remove watermarks, strip headers/footers, clean up PDF page furniture, or identify repeating overlay elements across PDF pages. Requires pikepdf and pymupdf (fitz).
---

# PDF Artifact Removal

Use this skill to surgically remove watermarks, headers, and footers from born-digital PDFs without affecting body content.

## Typical Invocation Prompts

**Full removal (watermark + header + footer):**

> Remove the watermark, header, and footer from `apex/Amath/25) Probability (IP students only).pdf`. Use the `$pdf-artifact-removal` skill. Save the cleaned output as a new file with " - no watermark" appended to the filename.

**Detection only (no changes):**

> Using the `$pdf-artifact-removal` skill, scan `apex/Amath/25) Probability (IP students only).pdf` and report what tagged artifact blocks (watermarks, headers, footers) are present on each page. Do not remove anything yet.

**Selective removal (e.g., watermark only):**

> Remove only the watermark from `path/to/file.pdf` using the `$pdf-artifact-removal` skill. Leave headers and footers intact.

**Batch processing (multiple files):**

> Remove the watermark, header, and footer from all PDFs in the `apex/Amath/` folder. Use the `$pdf-artifact-removal` skill. Save each cleaned file with " - no watermark" appended.

## Preconditions

- Python packages `pikepdf` and `pymupdf` must be installed.
- The input PDF must be **born-digital** (not scanned). Scanned PDFs require a rasterize-threshold-rebuild approach instead (see `references/scanned-fallback.md`).

## Bundled Script

- `scripts/remove_pdf_artifacts.py`

Use the script for reusable detection/removal runs:

```bash
# Detection only
python3 .agents/skills/pdf-artifact-removal/scripts/remove_pdf_artifacts.py \
  --dry-run \
  --report /tmp/artifact_scan.json \
  "path/to/input.pdf"

# Remove watermark + header + footer (new file by default)
python3 .agents/skills/pdf-artifact-removal/scripts/remove_pdf_artifacts.py \
  --report /tmp/artifact_removed.json \
  "path/to/input.pdf"

# Selective removal (watermark only)
python3 .agents/skills/pdf-artifact-removal/scripts/remove_pdf_artifacts.py \
  --remove Watermark \
  --report /tmp/artifact_removed_watermark_only.json \
  "path/to/input.pdf"
```

## Core Concept

Born-digital PDFs often wrap repeating page furniture inside **tagged `/Artifact` blocks** in the content stream using `BDC`/`EMC` operators:

```
/Artifact <</Subtype /Watermark /Type /Pagination ...>>BDC
q
...drawing commands...
Q
EMC
```

Subtypes include `/Watermark`, `/Header`, and `/Footer`. This skill regex-matches these blocks and removes them from each page's content stream.

## Workflow

### Phase 1: Detection

Before removing anything, always identify what's present.

**1.1 Scan for tagged artifact blocks (pikepdf)**

```python
import pikepdf
import re

pdf = pikepdf.open("input.pdf")
for i, page in enumerate(pdf.pages):
    contents = page.Contents
    if hasattr(contents, "read_bytes"):
        stream = contents.read_bytes().decode("latin-1")
    else:
        stream = "".join(c.read_bytes().decode("latin-1") for c in contents)

    for subtype in ["Watermark", "Header", "Footer"]:
        matches = re.findall(
            rf'/Artifact\s*<<[^>]*/Subtype\s*/{subtype}[^>]*>>', stream
        )
        if matches:
            # Extract BBox from each match
            for m in matches:
                bbox = re.search(r'/BBox\s*\[([^\]]+)\]', m)
                bbox_str = bbox.group(1) if bbox else "N/A"
                print(f"Page {i+1}: {subtype} BBox=[{bbox_str}]")
pdf.close()
```

**1.2 Identify repeating XObjects across pages (pikepdf)**

An image that appears on every page is very likely a watermark.

```python
import pikepdf

pdf = pikepdf.open("input.pdf")
objgen_counts = {}
objgen_info = {}
for page in pdf.pages:
    xobjs = page.Resources.get("/XObject", {})
    for name, xobj in xobjs.items():
        og = getattr(xobj, "objgen", None)
        objgen_counts[og] = objgen_counts.get(og, 0) + 1
        if og not in objgen_info:
            subtype = xobj.get("/Subtype", "N/A")
            w = xobj.get("/Width", "N/A")
            h = xobj.get("/Height", "N/A")
            has_smask = "/SMask" in xobj
            objgen_info[og] = (str(name), subtype, w, h, has_smask)

total = len(pdf.pages)
print(f"Total pages: {total}\n")
for og, count in sorted(objgen_counts.items(), key=lambda x: -x[1]):
    info = objgen_info[og]
    flag = " <-- likely watermark" if count == total else ""
    print(f"objgen={og}: {count}/{total} pages, name={info[0]}, "
          f"subtype={info[1]}, {info[2]}x{info[3]}, smask={info[4]}{flag}")
pdf.close()
```

**1.3 Get bounding boxes and visually confirm (PyMuPDF)**

```python
import fitz

doc = fitz.open("input.pdf")
page = doc[0]
for img in page.get_images(full=True):
    xref = img[0]
    rects = page.get_image_rects(xref)
    print(f"xref={xref} (w={img[2]}, h={img[3]}): {rects}")

    # Extract image for visual confirmation
    img_data = doc.extract_image(xref)
    with open(f"/tmp/xref_{xref}.{img_data['ext']}", "wb") as f:
        f.write(img_data["image"])
    print(f"  -> saved /tmp/xref_{xref}.{img_data['ext']}")
doc.close()
```

**1.4 Inspect the content stream placement (pikepdf)**

Check the transform matrix and graphics state for the suspected watermark:

```python
import pikepdf

pdf = pikepdf.open("input.pdf")
page = pdf.pages[0]
stream = page.Contents.read_bytes().decode("latin-1")

# Print lines around /Im0 Do (or whatever the watermark's resource name is)
lines = stream.split("\n")
for i, line in enumerate(lines):
    if "/Im0" in line:
        start = max(0, i - 10)
        end = min(len(lines), i + 3)
        for j in range(start, end):
            print(f"  [{j}] {lines[j]}")
pdf.close()
```

### Phase 2: Removal

**2.1 Remove tagged artifact blocks from content streams**

```python
import pikepdf
import re

pdf = pikepdf.open("input.pdf")

for i, page in enumerate(pdf.pages):
    contents = page.Contents
    streams = [contents] if hasattr(contents, "read_bytes") else list(contents)

    for stream in streams:
        data = stream.read_bytes().decode("latin-1")
        original = data

        # Remove watermarks
        data = re.sub(
            r'/Artifact\s*<<[^>]*?/Subtype\s*/Watermark[^>]*?>>BDC\s.*?EMC\s*',
            '', data, flags=re.DOTALL
        )
        # Remove headers
        data = re.sub(
            r'/Artifact\s*<<[^>]*?/Subtype\s*/Header[^>]*?>>BDC\s.*?EMC\s*',
            '', data, flags=re.DOTALL
        )
        # Remove footers
        data = re.sub(
            r'/Artifact\s*<<[^>]*?/Subtype\s*/Footer[^>]*?>>BDC\s.*?EMC\s*',
            '', data, flags=re.DOTALL
        )

        if data != original:
            print(f"Page {i+1}: cleaned")
            stream.write(data.encode("latin-1"))

pdf.save("output.pdf")
pdf.close()
```

**2.2 Clean up orphaned XObject references**

After removing artifact blocks, remove the now-unused XObject entries from each page's resources. Only remove entries whose referenced object you've confirmed belongs to the removed artifact.

```python
# Example: watermark was /Im0 referencing objgen (689, 0)
xobjs = page.Resources.get("/XObject", {})
if "/Im0" in xobjs:
    del xobjs["/Im0"]
```

### Phase 3: Mandatory Final Safety Check (Required Before Sign-off)

This phase is mandatory. The workflow is not complete until this check passes.

1. Visually inspect first/middle/last pages plus any page with non-zero removals in the JSON report.
2. Confirm that removed content is limited to intended artifact zones (header/footer/watermark regions only).
3. Confirm no legitimate text, diagram lines, labels, or question content disappeared.
4. Keep this output as an artifact-only baseline when chaining to `$apex-pdf-target-image-removal`.

If legitimate content was removed, do not sign off. Apply one or more remedies and re-check:

1. Narrow removal scope with `--remove` (for example, remove only `Header Footer` or only `Watermark`).
2. Re-run with `--dry-run` and inspect per-page detections; if only some pages are problematic, split the PDF and process safe page ranges only.
3. For untagged cases, use the header/footer obscure fallback with tighter rectangles; do not obscure central watermarks that overlap body content.
4. If safe removal is not possible, keep original content and report the limitation with affected pages.

## Execution Rules

- **Always detect before removing.** Run Phase 1 first and confirm findings before Phase 2.
- **Phase 3 is mandatory.** Never finalize output without the mandatory final safety check.
- **Target specific subtypes.** Only remove `/Watermark`, `/Header`, or `/Footer` as requested. Do not remove all artifact blocks indiscriminately.
- **Handle multiple content streams.** Some pages have a single `Contents` stream, others have an array. Always check with `hasattr(contents, "read_bytes")`.
- **Use `allow_overwriting_input=True`** if saving back to the same file with pikepdf.
- **Preserve the original.** Save to a new filename (e.g., `input - no watermark.pdf`) unless explicitly asked to overwrite.
- **Page 1 may differ.** Cover pages often have different header/footer structure (e.g., no footer, larger logo instead of small header logo). Verify per-page counts in Phase 1.

## Fallback Rules When BDC/EMC Tagging Is Absent

Not all PDFs have tagged artifact blocks. When the primary regex-based removal cannot be used, the following rules apply:

### Watermarks: Do NOT obscure — leave alone if untagged

Watermarks (like the Apex "APEX MATH TUITION" slanted text) are positioned **over the body content area** of the page. They visually overlap with text, diagrams, and other legitimate elements. If BDC/EMC-based removal is not possible (no tagged blocks found), **do not attempt to cover or obscure the watermark** — any opaque overlay placed over the watermark region would also hide the body content underneath. In this case, leave the watermark in place and inform the user that clean removal is not possible for this PDF.

### Headers and Footers: Obscure as fallback

Headers and footers occupy **distinct page regions** (top margin and bottom margin respectively) that do **not visually intersect** with body content. If BDC/EMC-based removal is not possible, headers and footers **can** be obscured by overlaying an opaque element (e.g., a white rectangle or white PNG image) over their bounding box region.

**Fallback: overlay white rectangles using PyMuPDF:**

```python
import fitz

doc = fitz.open("input.pdf")

# Bounding boxes (adjust per PDF — these are Apex Math Tuition values)
header_rect = fitz.Rect(0, 770, 600, 842)   # top strip covering header region
footer_rect = fitz.Rect(0, 0, 600, 75)      # bottom strip covering footer region

for i, page in enumerate(doc):
    # Header: page 1 has rule only; pages 2+ have rule + logo
    page.draw_rect(header_rect, color=None, fill=(1, 1, 1))  # white fill, no border

    # Footer: pages 2+ only (page 1 typically has no footer)
    if i > 0:
        page.draw_rect(footer_rect, color=None, fill=(1, 1, 1))

doc.save("output.pdf")
doc.close()
```

**Important:** When using the obscure fallback, verify that the white rectangle does not overlap with any body content. Render a page to an image before and after to visually confirm.

### Additional Example (Implementation Refinement, Not Workflow Replacement)

In one specific Apex file (`apex/Amath/O-Level Amath reminders (Sec 3).pdf`), the central watermark was untagged (no `/Artifact ... /Subtype /Watermark` block), but it was still removable because it was drawn as a repeating image XObject:

- The watermark image appeared on every page as `/Im1`.
- Each page content stream painted it with `/Im1 Do`.
- Removing the `/Im1 Do` paint commands and pruning `/Im1` from page `/Resources /XObject` removed the central watermark cleanly for that file.

This is an **implementation refinement** for a particular PDF structure. It is **not** a replacement for any part of the existing workflow above.

```python
import pikepdf
import re

pdf = pikepdf.open("input.pdf")
for page in pdf.pages:
    contents = page.get("/Contents", None)
    if contents is None:
        continue
    streams = [contents] if hasattr(contents, "read_bytes") else list(contents)

    for stream in streams:
        data = stream.read_bytes().decode("latin-1", errors="ignore")
        new_data, _ = re.subn(r'(?m)^\s*/Im1\s+Do\s*$\n?', '', data)
        if new_data != data:
            stream.write(new_data.encode("latin-1"))

    xobjs = page.Resources.get("/XObject", {})
    if "/Im1" in xobjs:
        del xobjs["/Im1"]

pdf.save("output.pdf")
pdf.close()
```

When using this refinement, perform rigorous checks to ensure legitimate page content is not modified:

1. Confirm the target XObject is truly watermark-only (repeating placement, dimensions, and visual extraction checks).
2. Verify removal scope is limited to intended paint commands (e.g., `/Im1 Do`) and matching `/XObject` entries.
3. Compare first/middle/last pages before and after; include pages with unusual layouts (cover/appendix pages).
4. Confirm body text, equations, diagrams, and tables remain intact after removal.
5. Re-run content-stream/resource checks to verify only intended references were removed.

## Limitations

- Only works for born-digital PDFs with tagged artifact blocks (primary method).
- If the PDF lacks BDC/EMC tagging: watermarks must be left alone; headers/footers can be obscured with white overlays (see Fallback Rules above).
- The regex approach assumes well-formed, non-nested artifact blocks. Deeply nested or malformed streams may require manual inspection.

## Worked Example: Apex Math Tuition PDFs

This section documents the exact artifact structure found in Apex Math Tuition PDFs (e.g., `apex/Amath/25) Probability (IP students only).pdf`, 17 pages). Use this as a reference when processing any Apex Math Tuition PDF — the structure is consistent across their documents.

**Reference images:** See `references/apex-math-tuition/` for visual samples:
- `apex-header.png` — Header: bordered "APEXMATH TUITION" logo box (left-aligned) followed by a horizontal rule spanning the page width.
- `apex-footer.png` — Footer: two horizontal rules (blue) with copyright text ("Unauthorized copying and distribution prohibited. Copyright © www.tuitionmath.com. All rights reserved") and right-aligned page number between them.

### Artifact Inventory

| Element | Tag in Content Stream | XObject | Object Details | Appears On |
|---|---|---|---|---|
| **Watermark** (slanted "APEX MATH TUITION" text, centered) | `/Artifact <</BBox [72.15 236.9001 523.1499 617.4] /Subtype /Watermark /Type /Pagination >>BDC` | `/Im0` → objgen `(689, 0)` | 710×599 JPEG with `/SMask` at objgen `(696, 0)` for transparency. Graphics state `/GS0` has CA=1.0, ca=1.0 (opacity via SMask only). Transform: `450.9999 0 0 380.4999 72.15 236.9 cm` (scale+translate, no rotation — the slant is baked into the JPEG). | All 17 pages |
| **Header — horizontal rule** | `/Artifact <</BBox [70.2497 791.75 525.2497 805.836] /Subtype /Header /Type /Pagination >>BDC` | None (vector drawing: colored rectangles via `re`/`f` operators) | Thin horizontal line near top of page | Page 1: yes (1 header block). Pages 2-17: yes |
| **Header — logo box** | `/Artifact <</BBox [69.3001 775.5501 148.5501 810.8501] /Subtype /Header /Type /Pagination >>BDC` | `/Im1` → objgen `(86, 0)` | 183×73 image (APEXMATH TUITION logo in bordered box) | Pages 2-17 only (not page 1) |
| **Footer** | `/Artifact <</BBox [70.2497 38.223 525.966 72.25] /Subtype /Footer /Type /Pagination >>BDC` | None (text operators + colored rectangles) | Copyright text, page number, two blue horizontal rules | Pages 2-17 only (not page 1) |

### Page 1 vs Pages 2-17

- **Page 1 (cover):** 1 watermark + 1 header (rule only). No logo header block, no footer.
- **Pages 2-17:** 1 watermark + 2 header blocks (rule + logo) + 1 footer block.

### Detection Commands (Apex-Specific)

```python
import pikepdf
import re

pdf = pikepdf.open("apex/Amath/25) Probability (IP students only).pdf")

for i, page in enumerate(pdf.pages):
    contents = page.Contents
    if hasattr(contents, "read_bytes"):
        stream = contents.read_bytes().decode("latin-1")
    else:
        stream = "".join(c.read_bytes().decode("latin-1") for c in contents)

    wm = len(re.findall(r'/Artifact\s*<<[^>]*/Subtype\s*/Watermark[^>]*>>', stream))
    hd = len(re.findall(r'/Artifact\s*<<[^>]*/Subtype\s*/Header[^>]*>>', stream))
    ft = len(re.findall(r'/Artifact\s*<<[^>]*/Subtype\s*/Footer[^>]*>>', stream))
    print(f"Page {i+1}: {wm} watermark(s), {hd} header(s), {ft} footer(s)")

pdf.close()
# Expected output:
# Page 1: 1 watermark(s), 1 header(s), 0 footer(s)
# Page 2: 1 watermark(s), 2 header(s), 1 footer(s)
# ...
# Page 17: 1 watermark(s), 2 header(s), 1 footer(s)
```

### Full Removal (Apex-Specific)

Removes all three artifact types and cleans up orphaned XObject references:

```python
import pikepdf
import re

pdf = pikepdf.open("apex/Amath/25) Probability (IP students only).pdf")

for i, page in enumerate(pdf.pages):
    contents = page.Contents
    streams = [contents] if hasattr(contents, "read_bytes") else list(contents)

    for stream in streams:
        data = stream.read_bytes().decode("latin-1")
        original = data

        # Remove watermark blocks
        data = re.sub(
            r'/Artifact\s*<<[^>]*?/Subtype\s*/Watermark[^>]*?>>BDC\s.*?EMC\s*',
            '', data, flags=re.DOTALL
        )
        # Remove header blocks
        data = re.sub(
            r'/Artifact\s*<<[^>]*?/Subtype\s*/Header[^>]*?>>BDC\s.*?EMC\s*',
            '', data, flags=re.DOTALL
        )
        # Remove footer blocks
        data = re.sub(
            r'/Artifact\s*<<[^>]*?/Subtype\s*/Footer[^>]*?>>BDC\s.*?EMC\s*',
            '', data, flags=re.DOTALL
        )

        if data != original:
            stream.write(data.encode("latin-1"))

    # Clean up orphaned XObject references
    xobjs = page.Resources.get("/XObject", {})
    # /Im0 is the watermark image (objgen 689,0) — present on all pages
    if "/Im0" in xobjs:
        del xobjs["/Im0"]
    # /Im1 is the header logo image (objgen 86,0) — present on pages 2-17
    if i > 0 and "/Im1" in xobjs:
        obj = xobjs["/Im1"]
        if getattr(obj, "objgen", None) == (86, 0):
            del xobjs["/Im1"]

pdf.save("apex/Amath/25) Probability (IP students only) - no watermark.pdf")
pdf.close()
```

### Verification Checklist (Apex)

1. Open output PDF. Confirm watermark text ("APEX MATH TUITION") is gone from all 17 pages.
2. Confirm header logo box and horizontal rule are gone from pages 2-17; horizontal rule gone from page 1.
3. Confirm footer (copyright text, page numbers, blue rules) is gone from pages 2-17.
4. Confirm all body content (math problems, diagrams, text) is intact and unchanged.
5. File size should decrease (watermark JPEG + SMask removed).

## Reference Files

- `references/scanned-fallback.md` — Alternative approach for scanned PDFs using OpenCV thresholding.
- `references/pdf-manipulation-cheatsheet.md` — Comprehensive PDF manipulation reference.
- `references/apex-math-tuition/apex-header.png` — Visual reference for Apex Math Tuition header (logo box + horizontal rule).
- `references/apex-math-tuition/apex-footer.png` — Visual reference for Apex Math Tuition footer (copyright text + page number + blue rules).

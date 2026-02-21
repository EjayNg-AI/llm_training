#!/usr/bin/env python3
"""
Remove known APEX targets from born-digital PDFs in two phases:

Phase 1 — Image XObject removal:
  Detect APEX logos, cartoon characters, and Must Do! / Challenging badge images
  via OCR + template similarity with rotation augmentation, then remove with
  PyMuPDF delete_image.

Phase 2 — Vector badge removal:
  Detect "Must Do!" and "Challenging!" badges rendered as vector paths
  (parallelogram borders + letter outlines) by matching their content-stream
  BDC/EMC block signatures (specific RGB stroke color + 2.25 w + closed path),
  then excise the matched blocks.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import fitz
import numpy as np
from PIL import Image


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSET_ROOT = SKILL_ROOT / "assets"

# Maximum expected standalone dimensions per family
MAX_STANDALONE = {
    "logo": (620, 260),
    "badge": (420, 150),
    "cartoon": (400, 400),
}
FUSED_SIZE_FACTOR = 1.5


def pixmap_to_pil(pix: fitz.Pixmap) -> Image.Image:
    if pix.n >= 5:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    if pix.n == 4:
        img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples).convert("RGB")
    elif pix.n == 3:
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    else:
        img = Image.frombytes("L", [pix.width, pix.height], pix.samples).convert("RGB")
    return img


def norm_corr(img_a: Image.Image, img_b: Image.Image, size: Tuple[int, int]) -> float:
    a = np.asarray(img_a.convert("L").resize(size, Image.Resampling.BILINEAR), dtype=float)
    b = np.asarray(img_b.convert("L").resize(size, Image.Resampling.BILINEAR), dtype=float)
    a = (a - a.mean()) / (a.std() + 1e-9)
    b = (b - b.mean()) / (b.std() + 1e-9)
    return float((a * b).mean())


def ocr_text(img: Image.Image, psm: str = "6") -> str:
    if img.width <= 0 or img.height <= 0:
        return ""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tmp = Path(tf.name)
    try:
        img.save(tmp)
    except Exception:
        tmp.unlink(missing_ok=True)
        return ""
    try:
        result = subprocess.run(
            ["tesseract", str(tmp), "stdout", "--psm", psm],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        text = result.stdout or ""
    finally:
        tmp.unlink(missing_ok=True)
    return " ".join(text.upper().split())


def badge_ocr_enhanced(img: Image.Image) -> str:
    arr = np.asarray(img.convert("RGB"), dtype=np.uint8).astype(np.float32) / 255.0
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    sat = (mx - mn) / (mx + 1e-9)
    mask = sat > 0.12

    bw = np.full(mask.shape, 255, dtype=np.uint8)
    bw[mask] = 0
    bw_img = Image.fromarray(bw, "L")

    texts: List[str] = []
    for ang in (0, -15, -10, -5, 5, 10, 15):
        rotated = bw_img.rotate(ang, expand=True, fillcolor=255)
        txt = ocr_text(rotated, psm="6")
        if txt:
            texts.append(txt)
    return " | ".join(dict.fromkeys(texts))


def detect_badge_by_color(img: Image.Image) -> str | None:
    """Return 'blue' or 'red' if the image has a dominant badge hue, else None."""
    if img.width <= 0 or img.height <= 0:
        return None
    arr = np.asarray(img.convert("RGB"), dtype=np.uint8).astype(np.float32) / 255.0
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    sat = (mx - mn) / (mx + 1e-9)
    sat_mask = sat > 0.12
    sat_ratio = float(sat_mask.mean())
    if sat_ratio < 0.03:
        return None

    # Compute hue in degrees for saturated pixels
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    delta = mx - mn + 1e-9
    hue = np.zeros_like(mx)
    # Red dominant
    r_mask = (mx == r) & sat_mask
    hue[r_mask] = (60.0 * ((g[r_mask] - b[r_mask]) / delta[r_mask]) % 360)
    # Green dominant
    g_mask = (mx == g) & sat_mask & ~r_mask
    hue[g_mask] = 60.0 * ((b[g_mask] - r[g_mask]) / delta[g_mask]) + 120.0
    # Blue dominant
    b_mask = sat_mask & ~r_mask & ~g_mask
    hue[b_mask] = 60.0 * ((r[b_mask] - g[b_mask]) / delta[b_mask]) + 240.0
    hue = hue % 360

    sat_pixels = hue[sat_mask]
    n_sat = len(sat_pixels)
    if n_sat == 0:
        return None

    blue_count = int(((sat_pixels >= 190) & (sat_pixels <= 250)).sum())
    red_count = int(((sat_pixels <= 25) | (sat_pixels >= 335)).sum())

    if blue_count / n_sat >= 0.60:
        return "blue"
    if red_count / n_sat >= 0.60:
        return "red"
    return None


def load_templates(folder: Path) -> List[Tuple[str, Image.Image]]:
    templates: List[Tuple[str, Image.Image]] = []
    for p in sorted(folder.glob("*.png")):
        try:
            img = Image.open(p).convert("RGB")
        except Exception:
            continue
        templates.append((p.name, img))
    return templates


def best_similarity(
    img: Image.Image,
    templates: Sequence[Tuple[str, Image.Image]],
    size: Tuple[int, int],
    angles: Sequence[int],
) -> Tuple[float, str]:
    best_score = -1.0
    best_name = ""
    for ang in angles:
        cand = img.rotate(ang, expand=True, fillcolor=(255, 255, 255))
        for name, timg in templates:
            score = norm_corr(cand, timg, size=size)
            if score > best_score:
                best_score = score
                best_name = name
    return best_score, best_name


def classify_candidate(
    img: Image.Image,
    width: int,
    height: int,
    cartoon_templates: Sequence[Tuple[str, Image.Image]],
    badge_templates: Sequence[Tuple[str, Image.Image]],
    logo_templates: Sequence[Tuple[str, Image.Image]],
    cartoon_threshold: float,
    badge_threshold: float,
    logo_threshold: float,
) -> Dict[str, object]:
    if img.width <= 0 or img.height <= 0:
        return {
            "target": False,
            "reasons": [],
            "ocr_text": "",
            "badge_color": None,
            "scores": {"cartoon": 0.0, "badge": 0.0, "logo": 0.0},
            "matches": {"cartoon": "", "badge": "", "logo": ""},
        }

    reasons: List[str] = []

    base_ocr = ocr_text(img)
    text = base_ocr

    arr = np.asarray(img.convert("RGB"), dtype=np.uint8).astype(np.float32) / 255.0
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    sat = (mx - mn) / (mx + 1e-9)
    color_ratio = float((sat > 0.15).mean())

    likely_badge_shape = 60 <= width <= 420 and 14 <= height <= 150 and (width / max(height, 1)) >= 1.6
    badge_color: str | None = None
    if likely_badge_shape and color_ratio >= 0.04:
        badge_color = detect_badge_by_color(img)
        enh = badge_ocr_enhanced(img)
        if enh:
            text = f"{base_ocr} | {enh}".strip(" |")

    clean = re.sub(r"[^A-Z0-9 ]+", " ", text)
    words = [w for w in clean.split() if w]

    # OCR logo rules (precision biased)
    has_apex_tokens = "APEX" in clean and ("MATH" in clean or "TUITION" in clean)
    logo_vocab = {"APEX", "APEXMATH", "MATH", "TUITION"}
    non_logo_words = [w for w in words if w not in logo_vocab and not w.startswith("APEX")]
    apex_wordy_ok = len(words) <= 6 and len(non_logo_words) <= 1
    apex_size_ok = (width <= 320 and height <= 170) or (width <= 620 and height <= 260 and width / max(height, 1) >= 1.8)
    if has_apex_tokens and apex_wordy_ok and apex_size_ok:
        reasons.append("ocr_apex_logo")

    # OCR badge rules
    if "MUST" in clean and "DO" in clean and width <= 280 and height <= 120:
        reasons.append("ocr_must_do_badge")
    if "CHALLENG" in clean and width <= 400 and height <= 140:
        reasons.append("ocr_challenging_badge")

    cartoon_score, cartoon_match = best_similarity(
        img,
        cartoon_templates,
        size=(192, 192),
        angles=(0, -5, 5, -10, 10, -15, 15),
    )
    badge_score, badge_match = best_similarity(
        img,
        badge_templates,
        size=(240, 90),
        angles=(0, -15, -10, -5, 5, 10, 15),
    )
    logo_score, logo_match = best_similarity(
        img,
        logo_templates,
        size=(220, 90),
        angles=(0, -8, 8),
    )

    if cartoon_score >= cartoon_threshold:
        reasons.append(f"cartoon_similarity:{cartoon_score:.3f}:{cartoon_match}")
    if badge_score >= badge_threshold:
        reasons.append(f"badge_similarity:{badge_score:.3f}:{badge_match}")
    if logo_score >= logo_threshold:
        reasons.append(f"logo_similarity:{logo_score:.3f}:{logo_match}")

    # Color-confirmed badge: fires even when OCR fails (slanted badges)
    if badge_color is not None and badge_score >= 0.72:
        color_label = "must_do" if badge_color == "blue" else "challenging"
        reasons.append(f"color_badge_{color_label}")

    return {
        "target": bool(reasons),
        "reasons": reasons,
        "ocr_text": text,
        "badge_color": badge_color,
        "scores": {
            "cartoon": cartoon_score,
            "badge": badge_score,
            "logo": logo_score,
        },
        "matches": {
            "cartoon": cartoon_match,
            "badge": badge_match,
            "logo": logo_match,
        },
    }


def primary_family(reasons: List[str]) -> str | None:
    """Return the dominant detection family from a list of reasons."""
    for family in ("logo", "badge", "cartoon"):
        if any(family in r for r in reasons):
            return family
    return None


def is_fused_suspect(width: int, height: int, family: str) -> bool:
    """Return True if the image dimensions exceed expected standalone size."""
    max_w, max_h = MAX_STANDALONE.get(family, (620, 400))
    return width > max_w * FUSED_SIZE_FACTOR and height > max_h * FUSED_SIZE_FACTOR


# ── Vector badge removal ──────────────────────────────────────────────

# Badge stroke/fill color RGB signatures
_BADGE_COLORS: Dict[str, str] = {
    "blue": r"(?<!\d)0\s+0?\.439\s+0?\.753",  # "Must Do!" (handles both 0.439 and .439)
    "red": r"(?<!\d)1\s+0\s+0",  # "Challenging!"
}
# Safety cap for vector-badge excision span. Oversized ranges are skipped to
# avoid removing unrelated vector content that may share the same color/path
# characteristics on some pages.
MAX_VECTOR_BADGE_REMOVAL_CHARS = 5000


def _find_top_level_bdc_blocks(stream: str) -> List[Tuple[int, int]]:
    """Return (start, end) char offsets of top-level BDC/BMC…EMC blocks.

    Works on single-line streams produced by ``page.clean_contents()``.
    Handles inline ``<<dict>>`` syntax in BDC tags.
    """
    # Regex for BDC/BMC: /Tag <<dict>> BDC  or  /Tag BDC  (dict optional)
    _bdc_re = re.compile(r"/\w+\s*(?:<<[^>]*>>)?\s*(?:BDC|BMC)")
    _emc_re = re.compile(r"\bEMC\b")

    # Build an ordered token list of (position, end, type)
    tokens: List[Tuple[int, int, str]] = []
    for m in _bdc_re.finditer(stream):
        tokens.append((m.start(), m.end(), "BDC"))
    for m in _emc_re.finditer(stream):
        tokens.append((m.start(), m.end(), "EMC"))
    tokens.sort(key=lambda x: x[0])

    blocks: List[Tuple[int, int]] = []
    depth = 0
    block_start = 0
    for start, end, ttype in tokens:
        if ttype == "BDC":
            if depth == 0:
                block_start = start
            depth += 1
        elif ttype == "EMC":
            if depth > 0:
                depth -= 1
                if depth == 0:
                    blocks.append((block_start, end))
    return blocks


def _is_badge_frame(content: str) -> str | None:
    """Return badge color name if *content* is a badge frame block, else None."""
    # Must have stroke width 2.25
    if not re.search(r"\b2\.25\s+w\b", content):
        return None
    # Must have a closed path (h = closepath operator)
    if not re.search(r"\bh\b", content):
        return None
    # Check for badge stroke colors (RG = DeviceRGB, SCN = named color space)
    for color_name, color_pat in _BADGE_COLORS.items():
        if re.search(color_pat + r"\s+(?:RG|SCN)\b", content):
            return color_name
    return None


def find_vector_badges(stream: str) -> List[Tuple[int, int, str]]:
    """Find vector-drawn badge block pairs in a content stream.

    Returns list of (start, end, color) tuples marking char offset ranges to
    excise.  Each range covers the frame BDC/EMC block and (when present) the
    adjacent vector-text BDC/EMC block that follows it.
    """
    blocks = _find_top_level_bdc_blocks(stream)
    removals: List[Tuple[int, int, str]] = []
    i = 0
    while i < len(blocks):
        start, end = blocks[i]
        content = stream[start:end]
        color = _is_badge_frame(content)
        if color is not None:
            removal_end = end
            skip = 1
            # Check if next block is the vector text companion
            if i + 1 < len(blocks):
                nxt_s, nxt_e = blocks[i + 1]
                nxt = stream[nxt_s:nxt_e]
                # Text companion: badge color used as *fill* (rg/scn lowercase),
                # path operators present, and NO BT/ET text operators.
                has_badge_fill = any(
                    re.search(cpat + r"\s+(?:rg|scn)\b", nxt)
                    for cpat in _BADGE_COLORS.values()
                )
                has_text_ops = bool(re.search(r"\bBT\b", nxt))
                if has_badge_fill and not has_text_ops:
                    removal_end = nxt_e
                    skip = 2
            # Guardrail: very large spans can include legitimate vector content
            # (labels/diagrams) in some PDFs; skip those conservative cases.
            if (removal_end - start) > MAX_VECTOR_BADGE_REMOVAL_CHARS:
                i += skip
                continue
            removals.append((start, removal_end, color))
            i += skip
        else:
            i += 1
    return removals


def drop_underflow_q_restore_ops(stream: str) -> Tuple[str, int]:
    """Remove standalone 'Q' operators that would underflow graphics-state stack.

    Vector badge block excision can leave behind orphan `Q` restore operators in
    some PDFs where neighboring tagged blocks share graphics-state boundaries.
    These orphan operators trigger parser warnings (e.g. Poppler / Adobe repair).
    """
    op_re = re.compile(r"(?<!\S)(q|Q)(?!\S)")
    to_remove: List[Tuple[int, int]] = []
    depth = 0
    for m in op_re.finditer(stream):
        op = m.group(1)
        if op == "q":
            depth += 1
            continue
        # Q
        if depth == 0:
            to_remove.append((m.start(), m.end()))
        else:
            depth -= 1

    if not to_remove:
        return stream, 0

    cleaned_parts: List[str] = []
    last = 0
    for start, end in to_remove:
        cleaned_parts.append(stream[last:start])
        last = end
    cleaned_parts.append(stream[last:])
    return "".join(cleaned_parts), len(to_remove)


def remove_vector_badges(
    doc, page_index: int, dry_run: bool,
) -> List[Dict[str, object]]:
    """Remove vector-drawn badge BDC/EMC blocks from a single page.

    Uses PyMuPDF to read/write the page content stream.  Returns a list of
    detection dicts suitable for the JSON report.
    """
    page = doc[page_index]
    pno = page_index + 1

    # Consolidate content streams into one for uniform handling
    page.clean_contents()
    xrefs = page.get_contents()
    if not xrefs:
        return []

    xref = xrefs[0]
    stream_bytes = doc.xref_stream(xref)
    stream = stream_bytes.decode("latin-1")

    badges = find_vector_badges(stream)
    if not badges:
        return []

    detections: List[Dict[str, object]] = []
    for start, end, color in badges:
        badge_type = "must_do" if color == "blue" else "challenging"
        detections.append({
            "page": pno,
            "badge_type": badge_type,
            "color": color,
            "stream_offsets": [start, end],
            "removed": not dry_run,
        })

    if not dry_run:
        # Excise badge blocks in reverse order to preserve earlier offsets
        modified = stream
        for start, end, _ in reversed(badges):
            modified = modified[:start] + modified[end:]
        modified, _ = drop_underflow_q_restore_ops(modified)
        doc.update_stream(xref, modified.encode("latin-1"))

    return detections


def process_pdf(
    pdf_path: Path,
    cartoon_templates: Sequence[Tuple[str, Image.Image]],
    badge_templates: Sequence[Tuple[str, Image.Image]],
    logo_templates: Sequence[Tuple[str, Image.Image]],
    cartoon_threshold: float,
    badge_threshold: float,
    logo_threshold: float,
    dry_run: bool,
    in_place: bool,
    force_remove_fused: bool = False,
    skip_vector_badges: bool = False,
) -> Dict[str, object]:
    doc = fitz.open(pdf_path)

    xref_occ: Dict[int, List[Tuple[int, dict]]] = defaultdict(list)
    for pno, page in enumerate(doc, start=1):
        for info in page.get_image_info(xrefs=True):
            xref_occ[info["xref"]].append((pno, info))

    detections: List[Dict[str, object]] = []
    target_xrefs: List[int] = []
    fused_suspect_xrefs: List[int] = []

    for xref, occ in sorted(xref_occ.items()):
        pno, info = occ[0]
        # Try raw pixmap extraction first.  Fall back to clip rendering for
        # degenerate images (e.g. badges whose visual content comes from PDF
        # graphics state, not raw pixels).
        #
        # Images with a separate SMask (soft mask / transparency) need special
        # handling: some templates were captured with a dark background (raw
        # extraction) while others were captured composited onto white.  We
        # try BOTH the raw and white-composited variants and keep whichever
        # yields the stronger classification.
        img_variants: List[Image.Image] = []
        try:
            pix = fitz.Pixmap(doc, xref)
            img_raw = pixmap_to_pil(pix)
            arr_check = np.asarray(img_raw.convert("L"), dtype=float)
            if arr_check.std() >= 2.0:
                img_variants.append(img_raw)
            smask_ref = doc.xref_get_key(xref, "SMask")
            if smask_ref[0] == "xref":
                smask_xref = int(smask_ref[1].split()[0])
                mask_pix = fitz.Pixmap(doc, smask_xref)
                mask_img = Image.frombytes(
                    "L", [mask_pix.width, mask_pix.height], mask_pix.samples
                )
                white = Image.new("RGB", img_raw.size, (255, 255, 255))
                img_comp = Image.composite(img_raw, white, mask_img)
                arr_check2 = np.asarray(img_comp.convert("L"), dtype=float)
                if arr_check2.std() >= 2.0:
                    img_variants.append(img_comp)
        except Exception:
            pass
        if not img_variants:
            page = doc[pno - 1]
            try:
                clip = page.get_pixmap(clip=fitz.Rect(info["bbox"]), dpi=260)
                img_variants.append(pixmap_to_pil(clip))
            except Exception:
                continue

        # Classify each variant; keep the best detection.
        best_cls = None
        for img in img_variants:
            cls = classify_candidate(
                img,
                width=info["width"],
                height=info["height"],
                cartoon_templates=cartoon_templates,
                badge_templates=badge_templates,
                logo_templates=logo_templates,
                cartoon_threshold=cartoon_threshold,
                badge_threshold=badge_threshold,
                logo_threshold=logo_threshold,
            )
            if best_cls is None:
                best_cls = cls
            elif cls["target"] and (
                not best_cls["target"]
                or max(cls["scores"].values()) > max(best_cls["scores"].values())
            ):
                best_cls = cls
        cls = best_cls
        if not cls["target"]:
            continue

        # Fused image protection: skip oversized composites unless forced
        family = primary_family(cls["reasons"])
        fused = family is not None and is_fused_suspect(info["width"], info["height"], family)
        skipped = fused and not force_remove_fused

        if fused:
            fused_suspect_xrefs.append(xref)

        if not skipped:
            target_xrefs.append(xref)
        detections.append(
            {
                "xref": xref,
                "first_page": pno,
                "size": [info["width"], info["height"]],
                "occurrence_pages": sorted({p for p, _ in occ}),
                "occurrence_count": len(occ),
                "reasons": cls["reasons"],
                "ocr_text": cls["ocr_text"],
                "badge_color": cls["badge_color"],
                "fused_suspect": fused,
                "skipped": skipped,
                "scores": cls["scores"],
                "matches": cls["matches"],
            }
        )

    removed_xrefs: List[int] = []
    if not dry_run:
        for xref in target_xrefs:
            pno = xref_occ[xref][0][0]
            try:
                doc[pno - 1].delete_image(xref)
                removed_xrefs.append(xref)
            except Exception:
                continue

    # Phase 2: Vector badge removal (content-stream BDC/EMC blocks)
    vector_badge_detections: List[Dict[str, object]] = []
    if not skip_vector_badges:
        for pno in range(len(doc)):
            vb_dets = remove_vector_badges(doc, pno, dry_run)
            vector_badge_detections.extend(vb_dets)

    output_path = pdf_path if in_place else pdf_path.with_name(f"{pdf_path.stem} - cleaned.pdf")
    if not dry_run:
        if in_place:
            tmp_output = pdf_path.with_name(f"{pdf_path.stem}.__tmp_clean__.pdf")
            doc.save(tmp_output)
            tmp_output.replace(pdf_path)
        else:
            doc.save(output_path)
    doc.close()

    return {
        "input": str(pdf_path),
        "output": str(output_path),
        "dry_run": dry_run,
        "target_xrefs_count": len(target_xrefs),
        "target_xrefs": target_xrefs,
        "removed_xrefs_count": len(removed_xrefs),
        "removed_xrefs": removed_xrefs,
        "fused_suspect_xrefs": fused_suspect_xrefs,
        "fused_suspect_count": len(fused_suspect_xrefs),
        "detections": detections,
        "vector_badges": vector_badge_detections,
        "vector_badge_count": len(vector_badge_detections),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove APEX logos, cartoons, and Must/Challenging badges from PDFs.")
    parser.add_argument("pdfs", nargs="+", help="Input PDF paths")
    parser.add_argument("--assets-root", default=str(DEFAULT_ASSET_ROOT), help="Root folder containing logos/cartoons/badges template PNGs")
    parser.add_argument("--cartoon-threshold", type=float, default=0.72)
    parser.add_argument("--badge-threshold", type=float, default=0.85)
    parser.add_argument("--logo-threshold", type=float, default=0.94)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument("--force-remove-fused", action="store_true", help="Remove fused composite images that contain non-target content")
    parser.add_argument("--skip-vector-badges", action="store_true", help="Skip Phase 2 vector badge content-stream removal")
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    assets_root = Path(args.assets_root)
    cartoon_templates = load_templates(assets_root / "cartoons")
    badge_templates = load_templates(assets_root / "badges")
    logo_templates = load_templates(assets_root / "logos")

    if not cartoon_templates:
        raise RuntimeError(f"No cartoon templates found in {assets_root / 'cartoons'}")
    if not badge_templates:
        raise RuntimeError(f"No badge templates found in {assets_root / 'badges'}")
    if not logo_templates:
        raise RuntimeError(f"No logo templates found in {assets_root / 'logos'}")

    results: List[Dict[str, object]] = []
    for raw in args.pdfs:
        pdf = Path(raw)
        if not pdf.exists():
            raise FileNotFoundError(f"Missing input PDF: {pdf}")
        results.append(
            process_pdf(
                pdf_path=pdf,
                cartoon_templates=cartoon_templates,
                badge_templates=badge_templates,
                logo_templates=logo_templates,
                cartoon_threshold=args.cartoon_threshold,
                badge_threshold=args.badge_threshold,
                logo_threshold=args.logo_threshold,
                dry_run=args.dry_run,
                in_place=args.in_place,
                force_remove_fused=args.force_remove_fused,
                skip_vector_badges=args.skip_vector_badges,
            )
        )

    report = {"results": results}
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

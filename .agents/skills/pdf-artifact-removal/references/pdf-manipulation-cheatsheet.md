# PDF Manipulation Cheat Sheet

Quick reference for common PDF operations used alongside artifact removal.

## Key Libraries

| Library | Import | Best For |
|---|---|---|
| pikepdf | `import pikepdf` | Low-level PDF object inspection, content stream editing, XObject manipulation |
| PyMuPDF | `import fitz` | Image extraction, bounding boxes, rendering pages to images, visual coverage |
| pypdf | `from pypdf import PdfReader, PdfWriter` | Page cropping, margin hiding, simple structural ops |

## PDF Content Stream Basics

A page's content stream is a sequence of drawing operators. Key operators:

| Operator | Meaning |
|---|---|
| `q` / `Q` | Save / restore graphics state |
| `cm` | Set current transformation matrix (6 values: a b c d tx ty) |
| `Do` | Paint an XObject (e.g., `/Im0 Do` draws image Im0) |
| `BDC` / `EMC` | Begin / end marked content (used for tagging artifacts) |
| `re` | Rectangle path |
| `f` | Fill path |
| `S` | Stroke path |
| `BT` / `ET` | Begin / end text block |
| `Tj` / `TJ` | Show text string / array |
| `gs` | Set graphics state (references ExtGState resource) |

## Transform Matrix Format

`a b c d tx ty cm`

- No rotation/skew: `a 0 0 d tx ty` (scale x by a, scale y by d, translate to tx,ty)
- With rotation: b and c are non-zero

## Artifact Block Structure

```
/Artifact <</BBox [x0 y0 x1 y1] /Subtype /Watermark /Type /Pagination >>BDC
q
/GS0 gs
450.9999 0 0 380.4999 72.15 236.9 cm
/Im0 Do
Q
EMC
```

## SMask (Soft Mask / Transparency)

Images with an `/SMask` entry have a separate grayscale image controlling per-pixel transparency. The watermark image itself may be opaque; the SMask makes it appear semi-transparent.

## Coordinate System

- PDF default origin: bottom-left (but many tools use top-left)
- Units: points (1 point = 1/72 inch)
- Typical A4 page: 595.5 x 842.25 points

## Pixel-to-Point Conversion

```python
x_points = x_pixels * (page.rect.width / pix.width)
y_points = y_pixels * (page.rect.height / pix.height)
```

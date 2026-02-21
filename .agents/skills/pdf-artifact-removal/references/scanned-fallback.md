# Scanned PDF Watermark Removal (Fallback)

When a PDF is scanned (page content is one big raster image with no tagged artifact blocks), use this rasterize-threshold-rebuild approach.

## Prerequisites

```bash
pip install pymupdf opencv-python numpy
```

## Approach

Render each page to a high-DPI image, apply binary thresholding to suppress the light watermark while preserving darker text, then rebuild the PDF from the cleaned images.

## Code

```python
import fitz
import cv2
import numpy as np

doc = fitz.open("scanned_input.pdf")
out = fitz.open()

for page in doc:
    pix = page.get_pixmap(dpi=300)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

    if pix.n == 4:
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    elif pix.n == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    new_page = out.new_page(width=page.rect.width, height=page.rect.height)
    png_bytes = cv2.imencode(".png", bw)[1].tobytes()
    new_page.insert_image(new_page.rect, stream=png_bytes)

out.save("scanned_output.pdf")
out.close()
doc.close()
```

## Tradeoffs

- Loses vector quality (everything becomes raster).
- File size may grow depending on DPI and compression.
- Works well when the watermark is lighter than the main text content.
- For color-preserving removal, use adaptive thresholding or color-range masking instead of Otsu binarization.

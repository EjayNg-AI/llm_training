# LaTeX Transcription Command Template

Use this reference to run the end-to-end workflow with one-image background requests.

## 1) Render PDF pages to PNG

```bash
mkdir -p /tmp/latex_ocr/pages /tmp/latex_ocr/sections /tmp/latex_ocr/snippets /tmp/latex_ocr/final
pdftoppm -f <start_page> -l <end_page> -png input.pdf /tmp/latex_ocr/pages/page
```

## 2) Build section/chunk images

Example append of contiguous pages:

```bash
convert /tmp/latex_ocr/pages/page-000006.png /tmp/latex_ocr/pages/page-000007.png -append /tmp/latex_ocr/sections/section_1_2.png
```

Split long sections into `...part1.png`, `...part2.png`, `...part3.png` as needed.

## 3) Transcribe each image independently (single image per call)

```bash
python -u transcribe_math_latex_background.py /tmp/latex_ocr/sections/section_1_2.png | tee /tmp/latex_ocr/sections/section_1_2.log
python -u transcribe_math_latex_background.py /tmp/latex_ocr/sections/section_1_3_part1.png | tee /tmp/latex_ocr/sections/section_1_3_part1.log
python -u transcribe_math_latex_background.py /tmp/latex_ocr/sections/section_1_3_part2.png | tee /tmp/latex_ocr/sections/section_1_3_part2.log
python -u transcribe_math_latex_background.py /tmp/latex_ocr/sections/section_1_3_part3.png | tee /tmp/latex_ocr/sections/section_1_3_part3.log
```

Expected lifecycle events in logs:
- `submit_start`
- `submitted`
- repeated `poll`
- `final`

## 4) Extract LaTeX payload from each log

```bash
awk '/===LATEX_BEGIN===/{flag=1;next}/===LATEX_END===/{flag=0}flag' /tmp/latex_ocr/sections/section_1_2.log > /tmp/latex_ocr/snippets/section_1_2.tex
```

Repeat for each chunk log.

## 5) Assemble snippets in reading order

```bash
cat \
  /tmp/latex_ocr/snippets/section_1_2.tex \
  /tmp/latex_ocr/snippets/section_1_3_part1.tex \
  /tmp/latex_ocr/snippets/section_1_3_part2.tex \
  /tmp/latex_ocr/snippets/section_1_3_part3.tex \
  > /tmp/latex_ocr/final/body.tex
```

Insert `body.tex` into a document wrapper (`\begin{document}...\end{document}`).

## 6) Compile final LaTeX

```bash
cd /tmp/latex_ocr/final
pdflatex -interaction=nonstopmode -halt-on-error final_transcription.tex
```

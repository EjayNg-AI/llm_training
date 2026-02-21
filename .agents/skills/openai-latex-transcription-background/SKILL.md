---
name: openai-latex-transcription-background
description: Convert PDF textbook pages into LaTeX by rendering pages to PNG, uploading one image per OpenAI Responses API request, and polling background jobs to completion. Use when users ask for OCR/transcription of math-heavy pages, full prose-plus-math LaTeX extraction, or reliable background-mode processing with ordered snippet assembly and pdflatex compilation.
---

# OpenAI LaTeX Transcription Background

Use this skill to run a reliable LaTeX transcription workflow with `transcribe_math_latex_background.py`.

## Preconditions

- Ensure `OPENAI_API_KEY` is available in environment variables or a local `.env` file.
- Ensure the repo has Python dependencies (`openai`, `python-dotenv`) installed.
- Ensure system tools are available:
- `pdftoppm` for rendering PDF pages to PNG
- `convert` (ImageMagick) for cropping/append operations
- `pdflatex` for final compile
- Run transcription commands with `python -u` for unbuffered polling logs.

## Core Workflow

1. Render source PDF pages to PNG:
```bash
pdftoppm -f <start_page> -l <end_page> -png input.pdf /tmp/latex_ocr/pages/page
```

2. Build section images in reading order:
- Crop section boundaries as needed.
- Append contiguous page segments when they belong to one section:
```bash
convert /tmp/latex_ocr/pages/page-000006.png /tmp/latex_ocr/pages/page-000007.png -append /tmp/latex_ocr/sections/section_1_2.png
```

3. Split very long sections into contiguous chunks for reliability/runtime.

4. Submit one image per OpenAI call using the repo script:
```bash
python -u transcribe_math_latex_background.py /tmp/latex_ocr/sections/section_1_2.png | tee /tmp/latex_ocr/sections/section_1_2.log
python -u transcribe_math_latex_background.py /tmp/latex_ocr/sections/section_1_3_part1.png | tee /tmp/latex_ocr/sections/section_1_3_part1.log
```
- Repeat once per PNG chunk.
- Keep each request single-image; do not batch multiple images in one request.

5. Monitor JSON events until terminal status:
- `submit_start`, `submitted`, repeated `poll`, then `final`
- Treat `completed` as success.

6. Extract transcribed LaTeX between delimiters:
- `===LATEX_BEGIN===`
- `===LATEX_END===`

7. Assemble extracted snippets in document reading order and compile with `pdflatex`.

## API Pattern

Follow this request shape for each image:

```python
uploaded = client.files.create(file=open(image_path, "rb"), purpose="vision")

response = client.responses.create(
    model="gpt-5.2",
    reasoning={"effort": "xhigh"},
    background=True,
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": TRANSCRIPTION_PROMPT},
                {"type": "input_image", "file_id": uploaded.id, "detail": "high"},
            ],
        }
    ],
)
```

Poll with `client.responses.retrieve(response.id)` every 10 seconds until terminal status.

## Execution Rules

- Use the Responses API (`responses.create`, `responses.retrieve`), not Chat Completions.
- Use `background=True` for long transcriptions.
- Upload and transcribe one PNG per request.
- Preserve chunk ordering when assembling final `.tex`.
- Keep logs for traceability and delimiter-based extraction.
- On non-`completed` status (`failed`, `cancelled`, `expired`, `incomplete`), inspect the final payload and retry only affected chunks.

## Repo-Specific Notes

- Use `transcribe_math_latex_background.py` as the canonical transcription runner.
- Follow `README.md` section `Latest End-to-End Process (Sections 1.2 and 1.3 from a1.pdf)` for the current canonical sequence.
- Use `references/workflow-template.md` for reusable command templates.

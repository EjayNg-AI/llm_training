#!/usr/bin/env python3
"""Generate a consolidated TXT bundle of implemented-docs references for SWE handoff."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent

DOC_FILES = [
    ("docs/README.md", "Index of repository documentation with a file-level map and update policy guidance."),
    ("docs/PROJECT_STATUS.md", "Tracks current implementation completion, stability, and major gaps versus the architecture reference."),
    ("docs/IMPLEMENTED_STEPS.md", "Provides detailed, stage-by-stage documentation of implemented pipeline steps and artifacts."),
    ("docs/TOKENIZER_BPE.md", "Serves as the full tokenizer implementation and operations reference."),
    ("docs/CHANGELOG.md", "Records chronological change entries with impacted files and validation notes."),
    ("docs/NEXT_STEPS.md", "Defines the roadmap and next implementation priorities aligned to the north-star overview."),
    ("docs/DEVELOPMENT_WORKFLOW.md", "Defines coding, testing, and documentation expectations for contributors and Codex."),
    ("docs/DIRECTORY_STRUCTURE.md", "Captures the tracked repository directory layout to onboard engineers to current file structure quickly."),
]

PROMPT = dedent(
    """
    You are an expert technical lead reviewing an LLM training scaffold repository.

    Task:
    Analyze the repository state based on the provided consolidated handoff document:
    `implemented_docs_bundle.txt` (generated from canonical docs).
    Do a careful, evidence-based assessment of what has been implemented and what the next concrete engineering steps should be.

    Your instructions:
    1) First, extract and summarize what is currently implemented across:
    - pipeline stages
    - infrastructure
    - docs/process
    - tokenizer subsystem
    - governance and roadmap items
    - validation/testing coverage

    2) Then generate a prioritized list of concrete next steps (short-, medium-, and long-horizon), each containing:
    - Specific goal
    - Why it is the next logical step (informed by gaps in docs)
    - Entry conditions (what must be true before starting)
    - Success conditions (how to verify completion)
    - Concrete implementation tasks
    - Risks/tradeoffs
    - Any hard dependencies (files, scripts, configs, docs, tests)
    - Suggested owner type (infrastructure / data / training / evaluation / governance)
    - Estimated verification approach

    3) Keep each recommendation actionable and testable.
    4) Where requirements are missing or unclear, explicitly flag as "Assumption needed" and list the exact missing input.
    5) Preserve ordering that aligns with architecture flow and release discipline.
    6) Identify any gaps where docs and implementation appear misaligned.

    Output format:
    - Executive summary (5–8 bullets)
    - High-confidence "next 10" action plan table (ordered)
    - Risk register (top 5 risks)
    - Documentation updates needed (if any), mapped by file path
    - Optional “Do not do now” backlog (explicitly de-scope items)

    Restrictions:
    - Use only the provided `implemented_docs_bundle.txt` as source material; do not assume external context.
    - Do not invent file-level behaviors not present in the source.
    - Do not propose adding external dependencies or cloud services unless they are explicitly implied by current repo constraints or roadmap.
    - If you see a conflict between docs and implementation details, flag it clearly.
    - Do not suggest destructive actions or broad rewrites; prefer incremental, low-risk steps that align with the existing architecture.
    - Keep recommendations concrete, measurable, and directly implementable by a software engineering team.

    Tone and style:
    - Be direct, precise, and executive-to-engineer actionable.
    - Prefer clarity over verbosity.
    - Base assertions on evidence-style references (e.g., “as documented in the bundled docs’ section on ...”).
    """
).strip()


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    out_path = repo_root / "implemented_docs_bundle.txt"

    sections = []
    sections.append("Prompt to run:\n" + PROMPT)

    header = dedent(
        f"""
        Repository implemented-docs bundle
        Generated: {datetime.now().isoformat(timespec='seconds')}

        This file contains curated documentation for engineering handoff and onboarding.
        """
    ).strip()

    sections.append(header)

    for rel_path, explanation in DOC_FILES:
        file_path = repo_root / rel_path
        if not file_path.exists():
            return 2

        content = file_path.read_text(encoding="utf-8")
        block = dedent(
            f"""
            ---
            Source: {rel_path}
            Purpose: {explanation}

            {content.strip()}
            """
        ).strip()
        sections.append(block)

    out_path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

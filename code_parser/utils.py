"""
utils.py
Two helpers used by ProjectDiagramView:
  1. extract_project_files()  – reads a .zip and returns concatenated code
  2. build_analysis_prompt()  – builds the structured Claude prompt
"""

import io
import zipfile


# ─────────────────────────────────────────────
#  1. ZIP extractor
# ─────────────────────────────────────────────

# File extensions we care about
ALLOWED_EXTENSIONS = {".py", ".html", ".txt", ".md", ".json", ".yaml", ".yml"}

# Files / dirs to skip (Django internals, migrations, etc.)
SKIP_PATTERNS = {
    "__pycache__", "migrations", ".pyc", ".git",
    "staticfiles", "node_modules", ".env",
}


def extract_project_files(zip_file_obj) -> str:
    """
    Read an uploaded .zip, collect all relevant source files,
    and return them concatenated as one string with file-path headers.

    Parameters
    ----------
    zip_file_obj : InMemoryUploadedFile or file-like object

    Returns
    -------
    str  –  concatenated source code with ──── separators
    """
    collected = []

    with zipfile.ZipFile(io.BytesIO(zip_file_obj.read()), "r") as zf:
        for member in zf.infolist():

            # Skip directories
            if member.is_dir():
                continue

            path = member.filename

            # Skip unwanted paths
            if any(skip in path for skip in SKIP_PATTERNS):
                continue

            # Only process allowed extensions
            ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
            if ext not in ALLOWED_EXTENSIONS:
                continue

            try:
                content = zf.read(member).decode("utf-8", errors="replace")
            except Exception:
                continue

            collected.append(
                f"\n\n{'─' * 60}\n"
                f"FILE: {path}\n"
                f"{'─' * 60}\n"
                f"{content}"
            )

    if not collected:
        raise ValueError("No readable Python / template files found in the ZIP.")

    return "".join(collected)


# ─────────────────────────────────────────────
#  2. Prompt builder
# ─────────────────────────────────────────────

SYSTEM_INSTRUCTIONS = """
You are a senior Django architect. Analyse the Django project code provided
and respond with ONLY a valid JSON object — no markdown fences, no preamble.

The JSON must follow this exact schema:

{
  "flowchart": "<Mermaid flowchart LR diagram as a string>",
  "class_diagram": "<Mermaid classDiagram as a string>",
  "steps": [
    {
      "step": 1,
      "title": "Short title",
      "explanation": "Clear, textbook-level explanation of this step."
    }
  ],
  "summary": "One paragraph overall summary of the project flow."
}

Rules:
- flowchart    : use Mermaid 'flowchart LR' syntax. Cover request → URL → view → ORM → response.
- class_diagram: use Mermaid 'classDiagram' syntax. Include all Django models found, their fields and relationships.
- steps        : 5 to 10 steps that explain the high-level logic flow in plain English.
- summary      : max 4 sentences, suitable for a textbook.
- Return ONLY the JSON. No extra text outside the JSON object.
"""


def build_analysis_prompt(code: str) -> str:
    """
    Wrap the project code in the structured Claude prompt.

    Parameters
    ----------
    code : str  –  concatenated project source code

    Returns
    -------
    str  –  full prompt ready to send to Claude
    """
    return (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        f"Here is the Django project code to analyse:\n\n"
        f"{code}"
    )
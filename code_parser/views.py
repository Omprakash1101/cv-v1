"""
views.py  –  api/views.py
Replace your entire current views.py with this file.

Views:
  FrontendPageView   GET  /          → renders index.html (the UI)
  ProjectDiagramView POST /diagram/  → runs AST parser, returns SVG + JSON / HTML
"""

import ast

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status

from django.http import JsonResponse
from django.conf import settings

from .serializers import ProjectAnalysisSerializer
from .utils import extract_project_files
from .cfg_builder import generate_flowchart_svg

import logging
logger = logging.getLogger(__name__)
# ─────────────────────────────────────────────
#  Pure-AST helpers (no AI needed)
# ─────────────────────────────────────────────
class HealthCheckView(APIView):
    """
    GET /healthcheck/
    Basic security + system status check
    """

    def get(self, request):
        return Response({
            "status": "ok",
            "debug": settings.DEBUG,
            "secure": not settings.DEBUG,
            "message": "Application running securely"
        })

def extract_classes(code: str) -> list:
    """Return list of dicts: { name, bases, methods, fields }"""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    classes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases   = [ast.unparse(b) for b in node.bases]
        methods, fields = [], []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                args = [a.arg for a in item.args.args if a.arg != "self"]
                methods.append(f"{item.name}({', '.join(args)})")
            elif isinstance(item, ast.Assign):
                for t in item.targets:
                    fields.append(ast.unparse(t))
            elif isinstance(item, ast.AnnAssign):
                fields.append(
                    f"{ast.unparse(item.target)}: {ast.unparse(item.annotation)}"
                )
        classes.append({"name": node.name, "bases": bases,
                        "methods": methods, "fields": fields})
    return classes


def extract_steps(code: str) -> list:
    """Return up to 15 high-level steps from the AST."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    steps, counter = [], [0]

    def add(title, explanation):
        counter[0] += 1
        steps.append({"step": counter[0], "title": title,
                      "explanation": explanation})

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            add(f"Define: {node.name}",
                f"Function '{node.name}({', '.join(args)})' "
                f"— {len(node.body)} statement(s).")
        elif isinstance(node, ast.ClassDef):
            bases = [ast.unparse(b) for b in node.bases]
            add(f"Class: {node.name}",
                f"Inherits from {', '.join(bases)}." if bases
                else f"Class '{node.name}' defined.")
        elif isinstance(node, ast.If):
            add("Conditional branch",
                f"if {ast.unparse(node.test)}: "
                f"{len(node.body)} true / {len(node.orelse)} false statements.")
        elif isinstance(node, ast.For):
            add(f"For loop",
                f"Iterates {ast.unparse(node.target)} over {ast.unparse(node.iter)}.")
        elif isinstance(node, ast.While):
            add("While loop", f"Loops while {ast.unparse(node.test)}.")
        elif isinstance(node, ast.Return) and node.value:
            add("Return", f"Returns: {ast.unparse(node.value)}")
        elif isinstance(node, ast.Raise):
            add("Raise exception",
                f"Raises: {ast.unparse(node.exc) if node.exc else 'exception'}")
        elif isinstance(node, ast.Try):
            add("Try / except",
                f"{len(node.handlers)} handler(s)"
                + (", with finally." if node.finalbody else "."))
        if counter[0] >= 15:
            break
    return steps


def build_summary(code: str) -> str:
    """Lightweight AST summary — no AI."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Syntax error: {e}"

    funcs   = [n.name for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    classes = [n.name for n in ast.walk(tree)
               if isinstance(n, ast.ClassDef)]
    imports = [ast.unparse(n) for n in ast.walk(tree)
               if isinstance(n, (ast.Import, ast.ImportFrom))]

    parts = []
    if classes:
        parts.append(f"{len(classes)} class(es): {', '.join(classes)}.")
    if funcs:
        parts.append(f"{len(funcs)} function(s): {', '.join(funcs)}.")
    if imports:
        parts.append(f"Imports: {', '.join(imports[:5])}"
                     + (" …" if len(imports) > 5 else "."))
    return " ".join(parts) if parts else "No top-level definitions found."


# ─────────────────────────────────────────────
#  View 1 — Frontend page  GET /
# ─────────────────────────────────────────────

class FrontendPageView(APIView):
    def get(self, request, *args, **kwargs):
        return render(request, "index.html")


# ─────────────────────────────────────────────
#  View 2 — Diagram API  POST /diagram/
# ─────────────────────────────────────────────

class ProjectDiagramView(APIView):
    """
    POST /diagram/
    Inputs : code (str) OR project_zip (file), format ("json"|"html")
    Returns: SVG flowchart + class info + steps + summary
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):

        serializer = ProjectAnalysisSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error":"Invaild input prodived"},
                            status=status.HTTP_400_BAD_REQUEST)

        validated   = serializer.validated_data
        raw_code    = validated.get("code", "")
        project_zip = validated.get("project_zip", None)
        fmt         = validated.get("format", "json").lower()

        # Extract from ZIP
        if project_zip:
            try:
                raw_code = extract_project_files(project_zip)
            except Exception as exc:


                logger.exception("ZIP extraction failed")

                return Response(
                    {"error": "Failed to process uploaded file."},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )

        if not raw_code or not raw_code.strip():
            return Response(
                {"error": "Provide 'code' (string) or 'project_zip' (file)."},
                status=status.HTTP_400_BAD_REQUEST)

        # Run AST analysis
        svg, err = generate_flowchart_svg(raw_code)
        if err and not svg:
            logger.exception("Flowchart generation failed")

            return Response(
                {"error": "Unable to generate diagram."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        # 👉 ADD HERE
        import logging
        logger = logging.getLogger(__name__)

        if err:
            logger.exception("Flowchart warning: %s", err)

        analysis = {
            "svg": svg,
            "classes": extract_classes(raw_code),
            "steps": extract_steps(raw_code),
            "summary": build_summary(raw_code),
        }

        if fmt == "json":

            return Response(analysis, status=status.HTTP_200_OK)

        if fmt == "html":
            return render(request, "diagram.html",
                          {"analysis": analysis})

        return Response({"error": "Invalid 'format'. Use 'json' or 'html'."},
                        status=status.HTTP_400_BAD_REQUEST)
import io
import ast as ast_mod

from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .parser import generate_flowchart_svg, CFGBuilder


# 🔹 Example codes (same as Flask)
EXAMPLE_CODES = {
    "factorial": '''def fact(n):
    if n == 0:
        return 1
    return n * fact(n - 1)

print(fact(5))''',

    "fibonacci": '''def fib(n):
    if n <= 1:
        return n
    a = 0
    b = 1
    for i in range(2, n + 1):
        c = a + b
        a = b
        b = c
    return b

print(fib(10))''',

    "bubble_sort": '''def bubble_sort(arr):
    n = 5
    for i in range(n):
        for j in range(n - i - 1):
            if j > j + 1:
                temp = j
    return n''',

    "binary_search": '''def binary_search(target):
    low = 0
    high = 100
    while low <= high:
        mid = (low + high) // 2
        if mid == target:
            return mid
        elif mid < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1''',

    "while_loop": '''x = 0
total = 0
while x < 10:
    if x == 5:
        break
    total = total + x
    x = x + 1
print(total)''',

    "for_loop": '''result = 0
for i in range(1, 6):
    if i == 3:
        continue
    result = result + i
print(result)''',
}


# 🔹 1. INDEX PAGE (like Flask "/")
def index(request):
    return render(request, "index.html", {
        "examples": list(EXAMPLE_CODES.keys())
    })


# 🔹 2. GENERATE API (like Flask "/generate")
@api_view(['POST'])
def generate(request):
    code = request.data.get("code", "")

    if not code.strip():
        return Response({"error": "No code provided"}, status=400)

    svg, error = generate_flowchart_svg(code)

    if error:
        return Response({"error": error}, status=400)

    return Response({"svg": svg})


# 🔹 3. EXAMPLE API (like Flask "/example/<name>")
@api_view(['GET'])
def example(request, name):
    code = EXAMPLE_CODES.get(name, "")

    if not code:
        return Response({"error": "Example not found"}, status=404)

    return Response({"code": code})


# 🔹 4. DOWNLOAD API (like Flask "/download")
@api_view(['POST'])
def download(request):
    code = request.data.get("code", "")
    fmt = request.data.get("format", "svg")

    if not code.strip():
        return Response({"error": "No code provided"}, status=400)

    svg, error = generate_flowchart_svg(code)

    if error:
        return Response({"error": error}, status=400)

    # ✅ SVG download
    if fmt == "svg":
        response = HttpResponse(svg, content_type="image/svg+xml")
        response['Content-Disposition'] = 'attachment; filename="flowchart.svg"'
        return response

    # ✅ PNG download
    elif fmt == "png":
        tree = ast_mod.parse(code)
        builder = CFGBuilder()

        for node in tree.body:
            if isinstance(node, ast_mod.FunctionDef):
                builder.visit(node)

        for node in tree.body:
            if not isinstance(node, ast_mod.FunctionDef):
                builder.visit(node)

        dot = builder.finish()
        png_bytes = dot.pipe(format="png")

        response = HttpResponse(png_bytes, content_type="image/png")
        response['Content-Disposition'] = 'attachment; filename="flowchart.png"'
        return response

    return Response({"error": "Unknown format"}, status=400)
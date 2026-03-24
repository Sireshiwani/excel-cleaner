#!/usr/bin/env python3
"""Simple Flask web app for Excel adjacent-row merging."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from flask import Flask, Response, render_template_string, request, send_file

from merge_adjacent_rows import process_workbook_bytes

app = Flask(__name__)

INDEX_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Excel Adjacent Row Merger</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; max-width: 760px; }
      form { padding: 1rem; border: 1px solid #ccc; border-radius: 8px; }
      label { display: block; margin-top: 0.75rem; font-weight: 600; }
      input[type="text"], input[type="file"] { width: 100%; margin-top: 0.35rem; }
      button { margin-top: 1rem; padding: 0.5rem 1rem; cursor: pointer; }
      .error { color: #b00020; margin-top: 1rem; }
    </style>
  </head>
  <body>
    <h1>Excel Adjacent Row Merger</h1>
    <p>Upload an .xlsx file to merge every 2 adjacent data rows (header row is kept unchanged).</p>

    <form action="/merge" method="post" enctype="multipart/form-data">
      <label for="excel_file">Excel file (.xlsx)</label>
      <input id="excel_file" name="excel_file" type="file" accept=".xlsx" required />

      <label for="sheet_name">Sheet name (optional)</label>
      <input id="sheet_name" name="sheet_name" type="text" placeholder="Example: Sheet1" />

      <label for="separator">Separator (optional)</label>
      <input id="separator" name="separator" type="text" value=" " />

      <button type="submit">Merge and Download</button>
    </form>

    {% if error %}
      <p class="error">{{ error }}</p>
    {% endif %}
  </body>
</html>
"""


@app.get("/")
def index() -> str:
    return render_template_string(INDEX_TEMPLATE)


@app.post("/merge")
def merge_excel() -> Response | str:
    uploaded_file = request.files.get("excel_file")
    if uploaded_file is None or not uploaded_file.filename:
        return render_template_string(INDEX_TEMPLATE, error="Please select an Excel file.")

    file_name = uploaded_file.filename
    if not file_name.lower().endswith(".xlsx"):
        return render_template_string(
            INDEX_TEMPLATE,
            error="Only .xlsx files are supported.",
        )

    separator = request.form.get("separator", " ")
    sheet_name = request.form.get("sheet_name", "").strip() or None

    try:
        merged_bytes = process_workbook_bytes(
            workbook_bytes=uploaded_file.read(),
            sheet_name=sheet_name,
            separator=separator,
        )
    except Exception as exc:  # pragma: no cover - simple UI error handling
        return render_template_string(INDEX_TEMPLATE, error=f"Failed to process file: {exc}")

    stem = Path(file_name).stem
    download_name = f"{stem}_merged.xlsx"

    return send_file(
        BytesIO(merged_bytes),
        as_attachment=True,
        download_name=download_name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

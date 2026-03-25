# excel-cleaner

Simple Python tools (CLI + web app) to merge values from every 2 adjacent data
rows in an Excel sheet while keeping the header row unchanged.

## Setup

```bash
python3 -m pip install -r requirements.txt
```

## CLI usage

```bash
python3 merge_adjacent_rows.py input.xlsx
```

By default this writes `input_merged.xlsx`.

Optional arguments:

```bash
python3 merge_adjacent_rows.py input.xlsx \
  --output-file output.xlsx \
  --sheet "Sheet1" \
  --separator " | "
```

## Web app usage

Start the server:

```bash
python3 web_app.py
```

Then open:

```text
http://localhost:5000
```

Upload your `.xlsx` file, optionally set sheet name/separator, and download the
merged result.

## Merge rules

Header row (row 1) is preserved as-is.

Starting at row 2, rows are merged in pairs:
- Rows 2 + 3 become one row
- Rows 4 + 5 become one row
- and so on

Per-column merge behavior:
- If one value is empty, the non-empty value is kept
- If both values are equal, value is kept once
- If both values are non-empty and different, values are concatenated with
  separator (default: single space)

If there is an odd number of data rows, the last unpaired row is kept as-is.

## Run tests

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

# AGENTS.md

## Cursor Cloud specific instructions

**Product**: excel-cleaner — a Python CLI + Flask web app for merging adjacent rows in `.xlsx` files.

### Services

| Service | Command | Port |
|---|---|---|
| Flask Web App | `python3 web_app.py` | 5000 |
| CLI Tool | `python3 merge_adjacent_rows.py <input.xlsx>` | N/A |

### Standard commands

See `README.md` for full usage. Quick reference:

- **Install deps**: `pip install -r requirements.txt`
- **Tests**: `python3 -m unittest discover -s tests -p "test_*.py"`
- **Lint**: `python3 -m flake8 --max-line-length=120 *.py tests/*.py`
- **Web app (dev)**: `python3 web_app.py` (runs on `0.0.0.0:5000` with debug mode)

### Notes

- `pyright` reports type errors on `wb.active` (openpyxl returns `Optional[Worksheet]`). These are pre-existing upstream type-stub issues, not real bugs.
- No external services (databases, caches, etc.) are required. The app is fully self-contained.
- The web app runs in Flask debug mode by default, so it auto-reloads on code changes.

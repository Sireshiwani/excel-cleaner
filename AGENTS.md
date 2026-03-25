# AGENTS.md

## Cursor Cloud specific instructions

This is a simple Python project (no build system, no Docker, no database). All commands are documented in the `README.md`.

### Services

| Service | Command | Notes |
|---|---|---|
| **Unit tests** | `python3 -m unittest discover -s tests -p "test_*.py"` | Uses stdlib `unittest` |
| **CLI tool** | `python3 merge_adjacent_rows.py <input.xlsx>` | Writes `<input>_merged.xlsx` by default |
| **Flask web app** | `python3 web_app.py` | Runs on `http://localhost:5000`, debug mode enabled |

### Caveats

- No linter is configured in the project. There is no `pyproject.toml`, `setup.cfg`, or linter config file.
- The Flask web app imports `merge_adjacent_rows` as a sibling module, so it must be run from the repository root (`/workspace`).
- pip installs to `~/.local` (user install) since system site-packages is not writeable; `~/.local/bin` may not be on `PATH` but `python3 -m flask` works as an alternative to the `flask` CLI.

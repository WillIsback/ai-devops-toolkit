# docgen

CLI tool that generates and inserts docstrings into Python and TypeScript source files using a locally-hosted [vLLM](https://github.com/vllm-project/vllm) instance. Designed for use during development or at build time via `uv run` or `pnpm run`.

All file edits are isolated in a short-lived `docgen/<timestamp>` git branch that is merged back into the current branch and deleted — keeping your working branch clean.

---

## Setup

Copy `.env.example` to `.env` and set your vLLM endpoint:

```
VLLM_BASE_URL=http://<your-host>:30000/v1
BATCH_SIZE=4
```

Then install dependencies:

```bash
uv sync
```

## Usage

```bash
# Single file
uv run docgen path/to/file.py

# Flat folder (top-level files only)
uv run docgen src/

# Recurse into subdirectories
uv run docgen src/ --recursive

# Regenerate existing docstrings
uv run docgen src/ --force

# Explicit format override
uv run docgen src/ --format tsdoc

# Via pnpm
pnpm run docgen -- src/
```

## Options

| Flag | Default | Description |
|---|---|---|
| `target` | — | File or folder to process (required) |
| `--format` | auto | Docstring format: `mkdocs` (Python) or `tsdoc` (TypeScript/TSX) |
| `--recursive` / `-r` | off | Recurse into subdirectories when target is a folder |
| `--force` | off | Regenerate docstrings even if they already exist |

## Format auto-detection

| Extension | Default format |
|---|---|
| `.py` | `mkdocs` |
| `.ts`, `.tsx` | `tsdoc` |

## How it works

1. **Pre-flight checks** — aborts if the working tree has uncommitted changes, or if vLLM is unreachable
2. **Model detection** — queries `GET /v1/models` to auto-detect the loaded model
3. **File resolution** — collects `.py` / `.ts` / `.tsx` files under the target (flat or recursive)
4. **Parsing** — Python files are parsed with the `ast` module; TypeScript files use regex. Files already fully documented are skipped (unless `--force`)
5. **Batch LLM calls** — files are sent to vLLM in parallel, up to `BATCH_SIZE` concurrent calls
6. **Git workflow** — creates a `docgen/<timestamp>` branch, writes patched files, commits, merges back, deletes the branch. On failure the branch is left intact for manual inspection

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Pre-flight failure (dirty tree, vLLM unreachable) or git error |
| `2` | Nothing to do (no files found or all already documented) |

## Files

```
docgen/
├── docgen.py          # CLI, parsing, LLM calls, git workflow
└── tests/
    └── test_docgen.py # 53 unit tests
pyproject.toml         # uv entry point: docgen = "docgen.docgen:app"
package.json           # pnpm scripts wrapper
.env.example           # VLLM_BASE_URL, BATCH_SIZE
```

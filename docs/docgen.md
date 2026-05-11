# docgen

CLI tool that generates and inserts docstrings into Python and TypeScript source files using a locally-hosted [vLLM](https://github.com/vllm-project/vllm) instance. Designed for use during development or at build time via `uv run` or `pnpm run`.

The engine is written in **Rust**: source files are parsed with [tree-sitter](https://tree-sitter.github.io/) AST queries (no regex), LLM calls run in parallel with a tokio semaphore, and all file edits are isolated in a short-lived `docgen/<timestamp>` git branch that is merged back and deleted — keeping your working branch clean.

---

## Installation

### Global install (use from anywhere)

Install `docgen` as a global tool with `uv`. Maturin builds the Rust binary and installs it into the tool environment:

```bash
uv tool install git+https://github.com/WillIsback/ai-devops-toolkit.git
```

Then run from any directory:

```bash
docgen src/ --recursive
```

To update later:

```bash
uv tool upgrade ai-devops-toolkit

# Or force a reinstall to pick up the latest commit:
uv tool install --reinstall git+https://github.com/WillIsback/ai-devops-toolkit.git
```

---

### Local install — Python project

```bash
uv add --dev git+https://github.com/WillIsback/ai-devops-toolkit.git
uv run docgen src/
```

---

### Local install — TypeScript / Node project

On `npm install` / `pnpm install` a postinstall script downloads the pre-compiled binary from GitHub Releases automatically.

```bash
npm install WillIsback/ai-devops-toolkit
# or
pnpm install WillIsback/ai-devops-toolkit
```

Then run:

```bash
pnpm run docgen -- src/
npm run docgen -- src/
```

---

### Local install — Python + TypeScript monorepo

Clone or add the toolkit as a submodule, then wire both entry points:

```bash
git clone https://github.com/WillIsback/ai-devops-toolkit.git tools/ai-devops-toolkit
cd tools/ai-devops-toolkit && uv sync
```

In your root `package.json`:

```json
{
  "scripts": {
    "docgen": "uv run --project tools/ai-devops-toolkit docgen"
  }
}
```

---

## Configuration

`docgen` loads `.env` files in two layers (project overrides global):

### Global config

Create `~/.config/docgen/.env` once — applies to every project on the machine:

```bash
mkdir -p ~/.config/docgen
cat > ~/.config/docgen/.env <<EOF
VLLM_BASE_URL=http://<your-host>:30000/v1
BATCH_SIZE=4
EOF
```

### Project-level config

Create a `.env` at the root of any project to override global values:

```
VLLM_BASE_URL=http://<your-host>:30000/v1
BATCH_SIZE=4
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `VLLM_BASE_URL` | `http://localhost:30000/v1` | vLLM server base URL |
| `BATCH_SIZE` | `4` | Max concurrent LLM requests |
| `VLLM_MODEL` | _(auto)_ | Override model ID; auto-detected from `/v1/models` if unset |

---

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
2. **Model detection** — uses `VLLM_MODEL` env var if set; otherwise queries `GET /v1/models`
3. **File resolution** — collects `.py` / `.ts` / `.tsx` files under the target (flat or recursive)
4. **AST parsing** — Python files are parsed with `tree-sitter-python`; TypeScript with `tree-sitter-typescript`. Files with all functions/classes documented are skipped (unless `--force`). Parsing runs in parallel via `rayon`.
5. **Batch LLM calls** — files are sent to vLLM concurrently, up to `BATCH_SIZE` in-flight requests via a `tokio` semaphore
6. **Git workflow** — creates a `docgen/<timestamp>` branch, writes patched files, commits, merges back into the original branch, deletes the feature branch. On failure the branch is left intact for manual inspection.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Pre-flight failure (dirty tree, vLLM unreachable) or git error |
| `2` | Nothing to do (no files found or all already documented) |

## Project structure

```
Cargo.toml                        # Workspace root
crates/
├── toolkit-core/                 # Shared: vLLM client, config, git, errors
└── docgen-cli/                   # docgen binary
    ├── src/
    │   ├── main.rs               # Orchestration
    │   ├── cli.rs                # Clap argument definitions
    │   ├── resolver.rs           # File discovery
    │   ├── detect.rs             # tree-sitter AST detection
    │   ├── process.rs            # Parallel LLM calls
    │   └── apply.rs              # Git branch/merge workflow
    └── Cargo.toml
pyproject.toml                    # maturin build — uv run docgen → Rust binary
package.json                      # pnpm scripts + npm postinstall binary download
.env.example                      # VLLM_BASE_URL, BATCH_SIZE
```

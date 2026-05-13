# ai-devops-toolkit

A collection of AI-powered DevOps tools for WillIsback projects, backed by a self-hosted [vLLM](https://github.com/vllm-project/vllm) instance.

The tools are written in **Rust** (Cargo Workspace) and distributed as native binaries — fast startup, no Python runtime required at run time.

---

## Tools

### `code-review` — GitHub Action

Reviews a Pull Request diff and posts a structured Markdown comment on the PR. Downloads a pre-compiled Rust binary from GitHub Releases — no `setup-python` or `pip install` step.

```yaml
- uses: WillIsback/ai-devops-toolkit/code-review@main
  with:
    vllm-url: ${{ secrets.VLLM_URL }}
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

→ [Full documentation](docs/code-review.md)

---

### `docgen` — CLI

Generates and inserts mkdocs/tsdoc docstrings into TypeScript and Python files using tree-sitter AST parsing. Distributed as a pre-compiled Rust binary — no Python runtime required.

**Install via pnpm/npm:**

```bash
pnpm add -D WillIsback/ai-devops-toolkit
# or
npm install --save-dev WillIsback/ai-devops-toolkit
```

The postinstall script downloads the correct binary for your platform from GitHub Releases into `node_modules/.bin/docgen`.

**Usage:**

```bash
# Run via pnpm exec (after install as a dependency)
pnpm exec docgen src/
pnpm exec docgen src/ --recursive
pnpm exec docgen path/to/file.ts --force
pnpm exec docgen path/to/file.ts --format tsdoc

# Or add to your package.json scripts:
# "docgen": "docgen"
# then: pnpm run docgen -- src/
```

**Options:**

| Flag | Short | Description |
|------|-------|-------------|
| `--recursive` | `-r` | Recurse into subdirectories |
| `--force` | | Regenerate existing docstrings |
| `--format` | | Force docstring format: `mkdocs` or `tsdoc` (auto-detected if omitted) |

→ [Full documentation](docs/docgen.md)

---

## Prerequisites

Both tools share the same vLLM backend:

- A running vLLM instance accessible from your machine or CI runner
- Model is auto-detected via `GET /v1/models` — no manual configuration needed
- Set `VLLM_MODEL` env var to skip auto-detection and use a specific model ID

## Setup

```bash
# Copy and configure environment
cp .env.example .env
# Set VLLM_BASE_URL in .env
```

`.env` files are loaded automatically — project `.env` overrides `~/.config/docgen/.env`.

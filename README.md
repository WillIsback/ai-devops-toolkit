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

Generates and inserts mkdocs/tsdoc docstrings into Python and TypeScript files using tree-sitter AST parsing. Runs locally via `uv` or `pnpm`, with parallel batch processing and a safe git branch workflow.

```bash
uv run docgen src/ --recursive
uv run docgen path/to/file.py --force
pnpm run docgen -- src/
```

→ [Full documentation](docs/docgen.md)

---

## Prerequisites

Both tools share the same vLLM backend:

- A running vLLM instance accessible from your machine or CI runner
- Model is auto-detected via `GET /v1/models` — no manual configuration needed
- Set `VLLM_MODEL` env var to skip auto-detection and use a specific model ID

## Setup

```bash
# Install the docgen binary via uv (maturin builds the Rust binary)
uv sync

# Copy and configure environment
cp .env.example .env
# Set VLLM_BASE_URL in .env
```

`.env` files are loaded automatically — project `.env` overrides `~/.config/docgen/.env`.

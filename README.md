# ai-devops-toolkit

A collection of AI-powered DevOps tools for WillIsback projects, backed by a self-hosted [vLLM](https://github.com/vllm-project/vllm) instance.

---

## Tools

### `code-review` — GitHub Action

Reviews a Pull Request diff and posts a structured Markdown comment on the PR.

```yaml
- uses: WillIsback/ai-devops-toolkit/code-review@main
  with:
    vllm-url: ${{ secrets.VLLM_URL }}
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

→ [Full documentation](docs/code-review.md)

---

### `docgen` — CLI

Generates and inserts mkdocs/tsdoc docstrings into Python and TypeScript files. Runs locally via `uv` or `pnpm`, with batch processing and a safe git branch workflow.

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
- For Qwen reasoning models, non-thinking mode is enabled automatically

## Setup

```bash
# Install Python dependencies (for docgen CLI)
uv sync

# Copy and configure environment
cp .env.example .env
# Set VLLM_BASE_URL in .env
```

# code-review

GitHub Composite Action that reviews a Pull Request diff using a self-hosted [vLLM](https://github.com/vllm-project/vllm) instance and posts a structured Markdown comment on the PR.

---

## Usage

```yaml
- name: Checkout code
  uses: actions/checkout@v4
  with:
    fetch-depth: 0

- name: AI Code Review
  uses: WillIsback/ai-devops-toolkit/code-review@main
  with:
    vllm-url: ${{ secrets.VLLM_URL }}
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `vllm-url` | yes | — | Base URL of the vLLM server (e.g. `http://<host>:30000/v1`) |
| `github-token` | yes | — | GitHub token for fetching the PR diff and posting the review comment |
| `vllm-model` | no | `""` | Override model ID — auto-detected from `/v1/models` if empty |
| `vllm-timeout` | no | `120` | Total request timeout in seconds |
| `vllm-retries` | no | `2` | Number of retries on LLM request failure |

## Prerequisites

- A self-hosted GitHub Actions runner with network access to your vLLM instance
- A repository or organisation secret `VLLM_URL` set to your vLLM endpoint

## How it works

1. Fetches the PR diff via the GitHub API
2. Splits large diffs into chunks that fit the model's context window
3. Queries `/v1/models` to auto-detect the loaded model (unless `vllm-model` is set)
4. Sends each chunk to the vLLM chat completions endpoint
5. Posts the aggregated review as a Markdown comment on the PR

## Qwen / reasoning models

For Qwen reasoning models, the action disables thinking mode per request so the final answer is returned directly in `message.content`:

```python
extra_body={
    "reasoning_effort": "none",
    "chat_template_kwargs": {"enable_thinking": False},
}
```

This prevents responses that contain only reasoning traces without the review content.

## Files

```
code-review/
├── action.yml     # GitHub Composite Action definition
├── reviewer.py    # Python script — fetches diff, calls vLLM, posts comment
└── tests/
    └── test_reviewer.py
```

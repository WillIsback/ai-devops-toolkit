# Docgen CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI tool (`docgen`) that generates and inserts mkdocs/tsdoc docstrings into Python and TypeScript files using a local vLLM instance, operating safely through short-lived git branches.

**Architecture:** Single `docgen/docgen.py` script with `typer` CLI. Loads config from `.env`, auto-detects vLLM model, filters files via AST (Python) or regex (TypeScript), calls vLLM in async batches of `BATCH_SIZE`, then isolates all file edits in a `docgen/<timestamp>` git branch that is merged back and deleted.

**Tech Stack:** Python 3.11+, typer, openai (AsyncOpenAI), httpx, python-dotenv, gitpython, pytest

---

## File Structure

```
ai-devops-toolkit/
├── pyproject.toml                    CREATE — uv project, script entry point, deps
├── package.json                      CREATE — pnpm scripts wrapper
├── .env.example                      CREATE — VLLM_BASE_URL, BATCH_SIZE
├── docgen/
│   ├── __init__.py                   CREATE — empty, makes docgen a package
│   └── docgen.py                     CREATE — all logic: config, preflight, parse, LLM, git, CLI
└── docgen/tests/
    ├── __init__.py                   CREATE — empty
    └── test_docgen.py                CREATE — all unit tests
```

---

## Task 1: Scaffold project structure

**Files:**
- Create: `pyproject.toml`
- Create: `package.json`
- Create: `.env.example`
- Create: `docgen/__init__.py`
- Create: `docgen/docgen.py` (skeleton)
- Create: `docgen/tests/__init__.py`
- Create: `docgen/tests/test_docgen.py` (skeleton)

- [ ] **Step 1: Create `pyproject.toml` at the repo root**

```toml
[project]
name = "ai-devops-toolkit"
version = "0.1.0"
description = "AI DevOps Toolkit"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "openai>=1.0",
    "httpx>=0.27",
    "python-dotenv>=1.0",
    "gitpython>=3.1",
    "pytest>=8.0",
]

[project.scripts]
docgen = "docgen.docgen:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["docgen"]

[tool.pytest.ini_options]
testpaths = ["docgen/tests", "code-review/tests"]
```

- [ ] **Step 2: Create `package.json` at the repo root**

```json
{
  "name": "ai-devops-toolkit",
  "scripts": {
    "docgen": "uv run docgen"
  }
}
```

- [ ] **Step 3: Create `.env.example`**

```
VLLM_BASE_URL=http://192.168.x.x:30000/v1
BATCH_SIZE=4
```

- [ ] **Step 4: Create `docgen/__init__.py`**

Empty file.

- [ ] **Step 5: Create skeleton `docgen/docgen.py`**

```python
#!/usr/bin/env python3
"""
Docgen CLI — generates docstrings for Python and TypeScript files
using a locally-hosted vLLM instance.
"""

import ast
import asyncio
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import git
import httpx
import typer
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

VLLM_BASE_URL: str = os.getenv("VLLM_BASE_URL", "http://localhost:30000/v1")
BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "4"))
VLLM_CONNECT_TIMEOUT: int = 5

app = typer.Typer(help="Generate docstrings using a local vLLM instance.")
```

- [ ] **Step 6: Create `docgen/tests/__init__.py`**

Empty file.

- [ ] **Step 7: Create skeleton `docgen/tests/test_docgen.py`**

```python
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
```

- [ ] **Step 8: Install dependencies**

```bash
uv sync
```

Expected: resolves and installs all deps, no errors.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml package.json .env.example docgen/
git commit -m "feat: scaffold docgen CLI project structure"
```

---

## Task 2: Config loading

**Files:**
- Modify: `docgen/docgen.py` — add `get_config()`
- Modify: `docgen/tests/test_docgen.py` — add `TestGetConfig`

- [ ] **Step 1: Write the failing test**

Add to `docgen/tests/test_docgen.py`:

```python
import importlib
from unittest.mock import patch


class TestGetConfig:
    def test_returns_defaults_when_env_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            import docgen.docgen as m
            importlib.reload(m)
            cfg = m.get_config()
        assert cfg["batch_size"] == 4
        assert "localhost" in cfg["vllm_base_url"]

    def test_reads_vllm_base_url_from_env(self):
        with patch.dict(os.environ, {"VLLM_BASE_URL": "http://myserver:8000/v1", "BATCH_SIZE": "4"}):
            import docgen.docgen as m
            importlib.reload(m)
            cfg = m.get_config()
        assert cfg["vllm_base_url"] == "http://myserver:8000/v1"

    def test_reads_batch_size_from_env(self):
        with patch.dict(os.environ, {"VLLM_BASE_URL": "http://x:1/v1", "BATCH_SIZE": "8"}):
            import docgen.docgen as m
            importlib.reload(m)
            cfg = m.get_config()
        assert cfg["batch_size"] == 8
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest docgen/tests/test_docgen.py::TestGetConfig -v
```

Expected: FAIL — `AttributeError: module 'docgen.docgen' has no attribute 'get_config'`

- [ ] **Step 3: Implement `get_config()` in `docgen/docgen.py`**

```python
def get_config() -> dict:
    return {
        "vllm_base_url": VLLM_BASE_URL,
        "batch_size": BATCH_SIZE,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest docgen/tests/test_docgen.py::TestGetConfig -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add docgen/docgen.py docgen/tests/test_docgen.py
git commit -m "feat: add config loading with VLLM_BASE_URL and BATCH_SIZE"
```

---

## Task 3: Pre-flight checks

**Files:**
- Modify: `docgen/docgen.py` — add `check_dirty_tree()`, `check_vllm_reachable()`
- Modify: `docgen/tests/test_docgen.py` — add `TestCheckDirtyTree`, `TestCheckVllmReachable`

- [ ] **Step 1: Write the failing tests**

Add to `docgen/tests/test_docgen.py`:

```python
from unittest.mock import MagicMock, patch


class TestCheckDirtyTree:
    def test_returns_empty_list_when_clean(self):
        mock_repo = MagicMock()
        mock_repo.index.diff.return_value = []
        mock_repo.untracked_files = []
        with patch("docgen.docgen.git.Repo", return_value=mock_repo):
            import docgen.docgen as m
            result = m.check_dirty_tree(Path("."))
        assert result == []

    def test_returns_modified_files_when_dirty(self):
        mock_diff = MagicMock()
        mock_diff.a_path = "src/foo.py"
        mock_repo = MagicMock()
        mock_repo.index.diff.return_value = [mock_diff]
        mock_repo.untracked_files = ["src/bar.py"]
        with patch("docgen.docgen.git.Repo", return_value=mock_repo):
            import docgen.docgen as m
            result = m.check_dirty_tree(Path("."))
        assert "src/foo.py" in result
        assert "src/bar.py" in result


class TestCheckVllmReachable:
    def test_returns_true_when_reachable(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        with patch("docgen.docgen.httpx.get", return_value=mock_response):
            import docgen.docgen as m
            assert m.check_vllm_reachable("http://localhost:30000/v1") is True

    def test_returns_false_on_connection_error(self):
        with patch("docgen.docgen.httpx.get", side_effect=Exception("timeout")):
            import docgen.docgen as m
            assert m.check_vllm_reachable("http://localhost:30000/v1") is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest docgen/tests/test_docgen.py::TestCheckDirtyTree docgen/tests/test_docgen.py::TestCheckVllmReachable -v
```

Expected: FAIL — functions not defined.

- [ ] **Step 3: Implement `check_dirty_tree()` and `check_vllm_reachable()` in `docgen/docgen.py`**

```python
def check_dirty_tree(repo_path: Path = Path(".")) -> list[str]:
    """Return list of modified/untracked files; empty if working tree is clean."""
    repo = git.Repo(repo_path, search_parent_directories=True)
    modified = [item.a_path for item in repo.index.diff(None)]
    return modified + list(repo.untracked_files)


def check_vllm_reachable(base_url: str) -> bool:
    """Return True if the vLLM /v1/models endpoint responds."""
    try:
        url = base_url.rstrip("/")
        if url.endswith("/v1"):
            url = url[:-3]
        httpx.get(f"{url}/v1/models", timeout=VLLM_CONNECT_TIMEOUT).raise_for_status()
        return True
    except Exception:
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest docgen/tests/test_docgen.py::TestCheckDirtyTree docgen/tests/test_docgen.py::TestCheckVllmReachable -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add docgen/docgen.py docgen/tests/test_docgen.py
git commit -m "feat: add pre-flight dirty-tree and vLLM reachability checks"
```

---

## Task 4: Model detection

**Files:**
- Modify: `docgen/docgen.py` — add `detect_model()`
- Modify: `docgen/tests/test_docgen.py` — add `TestDetectModel`

- [ ] **Step 1: Write the failing tests**

Add to `docgen/tests/test_docgen.py`:

```python
class TestDetectModel:
    def test_returns_first_model_id(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": [{"id": "Qwen/Qwen3-30B-A3B"}]}
        with patch("docgen.docgen.httpx.get", return_value=mock_response):
            import docgen.docgen as m
            assert m.detect_model("http://localhost:30000/v1") == "Qwen/Qwen3-30B-A3B"

    def test_returns_none_when_no_models(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": []}
        with patch("docgen.docgen.httpx.get", return_value=mock_response):
            import docgen.docgen as m
            assert m.detect_model("http://localhost:30000/v1") is None

    def test_returns_none_on_error(self):
        with patch("docgen.docgen.httpx.get", side_effect=Exception("conn refused")):
            import docgen.docgen as m
            assert m.detect_model("http://localhost:30000/v1") is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest docgen/tests/test_docgen.py::TestDetectModel -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `detect_model()` in `docgen/docgen.py`**

```python
def detect_model(base_url: str) -> Optional[str]:
    """Query /v1/models and return the first available model ID."""
    try:
        url = base_url.rstrip("/")
        if url.endswith("/v1"):
            url = url[:-3]
        response = httpx.get(f"{url}/v1/models", timeout=VLLM_CONNECT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if data.get("data"):
            model_id = data["data"][0]["id"]
            typer.echo(f"📦 Auto-detected model: {model_id}")
            return model_id
        return None
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest docgen/tests/test_docgen.py::TestDetectModel -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add docgen/docgen.py docgen/tests/test_docgen.py
git commit -m "feat: add vLLM model auto-detection"
```

---

## Task 5: File resolution

**Files:**
- Modify: `docgen/docgen.py` — add `resolve_files()`
- Modify: `docgen/tests/test_docgen.py` — add `TestResolveFiles`

- [ ] **Step 1: Write the failing tests**

Add to `docgen/tests/test_docgen.py`:

```python
import tempfile


class TestResolveFiles:
    def _make_tree(self, tmp: Path, structure: dict) -> None:
        for name, content in structure.items():
            p = tmp / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)

    def test_single_python_file(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "foo.py"
            f.write_text("x = 1")
            import docgen.docgen as m
            assert m.resolve_files(f) == [f]

    def test_single_non_matching_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "README.md"
            f.write_text("# docs")
            import docgen.docgen as m
            assert m.resolve_files(f) == []

    def test_flat_folder_no_recursion(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.py").write_text("")
            (root / "b.ts").write_text("")
            sub = root / "sub"
            sub.mkdir()
            (sub / "c.py").write_text("")
            import docgen.docgen as m
            result = m.resolve_files(root, recursive=False)
            names = {f.name for f in result}
            assert names == {"a.py", "b.ts"}

    def test_recursive_folder(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.py").write_text("")
            sub = root / "sub"
            sub.mkdir()
            (sub / "c.py").write_text("")
            import docgen.docgen as m
            result = m.resolve_files(root, recursive=True)
            names = {f.name for f in result}
            assert names == {"a.py", "c.py"}

    def test_tsx_files_included(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "Button.tsx"
            f.write_text("")
            import docgen.docgen as m
            assert m.resolve_files(f) == [f]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest docgen/tests/test_docgen.py::TestResolveFiles -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `resolve_files()` in `docgen/docgen.py`**

```python
def resolve_files(target: Path, recursive: bool = False) -> list[Path]:
    """Return .py/.ts/.tsx files under target. Flat by default, recursive if flagged."""
    extensions = {".py", ".ts", ".tsx"}
    if target.is_file():
        return [target] if target.suffix in extensions else []
    pattern = "**/*" if recursive else "*"
    return sorted(f for f in target.glob(pattern) if f.is_file() and f.suffix in extensions)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest docgen/tests/test_docgen.py::TestResolveFiles -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add docgen/docgen.py docgen/tests/test_docgen.py
git commit -m "feat: add file resolution with flat/recursive mode"
```

---

## Task 6: Python docstring detection

**Files:**
- Modify: `docgen/docgen.py` — add `python_has_missing_docstrings()`
- Modify: `docgen/tests/test_docgen.py` — add `TestPythonHasMissingDocstrings`

- [ ] **Step 1: Write the failing tests**

Add to `docgen/tests/test_docgen.py`:

```python
class TestPythonHasMissingDocstrings:
    def test_function_without_docstring_returns_true(self):
        source = "def foo():\n    return 1\n"
        import docgen.docgen as m
        assert m.python_has_missing_docstrings(source) is True

    def test_function_with_docstring_returns_false(self):
        source = 'def foo():\n    """Does foo."""\n    return 1\n'
        import docgen.docgen as m
        assert m.python_has_missing_docstrings(source) is False

    def test_class_without_docstring_returns_true(self):
        source = "class Bar:\n    pass\n"
        import docgen.docgen as m
        assert m.python_has_missing_docstrings(source) is True

    def test_class_with_docstring_returns_false(self):
        source = 'class Bar:\n    """Bar class."""\n    pass\n'
        import docgen.docgen as m
        assert m.python_has_missing_docstrings(source) is False

    def test_force_true_returns_true_even_when_documented(self):
        source = 'def foo():\n    """Has docstring."""\n    return 1\n'
        import docgen.docgen as m
        assert m.python_has_missing_docstrings(source, force=True) is True

    def test_invalid_syntax_returns_false(self):
        source = "def foo(:\n    pass\n"
        import docgen.docgen as m
        assert m.python_has_missing_docstrings(source) is False

    def test_no_functions_or_classes_returns_false(self):
        source = "x = 1\ny = 2\n"
        import docgen.docgen as m
        assert m.python_has_missing_docstrings(source) is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest docgen/tests/test_docgen.py::TestPythonHasMissingDocstrings -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `python_has_missing_docstrings()` in `docgen/docgen.py`**

```python
def python_has_missing_docstrings(source: str, force: bool = False) -> bool:
    """Return True if source contains functions/classes that need docstrings."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            has_doc = (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            )
            if not has_doc or force:
                return True
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest docgen/tests/test_docgen.py::TestPythonHasMissingDocstrings -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add docgen/docgen.py docgen/tests/test_docgen.py
git commit -m "feat: add Python AST-based docstring detection"
```

---

## Task 7: TypeScript docstring detection

**Files:**
- Modify: `docgen/docgen.py` — add `ts_has_missing_docstrings()`
- Modify: `docgen/tests/test_docgen.py` — add `TestTsHasMissingDocstrings`

- [ ] **Step 1: Write the failing tests**

Add to `docgen/tests/test_docgen.py`:

```python
class TestTsHasMissingDocstrings:
    def test_function_without_jsdoc_returns_true(self):
        source = "function greet(name: string): string {\n  return name;\n}\n"
        import docgen.docgen as m
        assert m.ts_has_missing_docstrings(source) is True

    def test_function_with_jsdoc_returns_false(self):
        source = "/**\n * Greets a user.\n */\nfunction greet(name: string): string {\n  return name;\n}\n"
        import docgen.docgen as m
        assert m.ts_has_missing_docstrings(source) is False

    def test_class_without_jsdoc_returns_true(self):
        source = "class MyService {\n  run() {}\n}\n"
        import docgen.docgen as m
        assert m.ts_has_missing_docstrings(source) is True

    def test_class_with_jsdoc_returns_false(self):
        source = "/**\n * MyService class.\n */\nclass MyService {\n  run() {}\n}\n"
        import docgen.docgen as m
        assert m.ts_has_missing_docstrings(source) is False

    def test_exported_function_without_jsdoc_returns_true(self):
        source = "export function add(a: number, b: number): number {\n  return a + b;\n}\n"
        import docgen.docgen as m
        assert m.ts_has_missing_docstrings(source) is True

    def test_force_returns_true_even_when_documented(self):
        source = "/**\n * Greets.\n */\nfunction greet() {}\n"
        import docgen.docgen as m
        assert m.ts_has_missing_docstrings(source, force=True) is True

    def test_no_declarations_returns_false(self):
        source = "const x = 1;\nconst y = 2;\n"
        import docgen.docgen as m
        assert m.ts_has_missing_docstrings(source) is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest docgen/tests/test_docgen.py::TestTsHasMissingDocstrings -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `ts_has_missing_docstrings()` in `docgen/docgen.py`**

```python
def ts_has_missing_docstrings(source: str, force: bool = False) -> bool:
    """Return True if source contains functions/classes that need JSDoc."""
    lines = source.splitlines()
    declaration_re = re.compile(
        r'^(?:export\s+)?(?:async\s+)?(?:function\s+\w+|class\s+\w+)'
    )
    for i, line in enumerate(lines):
        if declaration_re.match(line.strip()):
            prev_non_empty = next(
                (lines[j].strip() for j in range(i - 1, -1, -1) if lines[j].strip()),
                ""
            )
            has_jsdoc = prev_non_empty.endswith("*/")
            if not has_jsdoc or force:
                return True
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest docgen/tests/test_docgen.py::TestTsHasMissingDocstrings -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add docgen/docgen.py docgen/tests/test_docgen.py
git commit -m "feat: add TypeScript regex-based docstring detection"
```

---

## Task 8: `needs_docstrings` dispatcher and format helpers

**Files:**
- Modify: `docgen/docgen.py` — add `needs_docstrings()`, `get_format()`, `get_language()`
- Modify: `docgen/tests/test_docgen.py` — add `TestNeedsDocstrings`, `TestGetFormat`

- [ ] **Step 1: Write the failing tests**

Add to `docgen/tests/test_docgen.py`:

```python
class TestNeedsDocstrings:
    def test_routes_py_to_python_parser(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "foo.py"
            f.write_text("def bar():\n    return 1\n")
            import docgen.docgen as m
            assert m.needs_docstrings(f) is True

    def test_routes_ts_to_ts_parser(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "foo.ts"
            f.write_text("function greet() {}\n")
            import docgen.docgen as m
            assert m.needs_docstrings(f) is True

    def test_unknown_extension_returns_false(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "foo.rb"
            f.write_text("def bar; end\n")
            import docgen.docgen as m
            assert m.needs_docstrings(f) is False


class TestGetFormat:
    def test_py_defaults_to_mkdocs(self):
        import docgen.docgen as m
        assert m.get_format(Path("foo.py"), None) == "mkdocs"

    def test_ts_defaults_to_tsdoc(self):
        import docgen.docgen as m
        assert m.get_format(Path("foo.ts"), None) == "tsdoc"

    def test_tsx_defaults_to_tsdoc(self):
        import docgen.docgen as m
        assert m.get_format(Path("foo.tsx"), None) == "tsdoc"

    def test_explicit_format_overrides(self):
        import docgen.docgen as m
        assert m.get_format(Path("foo.py"), "tsdoc") == "tsdoc"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest docgen/tests/test_docgen.py::TestNeedsDocstrings docgen/tests/test_docgen.py::TestGetFormat -v
```

Expected: FAIL.

- [ ] **Step 3: Implement in `docgen/docgen.py`**

```python
def get_format(file: Path, fmt: Optional[str]) -> str:
    """Return docstring format: explicit override or auto-detected from extension."""
    if fmt:
        return fmt
    return "mkdocs" if file.suffix == ".py" else "tsdoc"


def get_language(file: Path) -> str:
    return "Python" if file.suffix == ".py" else "TypeScript"


def needs_docstrings(file: Path, force: bool = False) -> bool:
    """Return True if this file has functions/classes that need docstrings."""
    try:
        source = file.read_text()
    except OSError:
        return False
    if file.suffix == ".py":
        return python_has_missing_docstrings(source, force)
    if file.suffix in {".ts", ".tsx"}:
        return ts_has_missing_docstrings(source, force)
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest docgen/tests/test_docgen.py::TestNeedsDocstrings docgen/tests/test_docgen.py::TestGetFormat -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add docgen/docgen.py docgen/tests/test_docgen.py
git commit -m "feat: add needs_docstrings dispatcher and format helpers"
```

---

## Task 9: Async LLM client and batch processor

**Files:**
- Modify: `docgen/docgen.py` — add `generate_docstrings_async()`, `process_files_async()`
- Modify: `docgen/tests/test_docgen.py` — add `TestGenerateDocstrings`, `TestProcessFilesAsync`

- [ ] **Step 1: Write the failing tests**

Add to `docgen/tests/test_docgen.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


class TestGenerateDocstrings:
    def test_returns_patched_source_on_success(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "foo.py"
            f.write_text("def bar():\n    return 1\n")

            mock_client = MagicMock()
            mock_client.chat = MagicMock()
            mock_client.chat.completions = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content='def bar():\n    """Returns 1."""\n    return 1\n'))]
            ))

            import docgen.docgen as m
            sem = asyncio.Semaphore(4)
            result_path, result_content = asyncio.run(
                m.generate_docstrings_async(mock_client, sem, f, "mkdocs", False, "test-model")
            )
        assert result_path == f
        assert '"""Returns 1."""' in result_content

    def test_returns_none_on_llm_error(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "foo.py"
            f.write_text("def bar():\n    return 1\n")

            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=Exception("LLM down"))

            import docgen.docgen as m
            sem = asyncio.Semaphore(4)
            result_path, result_content = asyncio.run(
                m.generate_docstrings_async(mock_client, sem, f, "mkdocs", False, "test-model")
            )
        assert result_path == f
        assert result_content is None


class TestProcessFilesAsync:
    def test_returns_dict_of_patched_files(self):
        with tempfile.TemporaryDirectory() as d:
            f1 = Path(d) / "a.py"
            f2 = Path(d) / "b.py"
            f1.write_text("def a(): pass")
            f2.write_text("def b(): pass")

            patched_a = 'def a():\n    """Does a."""\n    pass'
            patched_b = 'def b():\n    """Does b."""\n    pass'

            async def fake_generate(client, sem, file, fmt, force, model):
                return (file, patched_a if file.name == "a.py" else patched_b)

            import docgen.docgen as m
            with patch.object(m, "generate_docstrings_async", side_effect=fake_generate):
                result = asyncio.run(
                    m.process_files_async([f1, f2], None, False, "test-model", 4, "http://x/v1")
                )
        assert result[f1] == patched_a
        assert result[f2] == patched_b

    def test_skips_files_where_llm_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            f1 = Path(d) / "a.py"
            f1.write_text("def a(): pass")

            async def fake_generate(client, sem, file, fmt, force, model):
                return (file, None)

            import docgen.docgen as m
            with patch.object(m, "generate_docstrings_async", side_effect=fake_generate):
                result = asyncio.run(
                    m.process_files_async([f1], None, False, "test-model", 4, "http://x/v1")
                )
        assert result == {}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest docgen/tests/test_docgen.py::TestGenerateDocstrings docgen/tests/test_docgen.py::TestProcessFilesAsync -v
```

Expected: FAIL.

- [ ] **Step 3: Implement in `docgen/docgen.py`**

```python
async def generate_docstrings_async(
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
    file: Path,
    fmt: str,
    force: bool,
    model: str,
) -> tuple[Path, Optional[str]]:
    """Send file source to vLLM and return (file, patched_source) or (file, None) on error."""
    source = file.read_text()
    language = get_language(file)
    action = (
        "Replace all existing docstrings and add missing ones"
        if force
        else "Add docstrings to all functions and classes that are missing them"
    )
    prompt = (
        f"{action} using {fmt} format in the following {language} source code. "
        f"Return ONLY the complete patched source code with no explanation and no markdown fences.\n\n"
        f"{source}"
    )
    async with semaphore:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                extra_body={
                    "reasoning_effort": "none",
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            )
            return file, response.choices[0].message.content
        except Exception as e:
            typer.echo(f"  ⚠️  LLM error for {file.name}: {e}", err=True)
            return file, None


async def process_files_async(
    files: list[Path],
    fmt: Optional[str],
    force: bool,
    model: str,
    batch_size: int,
    base_url: str,
) -> dict[Path, str]:
    """Process files in parallel (up to batch_size concurrent LLM calls)."""
    client = AsyncOpenAI(base_url=base_url, api_key="none")
    semaphore = asyncio.Semaphore(batch_size)
    tasks = [
        generate_docstrings_async(client, semaphore, f, get_format(f, fmt), force, model)
        for f in files
    ]
    results = await asyncio.gather(*tasks)
    return {path: content for path, content in results if content is not None}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest docgen/tests/test_docgen.py::TestGenerateDocstrings docgen/tests/test_docgen.py::TestProcessFilesAsync -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add docgen/docgen.py docgen/tests/test_docgen.py
git commit -m "feat: add async LLM client and batch processor"
```

---

## Task 10: Git workflow

**Files:**
- Modify: `docgen/docgen.py` — add `apply_with_git()`
- Modify: `docgen/tests/test_docgen.py` — add `TestApplyWithGit`

- [ ] **Step 1: Write the failing tests**

Add to `docgen/tests/test_docgen.py`:

```python
class TestApplyWithGit:
    def test_creates_branch_writes_files_merges_and_deletes(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "foo.py"
            patched = {f: 'def foo():\n    """Docs."""\n    pass\n'}

            mock_repo = MagicMock()
            mock_repo.active_branch.name = "main"

            with patch("docgen.docgen.git.Repo", return_value=mock_repo):
                import docgen.docgen as m
                m.apply_with_git(patched, Path(d))

            # branch created
            branch_call = mock_repo.git.checkout.call_args_list[0]
            assert branch_call.args[0] == "-b"
            assert branch_call.args[1].startswith("docgen/")
            # commit made
            mock_repo.git.commit.assert_called_once()
            # merged back
            mock_repo.git.merge.assert_called_once()
            # branch deleted
            mock_repo.git.branch.assert_called_with("-d", mock_repo.git.checkout.call_args_list[0].args[1])
            # file written
            assert f.read_text() == patched[f]

    def test_leaves_branch_on_merge_failure(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "foo.py"
            f.write_text("")
            patched = {f: "patched"}

            mock_repo = MagicMock()
            mock_repo.active_branch.name = "feature/x"
            mock_repo.git.merge.side_effect = Exception("conflict")

            with patch("docgen.docgen.git.Repo", return_value=mock_repo):
                import docgen.docgen as m
                with pytest.raises(Exception, match="conflict"):
                    m.apply_with_git(patched, Path(d))

            # checkout back to original branch called even on failure
            checkout_calls = [c.args for c in mock_repo.git.checkout.call_args_list]
            assert any("feature/x" in str(c) for c in checkout_calls)
```

- [ ] **Step 2: Run tests to verify they fail**

Add `import pytest` to the top of `test_docgen.py`, then:

```bash
uv run pytest docgen/tests/test_docgen.py::TestApplyWithGit -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `apply_with_git()` in `docgen/docgen.py`**

```python
def apply_with_git(patched: dict[Path, str], repo_path: Path = Path(".")) -> None:
    """Write patched files in a short-lived git branch and merge back."""
    repo = git.Repo(repo_path, search_parent_directories=True)
    branch_name = f"docgen/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    original_branch = repo.active_branch.name

    repo.git.checkout("-b", branch_name)
    try:
        for path, content in patched.items():
            path.write_text(content)
        repo.git.add("--", *[str(p) for p in patched.keys()])
        repo.git.commit("-m", f"docs: add docstrings via docgen")
        repo.git.checkout(original_branch)
        repo.git.merge(branch_name, "--no-ff", "-m", f"docs: merge {branch_name}")
    except Exception as e:
        typer.echo(f"  ✗ Git error: {e}", err=True)
        typer.echo(f"  Branch '{branch_name}' left for manual inspection.", err=True)
        try:
            repo.git.checkout(original_branch)
        except Exception:
            pass
        raise
    finally:
        try:
            repo.git.branch("-d", branch_name)
        except Exception:
            pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest docgen/tests/test_docgen.py::TestApplyWithGit -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add docgen/docgen.py docgen/tests/test_docgen.py
git commit -m "feat: add git branch/merge workflow for safe file edits"
```

---

## Task 11: CLI wiring and entry points

**Files:**
- Modify: `docgen/docgen.py` — add `main()` typer command
- Modify: `docgen/tests/test_docgen.py` — add `TestCli`

- [ ] **Step 1: Write the failing tests**

Add to `docgen/tests/test_docgen.py`:

```python
from typer.testing import CliRunner


class TestCli:
    def _runner(self):
        import docgen.docgen as m
        return CliRunner(), m.app

    def test_exits_1_on_dirty_tree(self):
        runner, app = self._runner()
        with patch("docgen.docgen.check_dirty_tree", return_value=["src/foo.py"]):
            result = runner.invoke(app, ["src/"])
        assert result.exit_code == 1
        assert "uncommitted changes" in result.output

    def test_exits_1_when_vllm_unreachable(self):
        runner, app = self._runner()
        with patch("docgen.docgen.check_dirty_tree", return_value=[]), \
             patch("docgen.docgen.check_vllm_reachable", return_value=False):
            result = runner.invoke(app, ["src/"])
        assert result.exit_code == 1
        assert "not reachable" in result.output

    def test_exits_1_when_model_not_detected(self):
        runner, app = self._runner()
        with patch("docgen.docgen.check_dirty_tree", return_value=[]), \
             patch("docgen.docgen.check_vllm_reachable", return_value=True), \
             patch("docgen.docgen.detect_model", return_value=None):
            result = runner.invoke(app, ["src/"])
        assert result.exit_code == 1

    def test_exits_2_when_no_files_found(self):
        runner, app = self._runner()
        with tempfile.TemporaryDirectory() as d:
            with patch("docgen.docgen.check_dirty_tree", return_value=[]), \
                 patch("docgen.docgen.check_vllm_reachable", return_value=True), \
                 patch("docgen.docgen.detect_model", return_value="test-model"):
                result = runner.invoke(app, [d])
        assert result.exit_code == 2

    def test_exits_2_when_all_files_already_documented(self):
        runner, app = self._runner()
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "foo.py"
            f.write_text('def foo():\n    """Already documented."""\n    pass\n')
            with patch("docgen.docgen.check_dirty_tree", return_value=[]), \
                 patch("docgen.docgen.check_vllm_reachable", return_value=True), \
                 patch("docgen.docgen.detect_model", return_value="test-model"):
                result = runner.invoke(app, [str(f)])
        assert result.exit_code == 2

    def test_exits_0_on_success(self):
        runner, app = self._runner()
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "foo.py"
            f.write_text("def foo():\n    return 1\n")
            with patch("docgen.docgen.check_dirty_tree", return_value=[]), \
                 patch("docgen.docgen.check_vllm_reachable", return_value=True), \
                 patch("docgen.docgen.detect_model", return_value="test-model"), \
                 patch("docgen.docgen.process_files_async", new_callable=AsyncMock,
                       return_value={f: 'def foo():\n    """Docs."""\n    return 1\n'}), \
                 patch("docgen.docgen.apply_with_git"):
                result = runner.invoke(app, [str(f)])
        assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest docgen/tests/test_docgen.py::TestCli -v
```

Expected: FAIL — `main` not defined.

- [ ] **Step 3: Implement `main()` in `docgen/docgen.py`**

```python
@app.command()
def main(
    target: Path = typer.Argument(..., help="File or folder to process"),
    fmt: Optional[str] = typer.Option(None, "--format", help="Docstring format: mkdocs, tsdoc (auto-detected if omitted)"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Recurse into subdirectories"),
    force: bool = typer.Option(False, "--force", help="Regenerate existing docstrings"),
) -> None:
    config = get_config()

    dirty = check_dirty_tree()
    if dirty:
        typer.echo("✗ Working tree has uncommitted changes. Commit or stash before running docgen:")
        for f in dirty:
            typer.echo(f"  {f}")
        raise typer.Exit(1)

    if not check_vllm_reachable(config["vllm_base_url"]):
        typer.echo(f"✗ vLLM not reachable at {config['vllm_base_url']}")
        raise typer.Exit(1)

    model = detect_model(config["vllm_base_url"])
    if not model:
        typer.echo("✗ Could not detect model from vLLM server")
        raise typer.Exit(1)

    files = resolve_files(target, recursive)
    if not files:
        typer.echo("⚠️  No Python or TypeScript files found.")
        raise typer.Exit(2)

    to_process = [f for f in files if needs_docstrings(f, force)]
    if not to_process:
        typer.echo("✓ Nothing to do — all files are already documented.")
        raise typer.Exit(2)

    typer.echo(f"📝 Processing {len(to_process)} file(s) in batches of {config['batch_size']}...")
    patched = asyncio.run(
        process_files_async(to_process, fmt, force, model, config["batch_size"], config["vllm_base_url"])
    )

    if not patched:
        typer.echo("⚠️  No files were successfully processed.")
        raise typer.Exit(1)

    typer.echo("🔀 Applying changes via git branch...")
    apply_with_git(patched)
    typer.echo(f"✓ Done. Docstrings added to {len(patched)} file(s).")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run all tests**

```bash
uv run pytest docgen/tests/test_docgen.py -v
```

Expected: all passed (no failures).

- [ ] **Step 5: Verify the CLI help works**

```bash
uv run docgen --help
```

Expected output includes: `target`, `--format`, `--recursive`, `--force` arguments listed with descriptions.

- [ ] **Step 6: Commit**

```bash
git add docgen/docgen.py docgen/tests/test_docgen.py
git commit -m "feat: wire typer CLI and entry points for docgen"
```

---

## Task 12: pnpm integration and final check

**Files:**
- Verify: `package.json` has `docgen` script
- Verify: `pyproject.toml` has correct entry point

- [ ] **Step 1: Verify `uv run docgen --help` works from repo root**

```bash
cd /path/to/ai-devops-toolkit && uv run docgen --help
```

Expected: typer help output showing all flags.

- [ ] **Step 2: Verify pnpm script works**

```bash
pnpm run docgen -- --help
```

Expected: same help output proxied through pnpm.

- [ ] **Step 3: Run full test suite one final time**

```bash
uv run pytest -v
```

Expected: all tests across `docgen/tests/` and `code-review/tests/` pass.

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete docgen CLI — docstring generator with vLLM batch processing"
```

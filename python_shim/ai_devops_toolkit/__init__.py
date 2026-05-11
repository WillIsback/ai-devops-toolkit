"""
Shim for ai-devops-toolkit — delegates to the compiled docgen Rust binary.
The actual binary is installed by maturin into the Python environment's bin dir.
"""
import subprocess
import sys
import shutil


def main() -> None:
    binary = shutil.which("docgen-bin") or shutil.which("docgen")
    if binary is None:
        print("Error: docgen binary not found in PATH. Run 'uv sync' to install.", file=sys.stderr)
        sys.exit(1)
    sys.exit(subprocess.call([binary] + sys.argv[1:]))

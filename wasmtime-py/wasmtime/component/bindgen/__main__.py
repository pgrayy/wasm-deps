"""CLI entry point for the WIT host bindgen.

Usage:
    python -m wasmtime.component.bindgen <wit-path> -o <out-dir>

Drives ``wasm-tools component wit --json``, parses the result into the typed
IR, and emits a Python *package* (one module per WIT interface plus an
``__init__.py`` that re-exports world-level types).

``-o`` is the output directory; it will be created if missing.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import _emit, _ir


def _dump_wit_ir(wit_path: Path) -> dict:
    result = subprocess.run(
        ["wasm-tools", "component", "wit", "--json", str(wit_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m wasmtime.component.bindgen",
        description="Generate wasmtime-py wire-shape Python types from a WIT package.",
    )
    parser.add_argument("wit_path", type=Path, help="Path to a WIT directory or file.")
    parser.add_argument(
        "-o", "--output", type=Path, required=True,
        help="Output directory for the generated package.",
    )
    args = parser.parse_args(argv)

    if not args.wit_path.exists():
        print(f"error: WIT path does not exist: {args.wit_path}", file=sys.stderr)
        return 1

    try:
        ir_json = _dump_wit_ir(args.wit_path)
    except FileNotFoundError:
        print("error: wasm-tools binary not found in PATH", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"error: wasm-tools failed:\n{exc.stderr}", file=sys.stderr)
        return 1

    ir = _ir.load(ir_json)
    files = _emit.emit_package(ir)

    out_dir: Path = args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    # Remove any previously-generated .py so deletions in the WIT propagate.
    for stale in out_dir.glob("*.py"):
        stale.unlink()
    for mod_name, content in files.items():
        (out_dir / f"{mod_name}.py").write_text(content)

    return 0


if __name__ == "__main__":
    sys.exit(main())

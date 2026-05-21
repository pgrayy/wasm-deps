"""CLI entry point for the WIT host bindgen.

Usage:
    python -m wasmtime.component.bindgen <wit-path> [-o <out.py>]

Drives ``wasm-tools component wit --json``, parses the result into the typed
IR, and emits a Python module that wasmtime-py accepts at the FFI boundary
without an additional marshaling layer.

If ``-o`` is omitted, the generated module is written to stdout.
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
        "-o", "--output", type=Path, default=None,
        help="Write the generated module to this path. Default: stdout.",
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
    src = _emit.emit_module(ir)

    if args.output is None:
        sys.stdout.write(src)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(src)

    return 0


if __name__ == "__main__":
    sys.exit(main())

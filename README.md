# wasm-deps

Forked WASM dependencies for the Strands Agents SDK.

## Contents

| Directory | Upstream | Purpose |
|-----------|----------|---------|
| `wasmtime/` | [bytecodealliance/wasmtime](https://github.com/bytecodealliance/wasmtime) | WASM runtime (Rust) |
| `wasmtime-py/` | [bytecodealliance/wasmtime-py](https://github.com/bytecodealliance/wasmtime-py) | Python bindings for wasmtime |

## Syncing with Upstream

Each directory is managed as a git subtree. To pull latest changes from upstream:

```bash
git subtree pull --prefix=wasmtime https://github.com/bytecodealliance/wasmtime.git main --squash
git subtree pull --prefix=wasmtime-py https://github.com/bytecodealliance/wasmtime-py.git main --squash
```

## Publishing

On GitHub Release, CI builds macOS wheels for wasmtime-py and attaches them as release assets.

Install from a release:

```bash
pip install https://github.com/pgrayy/wasm-deps/releases/download/v0.1.0/wasmtime-44.0.0-py3-none-macosx_11_0_arm64.whl
```

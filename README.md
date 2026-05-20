# wasm-deps

Forked WASM dependencies for the Strands Agents SDK.

## Contents

| Directory | Upstream | Purpose |
|-----------|----------|---------|
| `wasmtime/` | [bytecodealliance/wasmtime](https://github.com/bytecodealliance/wasmtime) | WASM runtime (Rust) |
| `wasmtime-py/` | [bytecodealliance/wasmtime-py](https://github.com/bytecodealliance/wasmtime-py) | Python bindings for wasmtime |
| `componentize-js/` | [bytecodealliance/ComponentizeJS](https://github.com/bytecodealliance/ComponentizeJS) | JS → WASM component compiler |
| `jco/` | [bytecodealliance/jco](https://github.com/bytecodealliance/jco) | JS toolchain for WebAssembly Components |

## Syncing with Upstream

Each directory is managed as a git subtree. To pull latest changes from upstream:

```bash
git subtree pull --prefix=wasmtime https://github.com/bytecodealliance/wasmtime.git main --squash
git subtree pull --prefix=wasmtime-py https://github.com/bytecodealliance/wasmtime-py.git main --squash
git subtree pull --prefix=componentize-js https://github.com/bytecodealliance/ComponentizeJS.git main --squash
git subtree pull --prefix=jco https://github.com/bytecodealliance/jco.git main --squash
```

## Contributing Fixes Upstream

To push changes from a directory back to the upstream repo:

```bash
git subtree push --prefix=wasmtime https://github.com/bytecodealliance/wasmtime.git my-fix-branch
```

Then open a PR on the upstream project from that branch.

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

## Releasing

Releases are triggered by publishing a GitHub Release. The release workflow builds a macOS arm64 C API tarball and a wasmtime-py wheel, attaches them to the release, and publishes the wheel to PyPI.

### Steps

1. Check the wasmtime version in the subtree:
   ```bash
   grep '^version' wasmtime/Cargo.toml
   ```

2. Update `wasmtime-py/VERSION` to match:
   ```bash
   echo "46.0.0" > wasmtime-py/VERSION
   ```

3. Update `WASMTIME_VERSION` in `wasmtime-py/ci/download-wasmtime.py` to the tag you're about to create (e.g., `v46.0.0`).

4. Commit and push to main:
   ```bash
   git add wasmtime-py/VERSION wasmtime-py/ci/download-wasmtime.py
   git commit -m "chore: bump versions to v46.0.0"
   git push
   ```

5. Create the release:
   ```bash
   gh release create v46.0.0 --title "v46.0.0" --notes "Wasmtime 46.0.0" --target main
   ```

6. Wait for the release workflow to complete. It will attach the tarball and wheel to the release and publish to PyPI.

### Install from a release

```bash
pip install https://github.com/pgrayy/wasm-deps/releases/download/v46.0.0/pgrayy_wasmtime-46.0.0-py3-none-macosx_11_0_arm64.whl
```

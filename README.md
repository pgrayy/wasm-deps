# wasm-deps

Forked dependencies for the Strands Agents SDK.

## Contents

| Directory | Upstream | Purpose |
|-----------|----------|---------|
| `wasmtime/` | [bytecodealliance/wasmtime](https://github.com/bytecodealliance/wasmtime) | WASM runtime (Rust) |
| `wasmtime-py/` | [bytecodealliance/wasmtime-py](https://github.com/bytecodealliance/wasmtime-py) | Python bindings for wasmtime |
| `aws-bedrock-token-generator-js/` | [aws/aws-bedrock-token-generator-js](https://github.com/aws/aws-bedrock-token-generator-js) | Bedrock bearer token generation (JS) |

## Syncing with Upstream

Each directory is a git subtree. Pull wasmtime before wasmtime-py (wasmtime-py may depend on new C API symbols).

```bash
git subtree pull --prefix=wasmtime https://github.com/bytecodealliance/wasmtime.git main --squash
git subtree pull --prefix=wasmtime-py https://github.com/bytecodealliance/wasmtime-py.git main --squash
git subtree pull --prefix=aws-bedrock-token-generator-js https://github.com/aws/aws-bedrock-token-generator-js.git main --squash
```

## Releasing

Releases use namespaced tags. The workflow detects which package to build based on the tag prefix.

| Tag prefix | Artifacts |
|------------|-----------|
| `wasmtime-v*` | macOS arm64 C API tarball, Python wheel (PyPI) |
| `token-gen-v*` | npm tarball (GitHub Release) |

### wasmtime-py

1. Update `wasmtime-py/VERSION` and `WASMTIME_VERSION` in `wasmtime-py/ci/download-wasmtime.py` to match the new tag.

2. Commit and push as a single commit (setuptools-git-versioning appends suffixes if commits exist after the VERSION change):
   ```bash
   git commit -am "chore: bump wasmtime-py to v<X.Y.Z>"
   git push
   ```

3. Create the release:
   ```bash
   gh release create wasmtime-v<X.Y.Z> --title "wasmtime-v<X.Y.Z>" --target $(git rev-parse HEAD)
   ```

Install:
```bash
pip install pgrayy-wasmtime
```

### aws-bedrock-token-generator-js

1. Update `version` in `aws-bedrock-token-generator-js/package.json`.

2. Commit and push:
   ```bash
   git commit -am "chore: bump token-gen to v<X.Y.Z>"
   git push
   ```

3. Create the release:
   ```bash
   gh release create token-gen-v<X.Y.Z> --title "token-gen-v<X.Y.Z>" --target $(git rev-parse HEAD)
   ```

Install from a release:
```bash
npm install https://github.com/pgrayy/wasm-deps/releases/download/token-gen-v<X.Y.Z>/aws-bedrock-token-generator-<X.Y.Z>.tgz
```

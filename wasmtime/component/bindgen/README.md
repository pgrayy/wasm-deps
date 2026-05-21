# wasmtime.component.bindgen

Generates Python classes from WIT that `wasmtime.component` accepts
directly at the FFI boundary — no separate marshaling layer between
user code and the wire.

Tracks [wasmtime-py issue #309][issue]. Replaces the previous host
bindgen, which was guest-shaped (snake_case, per-arm dataclasses) and
incompatible with the modern `wasmtime.component` API.

[issue]: https://github.com/bytecodealliance/wasmtime-py/issues/309

## Usage

```sh
python -m wasmtime.component.bindgen path/to/wit -o generated.py
```

`wasm-tools` must be on `PATH` — the bindgen drives
`wasm-tools component wit --json` to read WIT.

The generated module imports only `wasmtime.component` and is
freestanding.

## Wire-shape rules

| WIT shape            | Python representation                                                       |
|----------------------|-----------------------------------------------------------------------------|
| `record`             | class with kebab-case `__dict__` keys + snake_case property accessors       |
| `enum`               | `str` subclass; the kebab-case spelling IS the value                        |
| `variant` (tagged)   | `Variant(tag, payload)` via `Foo.arm(payload)` factories                    |
| `variant` (untagged) | bare payload via `Foo.arm(payload)`; `None` for unit arms                   |
| `option<T>`          | `None | inner` (untagged) or `Variant('none' | 'some', ...)` (tagged)       |
| `result<T, E>`       | `Variant('ok', val)` / `Variant('err', val)` via `ok()` / `err()` helpers   |
| `list<u8>`           | `bytes`                                                                     |
| `list<T>`            | `list`                                                                      |
| `tuple<...>`         | Python `tuple`                                                              |
| `flags`              | class exposing the names; values are sets of strings                        |
| `resource T`         | class wrapping `ResourceAny` / `ResourceHost` with method dispatch          |

The tagged/untagged classification mirrors `VariantLikeType._tagged` in
`wasmtime/component/_types.py`: a variant is tagged when two arms' Python
case-class sets overlap. The same predicate decides whether an `option<T>`
needs the `Variant`-wrapped form. Both are computed from the WIT IR at
codegen time, not re-derived from the emitted Python.

## Layout

| File           | Purpose                                            |
|----------------|----------------------------------------------------|
| `_ir.py`       | Typed loader for `wasm-tools component wit --json` |
| `_tagging.py`  | Tagged/untagged predicate over the IR              |
| `_emit.py`     | Code emission, one function per type kind          |
| `__main__.py`  | CLI entry point                                    |

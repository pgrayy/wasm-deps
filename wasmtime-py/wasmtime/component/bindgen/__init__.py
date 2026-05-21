"""WIT host bindgen for wasmtime-py.

Generates Python classes accepted directly at the FFI boundary —
kebab-case record attributes, ``Variant(tag, payload)`` for tagged
variants, raw payloads for untagged ones. No separate marshaling layer.

Usage:
    python -m wasmtime.component.bindgen <wit-path> -o out.py

Tracks https://github.com/bytecodealliance/wasmtime-py/issues/309.
"""

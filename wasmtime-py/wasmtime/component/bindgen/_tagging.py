"""Mirror of wasmtime-py's runtime "tagged variant" classification.

wasmtime-py decides at the FFI boundary whether a variant or option needs the
``Variant(tag, payload)`` wrapper or accepts a bare payload. The decision is
based on the Python "case classes" each arm contributes via
``ValType.add_classes``: if two arms' class sets overlap, the variant is
"tagged" and requires the wrapper; otherwise it's "untagged" and the bare
payload is accepted.

We compute the same predicate from the WIT IR at codegen time so the emitted
classes never need to introspect themselves. This module is the single source
of truth for the wire shape — it must agree with
``wasmtime/component/_types.py:_tagged``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ._ir import (
    Alias,
    Enum,
    Flags,
    Handle,
    List,
    Option,
    Record,
    Resolve,
    Resource,
    Result,
    Tuple,
    TypeRef,
    Variant,
)


# Mirror of wasmtime-py's ``ValType.add_classes``. We name classes by string
# so the predicate stays decoupled from whether ``wasmtime.component`` is
# importable here.
_PRIMITIVE_CLASSES: dict[str, str] = {
    "bool": "bool",
    "s8": "int", "s16": "int", "s32": "int", "s64": "int",
    "u8": "int", "u16": "int", "u32": "int", "u64": "int",
    "f32": "float", "f64": "float",
    "char": "str",
    "string": "str",
}


@dataclass
class TaggingCtx:
    """Caches predicate results to keep recursion cheap and break cycles."""

    ir: Resolve
    _classes: dict[int, frozenset[str]] = field(default_factory=dict)
    _variant_tagged: dict[int, bool] = field(default_factory=dict)

    @classmethod
    def new(cls, ir: Resolve) -> "TaggingCtx":
        return cls(ir=ir)


def _ref_classes(ref: TypeRef, ctx: TaggingCtx, _stack: Optional[set[int]] = None) -> frozenset[str]:
    """Return the case-class set wasmtime-py would use to distinguish this
    type as a variant arm payload."""
    if ref.is_primitive:
        assert ref.primitive is not None
        return frozenset({_PRIMITIVE_CLASSES[ref.primitive]})

    type_id = ref.type_id
    assert type_id is not None
    if type_id in ctx._classes:
        return ctx._classes[type_id]

    # Recursive types (e.g. via aliases) eventually fall back to {object}.
    if _stack is None:
        _stack = set()
    if type_id in _stack:
        return frozenset({"object"})
    _stack = _stack | {type_id}

    kind = ctx.ir.types[type_id].kind

    if isinstance(kind, Alias):
        result = _ref_classes(kind.target, ctx, _stack)
    elif isinstance(kind, Record):
        result = frozenset({"Record"})
    elif isinstance(kind, Enum):
        result = frozenset({"str"})
    elif isinstance(kind, Flags):
        result = frozenset({"set"})
    elif isinstance(kind, Tuple):
        result = frozenset({"tuple"})
    elif isinstance(kind, List):
        result = frozenset({"bytes"} if _is_u8(kind.elem) else {"list"})
    elif isinstance(kind, Option):
        # The ``none`` arm contributes ``object``; the inner type contributes
        # its own classes. Their union is what makes a surrounding variant or
        # option flip to "tagged".
        result = _ref_classes(kind.inner, ctx, _stack) | frozenset({"object"})
    elif isinstance(kind, Result):
        ok = _ref_classes(kind.ok, ctx, _stack) if kind.ok is not None else frozenset({"object"})
        err = _ref_classes(kind.err, ctx, _stack) if kind.err is not None else frozenset({"object"})
        result = frozenset({"Variant"}) if ok & err else (ok | err)
    elif isinstance(kind, Variant):
        if _variant_is_tagged(type_id, ctx, _stack):
            result = frozenset({"Variant"})
        else:
            acc: frozenset[str] = frozenset()
            for case in kind.cases:
                arm_classes = (
                    frozenset({"object"})
                    if case.ty is None
                    else _ref_classes(case.ty, ctx, _stack)
                )
                acc = acc | arm_classes
            result = acc
    elif isinstance(kind, (Resource, Handle)):
        result = frozenset({"ResourceAny", "ResourceHost"})

    ctx._classes[type_id] = result
    return result


def _is_u8(ref: TypeRef) -> bool:
    return ref.is_primitive and ref.primitive == "u8"


def _variant_is_tagged(type_id: int, ctx: TaggingCtx, _stack: set[int]) -> bool:
    if type_id in ctx._variant_tagged:
        return ctx._variant_tagged[type_id]
    cases = ctx.ir.types[type_id].kind
    assert isinstance(cases, Variant)
    seen: frozenset[str] = frozenset()
    tagged = False
    for case in cases.cases:
        cls = (
            frozenset({"object"})
            if case.ty is None
            else _ref_classes(case.ty, ctx, _stack)
        )
        if cls & seen:
            tagged = True
            break
        seen = seen | cls
    ctx._variant_tagged[type_id] = tagged
    return tagged


# --- Public predicates -------------------------------------------------

def variant_is_tagged(ref: TypeRef, ctx: TaggingCtx) -> bool:
    """Does this variant need the ``Variant(tag, payload)`` wrapper at the
    wasmtime-py boundary? Aliases are followed."""
    canonical = ref.canonical(ctx.ir)
    assert not canonical.is_primitive
    assert canonical.type_id is not None
    t = canonical.resolve(ctx.ir)
    assert isinstance(t.kind, Variant), f"variant_is_tagged called on {type(t.kind).__name__}"
    return _variant_is_tagged(canonical.type_id, ctx, set())


def option_is_tagged(ref: TypeRef, ctx: TaggingCtx) -> bool:
    """Does this ``option<T>`` need the ``Variant('none' | 'some', ...)`` wrapper?

    True iff the inner type's case classes contain ``object`` — that's what
    makes the option's two-arm class sets overlap (the ``none`` arm
    contributes ``{object}``).
    """
    canonical = ref.canonical(ctx.ir)
    assert not canonical.is_primitive
    t = canonical.resolve(ctx.ir)
    assert isinstance(t.kind, Option), f"option_is_tagged called on {type(t.kind).__name__}"
    return "object" in _ref_classes(t.kind.inner, ctx)


def result_is_tagged(ref: TypeRef, ctx: TaggingCtx) -> bool:
    """Does this ``result<T, E>`` need the ``Variant('ok' | 'err', ...)`` wrapper?

    Tagged iff the ok/err class sets overlap. Absent ok/err arms contribute
    ``{object}`` (mirrors a unit case).
    """
    canonical = ref.canonical(ctx.ir)
    assert not canonical.is_primitive
    t = canonical.resolve(ctx.ir)
    assert isinstance(t.kind, Result), f"result_is_tagged called on {type(t.kind).__name__}"
    ok = _ref_classes(t.kind.ok, ctx) if t.kind.ok is not None else frozenset({"object"})
    err = _ref_classes(t.kind.err, ctx) if t.kind.err is not None else frozenset({"object"})
    return bool(ok & err)


__all__ = [
    "TaggingCtx",
    "option_is_tagged",
    "result_is_tagged",
    "variant_is_tagged",
]

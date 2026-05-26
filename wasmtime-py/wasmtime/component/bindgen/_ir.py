"""Typed loader for ``wasm-tools component wit --json`` output.

The JSON is the ``wit_parser::Resolve`` IR. We mirror enough to drive code
generation: worlds, interfaces, types (records/variants/enums/options/results/
lists/tuples/flags/resources/handles/aliases), and functions.

Type references in the JSON are either a primitive name string or an integer
ID into the top-level ``types`` array. Both forms become :class:`TypeRef`.
:meth:`TypeRef.canonical` follows aliases through ``use``-style re-exports
between interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Union


PRIMITIVES = frozenset(
    {
        "bool",
        "s8", "s16", "s32", "s64",
        "u8", "u16", "u32", "u64",
        "f32", "f64",
        "char", "string",
    }
)


# --- Type kinds --------------------------------------------------------

@dataclass
class Field:
    name: str  # kebab-case
    ty: "TypeRef"
    docs: Optional[str] = None


@dataclass
class Case:
    name: str  # kebab-case
    ty: Optional["TypeRef"]  # None for unit arms
    docs: Optional[str] = None


@dataclass
class Record:
    fields: list[Field]


@dataclass
class Variant:
    cases: list[Case]


@dataclass
class Enum:
    cases: list[str]


@dataclass
class Flags:
    names: list[str]


@dataclass
class Tuple:
    types: list["TypeRef"]


@dataclass
class List:
    elem: "TypeRef"


@dataclass
class Option:
    inner: "TypeRef"


@dataclass
class Result:
    ok: Optional["TypeRef"]
    err: Optional["TypeRef"]


@dataclass
class Resource:
    pass


@dataclass
class Handle:
    """A `borrow<T>` or `own<T>` reference to a resource."""

    target: "TypeRef"
    borrow: bool


@dataclass
class Alias:
    target: "TypeRef"


TypeKind = Union[Record, Variant, Enum, Flags, Tuple, List, Option, Result, Resource, Handle, Alias]


@dataclass
class TypeRef:
    """Reference to a type. Either a primitive name or a named type by ID.

    Anonymous container types (option/list/tuple/result) appear in the type
    table with ``name=None``; they're still referenced by ID.
    """

    primitive: Optional[str] = None
    type_id: Optional[int] = None

    @property
    def is_primitive(self) -> bool:
        return self.primitive is not None

    def resolve(self, ir: "Resolve") -> "Type":
        assert self.type_id is not None, "cannot resolve a primitive ref"
        return ir.types[self.type_id]

    def canonical(self, ir: "Resolve") -> "TypeRef":
        """Follow aliases until we hit a non-alias type. Returns self for primitives."""
        cur = self
        seen: set[int] = set()
        while cur.type_id is not None:
            if cur.type_id in seen:
                raise ValueError(f"alias cycle through type id {cur.type_id}")
            seen.add(cur.type_id)
            t = cur.resolve(ir)
            if not isinstance(t.kind, Alias):
                break
            cur = t.kind.target
        return cur


@dataclass
class Type:
    """A named (or anonymous) type entry from the IR's flat ``types`` array."""

    id: int
    name: Optional[str]  # None for anonymous container types
    kind: TypeKind
    owner_interface: Optional[int] = None
    docs: Optional[str] = None


@dataclass
class Function:
    name: str  # raw, e.g. "[constructor]agent" or "call-tool"
    params: list[tuple[str, "TypeRef"]]
    result: Optional["TypeRef"]  # WIT functions have at most one result
    kind: str  # "freestanding" | "constructor" | "method" | "static"
    resource: Optional[int] = None  # type id of the resource for constructor/method/static
    docs: Optional[str] = None


@dataclass
class Interface:
    id: int
    name: Optional[str]
    package: Optional[int]
    types: dict[str, int] = field(default_factory=dict)  # local-name -> type id
    functions: dict[str, Function] = field(default_factory=dict)
    docs: Optional[str] = None


@dataclass
class World:
    name: str
    imports: dict[str, "WorldItem"] = field(default_factory=dict)
    exports: dict[str, "WorldItem"] = field(default_factory=dict)
    package: Optional[int] = None
    docs: Optional[str] = None


@dataclass
class WorldItem:
    """A world's import or export entry: an interface, a type, or a function."""

    interface_id: Optional[int] = None
    type_id: Optional[int] = None


@dataclass
class Package:
    id: int
    name: str  # e.g. "wasi:io@0.2.6" or "strands:agent@0.1.0"


@dataclass
class Resolve:
    types: list[Type]
    interfaces: list[Interface]
    worlds: list[World]
    packages: list[Package] = field(default_factory=list)


# --- Loader ------------------------------------------------------------

def _parse_typeref(raw: Any) -> TypeRef:
    if isinstance(raw, str):
        if raw not in PRIMITIVES:
            raise ValueError(f"unknown primitive type {raw!r}")
        return TypeRef(primitive=raw)
    if isinstance(raw, int):
        return TypeRef(type_id=raw)
    raise TypeError(f"unexpected type reference {raw!r}")


def _parse_optional_typeref(raw: Any) -> Optional[TypeRef]:
    return None if raw is None else _parse_typeref(raw)


def _parse_function(name: str, raw: dict) -> Function:
    kind_raw = raw["kind"]
    if isinstance(kind_raw, str):
        kind, resource = kind_raw, None  # "freestanding"
    else:
        # {"constructor": id} | {"method": id} | {"static": id}
        kind, resource = next(iter(kind_raw.items()))
    params = [(p["name"], _parse_typeref(p["type"])) for p in raw.get("params", [])]
    result = _parse_optional_typeref(raw.get("result"))
    docs = (raw.get("docs") or {}).get("contents")
    return Function(name=name, params=params, result=result, kind=kind, resource=resource, docs=docs)


def _parse_type_kind(raw: Any) -> TypeKind:
    if raw == "resource":
        return Resource()
    if not isinstance(raw, dict) or len(raw) != 1:
        raise ValueError(f"unexpected type kind {raw!r}")

    [(tag, body)] = raw.items()

    if tag == "record":
        return Record(
            fields=[
                Field(
                    name=f["name"],
                    ty=_parse_typeref(f["type"]),
                    docs=(f.get("docs") or {}).get("contents"),
                )
                for f in body["fields"]
            ]
        )
    if tag == "variant":
        return Variant(
            cases=[
                Case(
                    name=c["name"],
                    ty=_parse_optional_typeref(c.get("type")),
                    docs=(c.get("docs") or {}).get("contents"),
                )
                for c in body["cases"]
            ]
        )
    if tag == "enum":
        return Enum(cases=[c["name"] for c in body["cases"]])
    if tag == "flags":
        return Flags(names=[f["name"] for f in body["flags"]])
    if tag == "tuple":
        return Tuple(types=[_parse_typeref(t) for t in body["types"]])
    if tag == "list":
        return List(elem=_parse_typeref(body))
    if tag == "option":
        return Option(inner=_parse_typeref(body))
    if tag == "result":
        return Result(
            ok=_parse_optional_typeref(body.get("ok")),
            err=_parse_optional_typeref(body.get("err")),
        )
    if tag == "type":
        return Alias(target=_parse_typeref(body))
    if tag == "handle":
        if "borrow" in body:
            return Handle(target=_parse_typeref(body["borrow"]), borrow=True)
        if "own" in body:
            return Handle(target=_parse_typeref(body["own"]), borrow=False)
        raise ValueError(f"unexpected handle body {body!r}")

    raise ValueError(f"unknown type kind {tag!r}")


def _parse_world_item(raw: dict) -> WorldItem:
    if "interface" in raw:
        return WorldItem(interface_id=raw["interface"]["id"])
    if "type" in raw:
        return WorldItem(type_id=raw["type"])
    raise ValueError(f"unsupported world item {raw!r}")


def load(json_blob: dict) -> Resolve:
    """Parse the raw ``wasm-tools component wit --json`` dict into a :class:`Resolve`."""
    types = []
    for idx, raw in enumerate(json_blob["types"]):
        kind = _parse_type_kind(raw["kind"])
        owner = raw.get("owner")
        owner_iface = owner["interface"] if isinstance(owner, dict) and "interface" in owner else None
        docs = (raw.get("docs") or {}).get("contents")
        types.append(Type(id=idx, name=raw.get("name"), kind=kind, owner_interface=owner_iface, docs=docs))

    interfaces = []
    for idx, raw in enumerate(json_blob["interfaces"]):
        funcs = {
            fname: _parse_function(fname, fbody)
            for fname, fbody in (raw.get("functions") or {}).items()
        }
        interfaces.append(
            Interface(
                id=idx,
                name=raw.get("name"),
                package=raw.get("package"),
                types=dict(raw.get("types") or {}),
                functions=funcs,
                docs=(raw.get("docs") or {}).get("contents"),
            )
        )

    worlds = []
    for raw in json_blob["worlds"]:
        worlds.append(
            World(
                name=raw["name"],
                imports={k: _parse_world_item(v) for k, v in (raw.get("imports") or {}).items()},
                exports={k: _parse_world_item(v) for k, v in (raw.get("exports") or {}).items()},
                package=raw.get("package"),
                docs=(raw.get("docs") or {}).get("contents"),
            )
        )

    packages = [
        Package(id=idx, name=raw["name"])
        for idx, raw in enumerate(json_blob.get("packages") or [])
    ]

    return Resolve(types=types, interfaces=interfaces, worlds=worlds, packages=packages)


__all__ = [
    "Alias",
    "Case",
    "Enum",
    "Field",
    "Flags",
    "Function",
    "Handle",
    "Interface",
    "List",
    "Package",
    "Option",
    "Record",
    "Resolve",
    "Resource",
    "Result",
    "Tuple",
    "Type",
    "TypeKind",
    "TypeRef",
    "Variant",
    "World",
    "WorldItem",
    "load",
]

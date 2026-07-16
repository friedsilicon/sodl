# SODL Language Decisions

Resolutions to the open calls in `sodl-grammar-audit.md`. Recorded so the
grammar's shape is traceable to an intent rather than to an accident.

## D1 — Field terminator: `;` everywhere

Every field ends in `;`, in every construct — struct, key, and object alike.
There is no per-construct rule to remember.

```sodl
struct Address {
    street: string;
    city: string;
}

object UserAccount {
    userId: UUID, assigned = counter, required, key;
    username: string, required;
}
```

`;` terminates a **field**. `,` separates **props within** a field. The two
are different jobs and no longer share a token.

## D2 — No `type =` prefix

`userId: UUID` — not `userId: type = UUID`. The keyword carried no
information. Struct and object fields are now syntactically uniform; the
declaration keyword alone distinguishes them.

Resolves defects 6, 27. `KeyFieldProps` was the sole production carrying the
prefix and folds away entirely.

## D3 — Constraints are field props

`range` and `pattern` attach as comma-led props, never as a type suffix.

```sodl
maxLoginAttempts: uint8, range(3, 10);
email: string, pattern = "^[a-z]+@.*";
```

`ConstrainedType ::= BasicType TypeConstraint` (no comma) is **deleted**: it
matched zero sites in either example file. Resolves defect 5; defines
`MetaProp` by adding range/pattern to the prop lists (defect 15).

## D4 — Named structs only

No anonymous inline object *types*. The five sites in
`advanced-examples.sodl` become named structs. Required for fixed-layout v1.

Note this is narrower than it sounds: D7 introduces a recursive brace
production for instance *literals* regardless. D4 governs type position only.

## D5 — Four distinct dotted productions

The four uses of `.` are different constructs and resolve in different
scopes, so each gets its own production and is legal only in its own
position:

| Production | Example | Resolves in |
|---|---|---|
| `QualifiedType` | `Crypto.SHA256Hash` | module scope |
| `EnumMember` | `UserRole.Guest` | enum scope |
| `FieldPath` | `deviceInfo.deviceFingerprint` | nested field scope |
| `ObjectRef` | `Employee.employeeId` | cross-object scope |

Buys real diagnostics — "Employee has no field employeeId" rather than "bad
dotted name". Resolves defect 12; closes the `FieldPath` gate.

## D6 — Keys and keymaps: kept, and given semantics

Both named `key` declarations and `keymap` stay. Composite keys were never in
question — they come from `key` field props.

The semantics the audit found undefined (defects 20, 21, 23, 25):

- **Keys and keymaps allow indexing and addressing an object in multiple
  ways.**
- **Every object field used in a key or keymap MUST be annotated `key`.**
- **Conversely, there must be no unused key fields.** Both directions are
  statically checkable; a field annotated `key` but referenced by no key or
  keymap is an error, as is a key or keymap referencing an unannotated field.
- **A keymap represents the relationship between a key and the object that
  key is defined for.**
- **Keys define how an object can be created (primary) and retrieved
  (primary and all secondary keys).**

This is what makes `key` coherent as both a declaration and a field prop:
the prop marks participation, the declaration names an access path, and the
two must account for each other exactly.

### The three rules, precisely

1. **`key` implies `required`.** A key field is required by construction;
   writing `required` alongside `key` is redundant and the prop is dropped
   from key fields throughout. Nothing can be addressed by a field that
   might be absent.

2. **Every `key` field must be used by at least one `key` declaration AND
   at least one `keymap`.** There is no implicit primary key: a field
   annotated `key` that no declaration names is an error. This is the
   strict reading — primary keys are nameable like any other, so every
   object carries an explicit primary `key` decl and a `primary` keymap
   binding it. Resolves defects 20 and 23; `primary` now has a defined
   meaning (the access path through which an object is created).

3. **Every object MUST declare at least one `key` field.** An object with
   no key cannot be created or retrieved, so it is not a legal object.
   Resolves defect 21, which observed that nothing required this.

## D7 — Instance literals

A `.sodl` file holds schema **and** populated data. SODL is a typed config
language (CUE / Dhall / HCL class), not a schema-only IDL.

```sodl
object Endpoint {
    name: string, required, key;
    url:  string, required;
}

Endpoint local = {
    name: "local",
    url:  "http://127.0.0.1:8080"
};
```

`ObjectLiteral` is wired into `Value` and a top-level instance production is
added. Resolves defects 4 and 26 together — the dead productions become
reachable rather than deleted.

## D8 — `tlv<T>` accepts any type

`tlv` is not restricted to primitives. T = tag, L = byte length, V = inner
encoding; nesting is allowed. The grammar already permitted this; the
examples merely failed to demonstrate it, so the examples are fixed rather
than the grammar narrowed. Resolves defect 28.

## D9 — `bytes` primitive

Added to `BasicType`. Variable-length byte array — cache bodies, certs, keys,
hashes. `[uint8; N]` remains for fixed-length runs. Resolves defect 29.

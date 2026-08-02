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

## D10 — `const`: named literal

Binds a name to a compile-time literal. Implements P2.

```sodl
const MAX_RETRIES: uint8 = 5;
const DEFAULT_HOST: string = "127.0.0.1";
```

**The type is declared, not inferred**, and is a `BasicType`. Requiring it
keeps the "every type is named" invariant (D2, D4) and needs no inference
engine; the declared type also fixes which positions a const may fill — a
string const is not a numeric bound. Rejected: inference from the literal.

**The value is a scalar literal** — number, string, or bool. Rejected:
enum-valued consts (`const R: UserRole = UserRole.Guest`), which would need
enum-scope resolution in a value position, and compound consts (object or
list literals), which are "named defaults" — a different feature. Either can
arrive later without disturbing this record. A const declared with a type
that has no literal form (`bytes`, `Timestamp`) is therefore an error.

**A const reference is equivalent to its literal at the use site.** Writing
`MAX_RETRIES` is writing `5` there. The declared type is checked against the
const's own value — `const X: uint8 = 300` is an error, 300 does not fit
`uint8` — and it gives the reference a category, but assignment at the use
site is checked against the value, as inline. So `const X: uint8 = 5` is
legal against a `uint16` field (5 fits) and `const Y: uint16 = 300` is not
legal against a `uint8` field (300 does not). This answers the conversion
question the proposal raised without introducing a widening lattice.

**A const is admitted wherever `Value` is, plus the literal-only prop
positions.** `default = Value` and instance data already admit an
`Identifier`, so consts work there unchanged. `range(...)`, `pattern = ...`,
and `strict = ...` took bare literals and are widened to accept a const
reference, so `range(0, MAX_RETRIES)` resolves — the case the proposal
called out explicitly. `Constraint` gains `NumberRef`/`StringRef`, and
`strict` gains `StrictValue`; all three route through `ConstRef`.

**No const references another const, and no arithmetic.** The RHS is a
plain `Literal`. Rejected for v1: `const B = A` and `const B = A + 1`. Both
add an evaluation order and a cycle check for little gain; a later proposal
can lift the restriction.

## D11 — `alias`: named type (P1)

`alias Name = Type, constraint*;` binds a name to a type. §4.3 required every
field type to be named, yet no construct could name a *constrained
primitive* — the sole reason the example files leaned on a phantom
`common_types` for `UUID` and `Money`. `alias` fills that gap. The four open
questions, resolved:

**Constraints travel through an alias.** `alias Port = uint16, range(1,
65535)` carries its range to every use. This directly contradicts the old
§5.1 sentence ("a constraint does not travel with a type through an alias"),
so that sentence is rewritten rather than preserved: field constraints stay
local; alias constraints do not. *Rejected:* keeping §5.1 as written and
forbidding constraints on aliases — that would leave `alias` a bare typedef,
unable to name the constrained primitives that motivated it.

**A use site adds constraints; it never replaces them.** A field may pin a
tighter bound on top of an alias (`preferredAddress: AddressIndex, range(0,
4)` where `AddressIndex` is `range(0, 9)`). Both apply — intersection.
*Rejected:* override. Override lets a field silently widen an invariant the
alias author declared; a config language should make the tighter rule win,
not the later-written one.

**Aliases chain; cycles are a static error.** An alias may name another
alias, constraints accumulating down the chain, which must terminate at a
non-alias type. A cycle is rejected statically (check 7). *Rejected:*
forbidding chains — needless, since resolution is already whole-program and
transitive.

**An alias is a transparent synonym, not a distinct type.** `Port` *is*
`uint16`; no conversion rules, no nominal identity. *Rejected:* nominal
(distinct) typing — it would demand a conversion story between an alias and
its base for no benefit at v1, and a config/IDL language gains nothing from
distinguishing `Port` from `uint16` on the wire. Constraints still bind to
the name; transparency is about type identity, not about dropping the rules.

## D12 — Discriminated `union`

`union` gains a tag type and binds each member to a type. This replaces the
bare-identifier `UnionDecl`, whose members resolved to nothing — the only
construct in the language with no defined semantics.

```sodl
union ContactMethod : uint8 {
    Email  = 1 -> string;
    Phone  = 2 -> string;
    Postal = 3 -> Address;
}
```

The open questions in P3, resolved:

- **Tags are explicit and required; duplicates are an error.** Rejected the
  enum-style implicit numbering (`EnumValue`'s optional `= n`). A union tag
  is a wire discriminant, not a display ordinal: implicit numbering makes
  reordering members silently change the encoding. Written tags cannot. Both
  the tag values and the member names must be unique within the union.

- **The tag type is restricted to the unsigned integers** `uint8`–`uint64`.
  Rejected signed, float, and string tags: a discriminant is a small
  non-negative wire tag, and nothing else earns a place in front of every
  value.

- **Members must be fixed-size; `bytes` and `tlv<T>` are excluded.** A union
  is `tag + largest member`, so it is fixed-size only if every member is —
  which is what lets `[AuthenticationFactor; 3]` (D4's fixed-layout goal)
  have a length at all. Rejected admitting the variable-length constructs:
  that would reintroduce the very hole P3 exists to close. The regex checker
  catches a `bytes`/`tlv` member directly; it does not trace a struct member
  back to a variable-length field nested inside it (noted in `TODO.md`).

- **A union value is written `Member(value)`** in instance data. The member
  name selects the tag, so the tag is recoverable without writing it.
  Rejected a `{ tag: n, value: … }` form (the tag would be redundant with,
  and could contradict, the member) and a bare member name with no payload
  (a union member always carries one).

- **Union and enum stay separate.** Rejected subsuming `enum` into a
  payload-less union: an enum member is a bare named integer usable as a
  value (`default = UserRole.Guest`), a union member binds a type and is
  never a value on its own. Collapsing them would burden every enumerand
  with a unit type and cost `enum` its role as a plain constant set.

## D13 — Parser: chumsky (toolchain)

The front end uses `chumsky`, a Rust parser-combinator library, lowering
directly into the typed AST. Keeps the toolchain single-language (pure
`cargo`, no JS/C build) and gives first-class error recovery and diagnostics
— which matter for a hand-authored language.

Rejected: tree-sitter (editor-first — incremental, always produces a tree;
its JS-grammar/C-output build and CST-not-AST model fit an LSP, not a
converter — reserved for editor support, see TODO); `pest`/`winnow`/`nom`
(viable, weaker diagnostics or lower-level); bison/flex and hand-written
recursive descent (the prior C++/JSON pattern and its all-manual inverse).

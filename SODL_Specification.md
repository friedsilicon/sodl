# SODL Specification

Normative. Where this document and `sodl.ebnf` disagree, that is a bug in
one of them — report it.

- **Syntax:** `sodl.ebnf`
- **Rationale for the choices below:** `DECISIONS.md`
- **Introduction and tutorial:** `Primer.md` (non-normative)

## 1. Scope

SODL defines data structures, their relationships, their constraints, and
their populated values. A `.sodl` file carries schema and data together
(§7); SODL is a typed configuration language, not a schema-only IDL.

## 2. Program structure

    Program ::= ImportStatement* TopLevelItem*
    TopLevelItem ::= Declaration | InstanceDecl

Imports precede all other items. Declarations and instance declarations may
interleave.

## 3. Lexical

Comments are `//` to end of line, legal anywhere between tokens.

Integer literals are decimal (`42`) or hexadecimal (`0x2A`). Float literals
require digits on both sides of the point. String literals are
double-quoted. Boolean literals are `true` and `false`.

Identifiers match `[a-zA-Z_][a-zA-Z0-9_]*`.

## 4. Types

### 4.1 Basic types

`uint8` `uint16` `uint32` `uint64` `int8` `int16` `int32` `int64`
`float32` `float64` `string` `bool` `bytes` `Timestamp`

`bytes` is a variable-length byte array. For fixed-length runs use
`[uint8; N]`.

Importing a name that collides with a basic type is an error. Basic types
are not shadowable.

### 4.2 Complex types

- **List:** `[T; N]` — fixed-length, N elements of type T. Nestable:
  `[[string; 2]; 5]`.
- **TLV:** `tlv<T>` — tag, byte length, value. T is *any* type, including
  structs and further TLVs. The value is encoded per T's own rules.

### 4.3 User types

A struct, object, key, union, enum, or alias name. May be qualified by an
import alias: `Crypto.SHA256Hash`.

Field types are always named. There are no anonymous inline object types;
a nested structure is declared as a struct and referenced by name.

### 4.4 Aliases

An alias binds a name to a type, optionally with constraints:

    alias Port = uint16, range(1, 65535);
    alias UUID = string, pattern = "^[0-9a-fA-F]{8}-...-[0-9a-fA-F]{12}$";

An alias is a **transparent synonym**, not a distinct type. `Port` resolves
to `uint16` everywhere and is wire-identical to it; no conversion is defined
or needed, and a value typed `Port` is a value typed `uint16`. Aliases exist
to *name* a type — above all a constrained primitive, which no other
construct can name.

**Constraints travel.** A constraint written on an alias declaration is part
of the alias and applies at every use site. This is the one exception to
§5.1: field constraints are local, but an alias's are not — that is the
point of the construct.

**Aliases chain.** An alias may name another alias. The chain must terminate
at a non-alias type; a cycle (`alias A = B; alias B = A`) is a static error.
Constraints **accumulate** down the chain: a value must satisfy every
constraint on every link.

**Use sites add, they do not replace.** A field may attach its own
constraints on top of an alias that already carries some. Both apply —
the value must satisfy the alias's constraints *and* the field's
(intersection, never override). A field cannot loosen an invariant its
alias declared.

### 4.5 Discriminated unions

    union Name : TagType { Member = tag -> Type; ... }

A union is a tagged choice among typed members. `TagType` is an unsigned
integer basic type — `uint8`, `uint16`, `uint32`, `uint64` — and is the
wire discriminant. Each member binds a name to an explicit tag value and a
member type:

    union ContactMethod : uint8 {
        Email  = 1 -> string;
        Phone  = 2 -> string;
        Postal = 3 -> Address;
    }

Rules, checked statically:

- Tag values are explicit and must fit in `TagType`. Member names and tag
  values are each unique within the union. There is no implicit numbering:
  the tag is a wire contract, so it is written, not inferred from position.
- A member type must be fixed-size. `bytes` and `tlv<T>` — the
  variable-length constructs — are not admissible member types.

A union is encoded as the tag followed by the selected member's value. Its
size is the size of `TagType` plus the size of the largest member, so a
union is itself fixed-size and may appear in a fixed-length list
(`[ContactMethod; 3]`).

Union and enum are separate constructs. An enum member is a bare named
integer and carries no payload; a union member binds a type. Neither
subsumes the other.

## 5. Fields

Every field terminates with `;`. Props within a field are separated by `,`:

    fieldName: Type, prop, prop;

`;` ends a field. `,` separates props. The two never substitute.

### 5.1 Props

| Prop | Meaning |
|---|---|
| `required` | The field must be present. |
| `optional` | The field may be absent. |
| `key` | The field participates in this object's identity (§6). Implies `required`. |
| `assigned = counter \| random` | The value is generated, not supplied. |
| `default = Value` | Value used when the field is absent. |
| `strict = Literal` | The field must equal this literal exactly. |
| `range(min, max)` | Numeric bounds, inclusive. |
| `pattern = "regex"` | String must match. |

Constraints (`range`, `pattern`) are props. Written on a **field** they are
not part of the type and are local to that field: `uint8, range(0, 120)` —
never `uint8 range(0, 120)`. Written on an **alias** they bind into the
named type and travel with it (§4.4); an alias's constraints and a field's
own both apply, by intersection.

A `range` bound, a `pattern`, a `strict` value, and a `default` may each be
given as a named constant in place of a literal (§9).

## 6. Identity: keys and keymaps

Keys and keymaps are how an object is addressed. An object may be
addressable in several ways; each way is a key.

- A **`key` field prop** marks a field as participating in identity.
  Multiple `key` props on one object form a **composite key**.
- A **`key` declaration** names an access path and lists the fields it
  addresses by.
- A **`keymap`** binds a key declaration to the object that key addresses,
  field by field, with `->`.

A keymap marked `primary` is the path through which the object is
**created**. Every key — primary and secondary — is a path by which it can
be **retrieved**.

### 6.1 Rules

These are checked statically. They are not expressible in EBNF.

1. **`key` implies `required`.** Writing both is an error. Identity cannot
   depend on a field that may be absent.

2. **Every `key` field must be named by at least one key declaration and
   used by at least one keymap.** There is no implicit primary key: an
   object's primary key is declared and bound like any other. A `key` field
   that no declaration reaches is an error, and so is the converse — a key
   or keymap referencing a field not annotated `key`.

3. **Every object must declare at least one `key` field.** An object with
   no identity can be neither created nor retrieved.

A keymap's target may be reached by `FieldPath` into a nested struct
(`deviceFingerprint -> deviceInfo.deviceFingerprint`). The nested field is
the key field; the enclosing struct is not.

`cascadeDelete` on a keymap: deleting the source deletes what it addresses.

## 7. Instance data

An instance declaration binds a name to a populated value:

    TypeName instanceName = Value;

    Endpoint local = {
        name: "local",
        url: "http://127.0.0.1:8080"
    };

The value is checked against the named type: structurally, and against
every constraint and `required` prop. Object literals nest; list literals
use `[a, b, c]`.

A union value is written `Member(value)`: the member name selects the tag,
and the parenthesized value has that member's type. The tag is thus
recoverable from the literal without being written out.

    contactMethod: Email("root@acme.example")

## 8. Dotted names

Four constructs, distinguished by position and resolved in different
scopes:

| Form | Example | Scope |
|---|---|---|
| Qualified type | `Crypto.SHA256Hash` | import alias |
| Enum member | `UserRole.Guest` | enum |
| Field path | `deviceInfo.deviceFingerprint` | nested field, same object |
| Object ref | `Employee.employeeId` | another object |

Each is legal only where its production admits it.

## 9. Constants

A `const` binds a name to a compile-time literal:

    const MAX_RETRIES: uint8 = 5;
    const DEFAULT_HOST: string = "127.0.0.1";

The type is declared, never inferred, and is a basic type (§4.1) that has a
literal form — number, string, or bool. `bytes` and `Timestamp` have no
literal, so they cannot be a const's type. The value is a single literal: a
const references no other const, and no arithmetic is permitted.

A const reference is equivalent to writing its literal in place. Two checks
follow from that. First, the declared type is checked against the const's
own value — `const X: uint8 = 300` is an error, because 300 does not fit
`uint8`. Second, at a use site the value is checked exactly as an inline
literal would be: `const X: uint8 = 5` is legal against a `uint16` field
because 5 fits it, and `const Y: uint16 = 300` is not legal against a
`uint8` field because 300 does not.

A const may be used wherever a value of its type is legal: as a `range`
bound, a `pattern`, a `strict` value, a `default`, and in instance data.
The declared type also fixes the category of the reference — a string const
cannot be a numeric bound.

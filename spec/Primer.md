# SODL Primer

Non-normative. The spec is `SODL_Specification.md`.

## What it is

SODL describes a data model — the shapes, how they are addressed, what
values are legal — and then holds the actual values too. Schema and config
in one file, checked against each other.

## Fields

A field is a name, a type, and some props:

```sodl
struct Address {
    street: string;
    city: string;
    country: string;
}
```

`;` ends a field. `,` separates props within one:

```sodl
age: uint8, range(13, 120);
email: string, pattern = "^[^@]+@[^@]+$";
```

Constraints are props, not part of the type. `uint8, range(13, 120)` — the
comma matters.

## Naming a type

Every field type has to be named. Structs, objects, enums, and unions give
you names for compound shapes — but not for a *constrained primitive*. That
is what `alias` is for:

```sodl
alias Port = uint16, range(1, 65535);
alias UUID = string, pattern = "^[0-9a-fA-F]{8}-...-[0-9a-fA-F]{12}$";
```

An alias is just another name for its type — `Port` *is* a `uint16`, nothing
converts between them. What the alias adds is that its constraints come
along for the ride: write `Port` anywhere and the `1..65535` bound is
already in force. Compare a field constraint, which stays put on that one
field.

A field can tighten an alias further, and both bounds hold:

```sodl
preferredAddress: AddressIndex, range(0, 4);  // AddressIndex is range(0, 9)
```

Never looser — a field can only add rules, not drop the alias's. Aliases can
also name other aliases; the chain just can't loop back on itself.

## Constants

A `const` gives a literal a name:

```sodl
const MAX_LOGIN_ATTEMPTS: uint8 = 5;
const DEFAULT_THEME: string = "light";
```

The type is spelled out — no inference — and the value is one literal:
number, string, or bool. A const can't be built from another const, and
there's no arithmetic.

Use it anywhere the bare value would go: a range bound, a default, a
`strict` value, or in the instance data further down.

```sodl
loginAttempts: uint8, default = 0, range(0, MAX_LOGIN_ATTEMPTS);
theme: string, default = DEFAULT_THEME;
```

A const reference just *is* its value at that spot. `const X: uint8 = 5`
drops into a `uint16` field fine — 5 fits. `const Y: uint16 = 300` won't go
into a `uint8` field, for the same reason `300` wouldn't: it doesn't fit.

## Objects and identity

An object is a thing you store and retrieve. Every object needs at least
one `key` field — something to address it by:

```sodl
object UserAccount {
    userId: UUID, assigned = counter, key;
    email: string, key;
}
```

`key` implies `required` — you cannot address a thing by a field that might
be missing, so don't write both.

Marking a field `key` isn't enough on its own. You must also declare the
access path and bind it:

```sodl
key UserId {
    userId: UUID;
}

keymap UserId:UserAccount {
    userId -> userId
}, primary, name = "UserIdLookup";
```

That's three pieces for one idea, and it's deliberate:

- the **prop** says *this field is part of an identity*
- the **key** names *an identity*
- the **keymap** says *this identity addresses this object*

`primary` marks the path an object is created through. Others are
retrieval-only — add a second key and keymap to address the same object
another way:

```sodl
key UserEmail {
    email: string;
}

keymap UserEmail:UserAccount {
    email -> email
}, name = "EmailLookup";
```

That requires `email` to carry the `key` prop too. Two `key` fields in one
key declaration make a composite instead — both values together address one
object.

The rule cuts both ways: no `key` field without a key and keymap using it,
and no key or keymap naming a field that isn't `key`. Nothing dangles in
either direction.

## Data

The part that makes SODL a config language rather than a schema:

```sodl
UserAccount root = {
    userId: "018f3a2b-0000-7000-8000-000000000002",
    username: "root",
    email: "root@example.com"
};
```

Checked against the declaration — every constraint, every `required` field.
A typo here is a compile error, not a 3am page.

## Unions

A union is a tagged choice: one of several typed alternatives, with a tag
byte in front saying which. You give it a tag type and bind each member to
a type:

```sodl
union ContactMethod : uint8 {
    Email  = 1 -> string<254>;
    Phone  = 2 -> string<32>;
    Postal = 3 -> Address;
}
```

The tags are written, not counted — they're the wire discriminant, so
reordering the members must not change them. Every member type has to be
fixed-size — so `bytes`, `tlv<T>`, and bare `string` are all out, which is
why the members above are `string<N>`. That is what lets a union sit in a
fixed-length list: `[ContactMethod; 3]` has a length because a union is the
tag plus its largest member.

In data, you name the member and hand it a value; the tag comes from the
name:

```sodl
contactMethod: Email("root@acme.example")
```

Enums are the flatter cousin — named integers with no payload. A union
member carries a value; an enum member is just a value. They don't fold
into each other.

## Types worth knowing

- `bytes` — variable-length binary: certs, keys, cache bodies.
  `[uint8; 32]` when the length is fixed.
- `string<N>` — exactly N bytes, fixed-size. `string` on its own is
  variable-length.
- `[T; N]` — fixed-length list. T must be fixed-size, so `[string<16>; 5]`
  works and `[string; 5]` does not. Nestable.
- `tlv<T>` — tag/length/value around any type, including structs and other
  TLVs.
- `Crypto.SHA256Hash` — a type from an import alias.

## Layout

SODL is its own wire format, so every declaration has a byte layout.

```sodl
packed struct Packet {      // packed is the default: no padding
    version: uint8;         // offset 0
    id:      [uint8; 16];   // offset 1
    payload: bytes;         // variable — must come last
}

fixed struct Header { … }   // natural alignment instead, for C overlay
bigEndian packed struct IpHeader { … }   // little-endian by default
```

One rule shapes how you write a declaration: **variable-length fields go
last.** Once a `string`, `bytes`, or `tlv<T>` appears, no fixed-size field
may follow it — otherwise that field would have no computable offset. So
every declaration has a fixed prefix a C program can read directly, and a
trailing region that gets walked.

It is transitive. A struct containing a bare `string` is itself
variable-length, so it too may only appear last in whatever holds it — and
it cannot be an element of `[T; N]`. That is usually the nudge to reach for
`string<N>` instead.

## Next

- `examples/example.sodl` — the core constructs end to end
- `examples/advanced-examples.sodl` — constraints, TLV, `bytes`, instance data
- `SODL_Specification.md` — the normative rules (this directory)
- `DECISIONS.md` — why it's shaped this way (this directory)

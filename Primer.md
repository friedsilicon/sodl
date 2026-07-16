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

## Types worth knowing

- `bytes` — variable-length binary: certs, keys, cache bodies.
  `[uint8; 32]` when the length is fixed.
- `[T; N]` — fixed-length list. Nestable.
- `tlv<T>` — tag/length/value around any type, including structs and other
  TLVs.
- `Crypto.SHA256Hash` — a type from an import alias.

## Next

- `example.sodl` — the core constructs end to end
- `advanced-examples.sodl` — constraints, TLV, `bytes`, instance data
- `SODL_Specification.md` — the normative rules
- `DECISIONS.md` — why it's shaped this way

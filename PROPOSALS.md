# SODL Proposals

Constructs under consideration. **Nothing here is normative.** Nothing here
is in `sodl.ebnf`. Syntax shown is illustrative and expected to change.

A proposal leaves this file when it is settled: the open questions become a
record in `DECISIONS.md`, the syntax becomes a production in `sodl.ebnf`,
the rules become prose in `SODL_Specification.md`, and the construct appears
in the examples and `Primer.md`. A proposal that is rejected leaves with a
decision record saying why.

## P1 — `alias`: named type

Binds a name to a type, optionally with constraints attached.

```sodl
alias Port = uint16, range(1, 65535);
alias UUID = string, pattern = "^[0-9a-f]{8}-[0-9a-f]{4}-...";
```

**Motivation.** Spec §4.3 requires every field type to be named, but the
only way to name one today is to declare a struct, object, key, union, or
enum. There is no way to name a constrained primitive. Both example files
reference `UUID` and `Money` as if from a `common_types` module that does
not exist, so static check 4 cannot be exercised on them — see the
"instance data is not type-checked" bug in `TODO.md`.

**Open questions.**

- Spec §5.1 states a constraint does not travel with a type through an
  alias. If `alias Port = uint16, range(1, 65535)` is admitted, that
  sentence is either wrong or aliases are a deliberate exception. Decide
  which, and edit §5.1 accordingly.
- Whether a field may add constraints on top of an alias that already
  carries them, and if so whether the effect is intersection or override.
- Whether aliases may chain, and whether a cycle is a static error.
- Whether an alias is a distinct type or a transparent synonym.

## P2 — `const`: named literal

Binds a name to a compile-time literal value.

```sodl
const MAX_RETRIES: uint8 = 5;
const DEFAULT_HOST: string = "127.0.0.1";
```

**Motivation.** Every bound and default in both example files is an unnamed
literal. A named constant is usable from `range(...)`, `default = ...`, and
`strict = ...`, and from instance data.

**Open questions.**

- Whether a `const` is admitted wherever `Value` is, or only in the prop
  positions that take a literal.
- Whether `range(0, MAX_RETRIES)` resolves. `Constraint` currently takes
  `NumberLiteral`, not `Value`, so this needs an explicit answer.
- Whether the declared type is required or inferred, and what conversions
  are legal — `const X: uint8 = 5` used against a `uint16` field.
- Whether constants may reference other constants, and whether arithmetic
  is permitted. Probably not, for v1.

## P3 — Discriminated `union`

Gives `union` a tag type and binds each member to a type.

```sodl
union ContactMethod : uint8 {
    Email = 1 -> EmailAddress;
    Phone = 2 -> PhoneNumber;
}
```

**Motivation.** `union` is the only construct with no defined semantics —
see the "union has no semantics" bug in `TODO.md`.
`UnionDecl ::= "union" Identifier "{" IdentList "}"` lists bare identifiers
that resolve to nothing; the members of `AuthenticationFactor` and
`ContactMethod` are undeclared in both example files. With no discriminant
and no member types there is no wire format and no size rule, which makes
`[AuthenticationFactor; 3]` a fixed-length list of something with no
length. A tag type plus a member-to-type binding addresses the
discriminant, the encoding, and the size question together.

**Open questions.**

- Whether tag values are explicit, implicit, or either; and whether
  duplicate tags are an error. They should be.
- The size rule. Fixed-size v1 (D4's stated goal) implies a union's size is
  the tag plus the largest member, which requires every member type to be
  sized. That excludes `bytes` and any `tlv<T>` member.
- How a union value is written in instance data (§7). The tag has to be
  recoverable from the literal.
- Whether the tag type is restricted to unsigned integers.
- Whether this subsumes `enum`, or the two stay separate.

# SODL Proposals

Constructs under consideration. **Nothing here is normative.** Nothing here
is in `sodl.ebnf`. Syntax shown is illustrative and expected to change.

A proposal leaves this file when it is settled: the open questions become a
record in `DECISIONS.md`, the syntax becomes a production in `sodl.ebnf`,
the rules become prose in `SODL_Specification.md`, and the construct appears
in the examples and `Primer.md`. A proposal that is rejected leaves with a
decision record saying why.

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

This replaces the existing `UnionDecl` production; it is not a parallel
construct alongside it.

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

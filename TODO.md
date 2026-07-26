# TODO

Known gaps after the audit reconciliation. Ordered roughly by severity.

## Bugs

**D5 is encoded wrong.** `QualifiedType`, `EnumMember`, and `ObjectRef` are
identical rules (`Ident "." Ident`), and `FieldPath` (`Ident ("." Ident)*`)
subsumes `ObjectRef`. `KeyMapTarget ::= FieldPath | ObjectRef` is therefore
ambiguous — a generator takes the first arm and `ObjectRef` is unreachable
(defect 4, reintroduced). What separates these is what the head resolves to
(field / type / import alias), which is a symbol-table question, not a
grammar one. Fix: one `DottedName ::= Identifier ("." Identifier)*` plus
resolution rules in the spec. Same diagnostics, no ambiguity.

**`assigned` contradicts instance data.** `userId: UUID, assigned = counter`
declares the value generated; `UserAccount rootUser = { userId: "018f..." }`
supplies it. Both `rootUser.userId` and `acme.orgId` do this in
`example.sodl`. Undecided: literal wins, `assigned` wins, or error. Likely
needs a "generate this field" syntax, or a rule that objects with `assigned`
fields cannot be written as instances. Product call — same class as D7.

**`union` has no semantics.** Members don't resolve: `AuthenticationFactor`
lists `PasswordHash`, `TOTPToken`, `BiometricData`, `SecurityKey`,
`RecoveryCode` — none declared. `ContactMethod` lists `Email`, `Phone` —
neither declared. No discriminant, no wire format, no size rule, so
`[AuthenticationFactor; 3]` is a fixed-size list of something with no size.
Either specify it or cut it. Currently the only construct with no defined
semantics.

**Instance data is not type-checked.** `userId: "018f3a2b-..."` and `price:
"49.99"` now resolve — D10 made `UUID` and `Money` local aliases for
constrained `string`s, so the types are defined and their patterns are even
knowable statically. But nothing checks them: static check 4 (grammar, foot)
promises structural and constraint matching of instance values, and
`check-sodl.py` still implements none of it. This needs an AST — the regex
lint cannot match a literal against an alias's pattern.

## Next steps

- **Make one import resolvable.** D10 pulled `UUID` and `Money` in-file as
  aliases, but `GeoLocation`, the `validated_types` names, and the `Crypto`
  wildcard are still unresolved imports. A real module behind one of them
  turns static check 4 into a test and exposes what else hides behind a name.
- **Write a parser.** The grammar has never been fed to a generator. `D5`
  above is exactly the kind of bug that surfaces the moment one runs.
- **Move checks off regex.** `check-sodl.py` reads concrete syntax by regex.
  It enforces D6 and catches defects 17/19, but union members, instance
  types, and anything scope-dependent need an AST. It now validates each
  `const` declaration (D10, static check 6) and that a `range` bound naming
  an identifier resolves to a numeric const, but a const reference in
  `default`, `strict`, or instance data is not resolved, and no reference is
  checked to *fit* the position — both need the same field-level type
  checking that static check 4 still lacks.

## Underspecified

- **`Timestamp`** — no encoding, no precision, no epoch.
- **`strict`** — in grammar and spec, used in zero examples, semantics
  undefined. Audit flagged it; still open.
- **`range` accepts floats on integer types.** `range(0.5, 1.5)` on a `uint8`
  parses. Should be type-checked against the field, or restricted.
- **`assigned = counter`** — scope, monotonicity, and collision behaviour
  unstated (audit defect 22). `random` likewise: source, width, uniqueness.
- **`cascadeDelete`** — one sentence, no story for cycles.
  `advanced-examples.sodl` has a real `Department` ↔ `Employee` cycle.

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

**Instance data is not type-checked.** `userId: "018f3a2b-..."` and `price:
"49.99"` now resolve — D11 made `UUID` and `Money` local aliases for
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

## Toolchain

Direction: a single-language toolchain (no serialized boundary between
front end and backends). The IR is in-memory typed data; every format and
codegen backend is a library against it.

- **Serialized IR boundary — deferred, not rejected.** The prior art here
  was bison/flex → a C++ binary emitting a JSON AST → consumers parsing the
  JSON. The JSON boundary is worth keeping *as an option*: it lets
  out-of-tree backends be written in any language against a stable artifact.
  We are not building it now — a single-language library is simpler and
  type-safe — but the IR should be serializable so a later `--emit-ir=json`
  flag is additive, not a rewrite. Revisit when a backend needs to live
  outside the main toolchain. If added, serialize the *resolved, checked*
  IR, not the raw parse tree, so consumers inherit semantics rather than
  re-deriving them.

- **Primary direction is X → SODL.** SODL is the hub; the common workflow is
  importing an existing Avro / Protobuf / Parquet schema into SODL, not
  emitting to it. Two consequences: (1) SODL must be a superset of every
  source format's expressiveness, so X → SODL → X round-trips losslessly —
  gaps in that superset are SODL design pressure, i.e. new proposals; (2) a
  per-target capability matrix must record every construct that does *not*
  round-trip cleanly, its mitigation (Avro logical types, Protobuf custom
  options, Parquet KV metadata), and — where no mapping exists — the open
  question. That matrix is the first toolchain deliverable, before code.

- **Editor support — future, separate artifact.** A tree-sitter grammar for
  syntax highlighting and an LSP for authoring `.sodl` by hand. Tree-sitter
  is the right tool for this layer (incremental, error-tolerant) but the
  wrong one for the compiler front end (JS+C build, CST not AST, recovery
  over rejection — see D13). It would be a second grammar kept in sync with
  `sodl.ebnf`, not the parser the toolchain uses.

### Format-interchange gaps

Surfaced by the X → SODL superset requirement. Each construct a source
format has but SODL lacks is a new proposal; each SODL construct a target
lacks is a capability-matrix cell with a mitigation or an open question.

Missing SODL constructs — now proposals in `PROPOSALS.md`:

- **Map type** — Avro `map`, Protobuf `map<K,V>`. SODL's only complex types
  are fixed lists and TLV; an imported map has nowhere to land. P4.
- **Variable-length list** — Avro `array`, Protobuf `repeated`; SODL has
  only fixed `[T; N]`. The largest gap: most real schemas use one, so
  without it X → SODL is non-functional for them. P5.
- **Explicit field numbers** — Protobuf identifies fields on the wire by
  number; those must be preserved or binary compatibility breaks. SODL
  fields have no number. P6.
- **`decimal<P, S>`** — Avro / Parquet DECIMAL. `Money` is currently an
  alias for a constrained `string` (D11), which is neither numeric nor
  scale-aware. P7.

SODL constructs no target represents — capability-matrix cells, not gaps in
SODL:

- **`tlv<T>`** — a wire byte layout; Avro / Parquet / Protobuf abstract the
  wire away, and no annotation recovers it. Options: `bytes` + a `sodl.tlv`
  annotation (native consumers see opaque bytes), or lower tag/length/value
  into an explicit struct (loses the TLV encoding). Needs a decision.
- **Fixed-size `[T; N]`** — the `N` survives as a target annotation but stops
  being enforced, since Avro `array` / Protobuf `repeated` are unbounded.
- **`key` / `keymap`, `range` / `pattern`, `assigned`, `strict`** — no
  schema-format home; ride along as custom attributes (Avro), custom options
  (Protobuf), or KV metadata (Parquet). Round-trip through SODL faithfully;
  invisible to native consumers. Acceptable — these are SODL concerns.
- **Temporal logical types** — Avro / Parquet have date, time, timestamp
  variants, and duration; SODL has only the underspecified `Timestamp`.
  Deferred, pending the Timestamp encoding decision (see Underspecified). A
  candidate for its own proposal once that lands.

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
- **Union member fixed-size is checked shallowly (D12).** `check-sodl.py`
  rejects a `bytes` or `tlv<T>` union member directly, but a member typed as
  a struct that transitively contains a `bytes` or `tlv` field slips through.
  The same transitive hole exists for `[T; N]` lists; both need the AST the
  regex checker doesn't have.

## Program of work

- **Example coverage gaps.** `float32`, `float64`, `int64` now exercised in
  `example.sodl`. `strict = …` still uncovered — but writing an example
  needs its semantics decided first (Underspecified), so it is queued for
  approval, not filled unattended.
- **avrotize as the conversion hub (→ proposal, pending approval).** Build
  only SODL ↔ Avro in-tree; delegate Avro ↔ {Parquet, Protobuf, JSON Schema,
  SQL, Kusto, …} to avrotize (clemensv/avrotize, Python). Collapses the N
  format backends to one, and pins the capability matrix to Avro's logical
  types. Open: which conversions avrotize covers losslessly, how to invoke
  it (subprocess vs library), and where SODL-native constructs (keys, TLV)
  ride along.
- **JSON structure support (→ proposal, pending approval).** JSON Schema as a
  source+target format, and JSON as an instance-data interchange. Interacts
  with P10 (`json` type) but is distinct — this is whole-schema, that is a
  field type.

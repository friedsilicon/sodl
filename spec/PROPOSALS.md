# SODL Proposals

Constructs under consideration. **Nothing here is normative.** Nothing here
is in `sodl.ebnf`. Syntax shown is illustrative and expected to change.

A proposal leaves this file when it is settled: the open questions become a
record in `DECISIONS.md`, the syntax becomes a production in `sodl.ebnf`,
the rules become prose in `SODL_Specification.md`, and the construct appears
in the examples and `Primer.md`. A proposal that is rejected leaves with a
decision record saying why.

P1 (`alias`), P2 (`const`), and P3 (discriminated `union`) have been
implemented — see `DECISIONS.md` D11, D10, and D12 respectively.

P4–P7 below all arise from one requirement: X → SODL is the primary
direction, so SODL must be a superset of every source format's
expressiveness (see `TODO.md`, Format-interchange gaps). Each is a construct
that Avro, Parquet, or Protobuf has and SODL lacks, so an imported schema
using it cannot round-trip today.

## P4 — `map<K, V>`: associative type

Binds a variable set of keys to values.

```sodl
struct Config {
    limits: map<string, uint32>;
}
```

**Motivation.** Both Avro (`map`) and Protobuf (`map<K,V>`) have a native
associative type. SODL's only complex types are the fixed list `[T; N]` and
`tlv<T>`, so an imported map has nowhere to land and Avro/Protobuf → SODL
cannot round-trip a schema that uses one.

**Open questions.**

- Key type. Avro maps are string-keyed; Protobuf allows integral and string
  keys but not float, bytes, or message. String-only is the safe
  intersection — decide whether SODL admits more.
- A map is variable-length, like `bytes`. That makes it inadmissible as a
  union member (static check 10) and inside a fixed list. State this,
  consistent with how `bytes` and `tlv` are already handled.
- Value type: any `Type`, including nested maps and structs? (Probably yes,
  mirroring `[T; N]` and `tlv<T>`.)
- Ordering. Avro and Protobuf maps are unordered; round-trip must not depend
  on key order.
- Whether `range` / `pattern` may attach to keys, values, or neither.

## P5 — variable-length list

A list with no declared length.

```sodl
struct Post {
    tags: [string];     // no count — variable-length
}
```

**Motivation.** The single largest X → SODL gap. Avro `array` and Protobuf
`repeated` are unbounded, and nearly every real schema uses one. SODL today
expresses only a fixed count, so importing an unbounded field either fails
or fabricates a bogus `N`. Without this, X → SODL is non-functional for most
real schemas.

**Open questions.**

- Syntax. `[T]` (no count) reads cleanly against `[T; N]`, but the
  empty-count form must be unambiguous in the grammar. Alternatives: `[T; *]`
  or a distinct keyword.
- Whether `[T; N]` and `[T]` are one type family with `N` optional, or two
  distinct types.
- Tension with D4's fixed-layout-v1 goal: a variable-length list breaks
  fixed size, exactly as `bytes` and `tlv` already do. The precedent exists,
  but the union-member and fixed-list admissibility rules (check 10) must
  extend to it.
- Whether an optional max-length cap is offered, to preserve a
  fixed-upper-bound story where a target needs one.

## P6 — explicit field numbers

A field carries an explicit wire number.

```sodl
struct User {
    id:   uint64, field = 1;
    name: string, field = 2;
}
```

**Motivation.** Protobuf identifies fields on the wire by number, not name,
and those numbers must be preserved or binary compatibility breaks. SODL
fields have no number, so Protobuf → SODL drops them and SODL → Protobuf
reassigns them — silently breaking every previously-serialized message.

**Open questions.**

- First-class field prop (as sketched) versus a `sodl.field` interchange
  annotation carried only for Protobuf and ignored elsewhere. First-class is
  cleaner but adds a Protobuf-shaped concept to the core language.
- Whether numbers are optional (assigned by declaration order when absent)
  or required once any field in a type has one.
- Whether to model Protobuf `reserved` numbers/ranges (schema-evolution
  reservations) too, or only live numbers.
- Static checks: uniqueness within a type, and the legal range (Protobuf
  1–536,870,911, excluding the reserved 19000–19999 block).
- Whether the prop is legal on all fields or only in types destined for
  Protobuf.

## P7 — `decimal<P, S>`: exact decimal

An exact decimal parameterized by precision and scale.

```sodl
struct LineItem {
    price: decimal<10, 2>;     // precision 10, scale 2
}
```

**Motivation.** Avro and Parquet both have a DECIMAL logical type
parameterized by precision and scale, for exact money and measure values.
SODL has only binary floats (lossy) and, since D11, `Money` as an alias for
a constrained `string` — neither numeric nor scale-aware. Importing an Avro
`decimal(10, 2)` into a string pattern loses the numeric type and the scale.

**Open questions.**

- Whether `decimal<P, S>` is a new parameterized primitive (BasicType-like)
  or a logical type layered over `bytes` or an integer, as Avro does.
- Whether `Money`'s D11 alias is redefined as `alias Money = decimal<...>` —
  a follow-on edit if this lands.
- Size. Fixed-size for a given `P` (hence union-member-admissible), or
  variable? Avro decimal on `fixed` is fixed; on `bytes` is not.
- Whether `range(...)` applies, and in decimal or float terms.
- Rounding and overflow semantics on assignment.

---

P9–P11 are the **logical-type extension layer** (see `SODL_Extensions.md`,
D14). Each maps an Avro/Parquet logical type onto a core type plus
semantics; a core-only implementation may ignore or reject them.

## P9 — `uuid`

```sodl
struct User { id: uuid; }
```

**Motivation.** Avro (uuid on `string`) and Parquet (UUID on `fixed[16]`)
have it. D11 currently fakes it as `alias UUID = string, pattern = ...`,
which is neither 16-byte nor semantic.

**Open questions.**

- Wire form: 16 bytes (Parquet) vs string (Avro). Pick canonical, record
  both mappings.
- Redefine the D11 `UUID` alias as this type — follow-on edit.
- Fixed-size (hence union-member admissible)? Yes if 16-byte.

## P10 — semi-structured: `json` / `bson`

```sodl
struct Log { payload: json; }
```

**Motivation.** Parquet JSON/BSON logical types carry opaque nested
documents; useful generally for schemaless fields. No SODL construct holds
one.

**Open questions.**

- One `json` type, or distinct `json` / `bson`? (bson = binary encoding of
  the same model.)
- Variable-length, like `bytes` — inadmissible as a union member or
  fixed-list element.
- Fully opaque, or is any structure/validation offered?

## P11 — `float16` (half precision)

```sodl
struct Sample { level: float16; }
```

**Motivation.** Parquet FLOAT16. Completes the float family (SODL has
`float32`/`float64`) for lossless Parquet round-trip.

**Open questions.**

- Literal form and precision/range checks.
- Core `BasicType` or extension-only. Probably extension.

---

P12–P13 are **toolchain** proposals, not language constructs. They add no
production to `sodl.ebnf`; they decide how the toolchain reaches other
formats. Listed here because they follow the same TODO → PROPOSAL →
DECISION process.

## P12 — avrotize as the conversion hub

Build only SODL ↔ Avro in-tree. Delegate Avro ↔ everything else to
[avrotize](https://github.com/clemensv/avrotize) (Python).

```
Parquet ─┐                        ┌─ Parquet
Protobuf ─┼─ avrotize ─ Avro ─ SODL ─ Avro ─ avrotize ─┼─ Protobuf
JSON Sch ─┘                        └─ JSON Sch, SQL, …
```

**Motivation.** The naive plan is one backend per format, each direction —
N backends, each with its own edge cases. avrotize already converts Avro to
and from Parquet, Protobuf, JSON Schema, XSD, SQL DDL, Kusto, and more. One
in-tree backend (Avro) buys the whole set, and pins the capability matrix to
a single well-documented type system instead of N.

**Open questions.**

- Verify the claim. Which conversions does avrotize actually support in each
  direction, and which are lossy? The hub is only as good as its worst leg —
  audit before committing.
- Invocation: subprocess (`avrotize` CLI) from the Rust toolchain, or a
  documented external step the user runs? Subprocess adds a Python runtime
  dependency to a Rust toolchain.
- Two-hop loss. SODL → Avro → Parquet compounds whatever each leg drops.
  Does the capability matrix track per-leg or end-to-end?
- Where SODL-native constructs (keys, keymaps, `tlv`, constraints) ride:
  Avro custom attributes are the only channel, and avrotize must preserve
  unknown attributes through the second hop. Verify it does.
- Fallback for what avrotize does not cover, and whether any format
  eventually earns a direct in-tree backend anyway.
- Licence and dependency posture of taking it on.

## P13 — JSON: schema and instance interchange

Two distinct capabilities, deliberately proposed together because they share
a serialization:

1. **JSON Schema** as a source and target format (schema ↔ schema).
2. **JSON** as an instance-data interchange for SODL's `D7` values.

```
User user1 = { "userId": "018f…", "role": "Admin" }   // JSON in
```

**Motivation.** JSON Schema is the most widely deployed schema language and
a likely X in X → SODL. Separately, SODL already carries instance data
(D7) but only in its own literal syntax, so populated values cannot be
exchanged with anything.

**Open questions.**

- Does JSON Schema come via avrotize (P12) or a direct backend? avrotize
  covers it, but JSON Schema's expressiveness (oneOf, allOf, conditionals,
  open-ended objects) may not survive the Avro hop.
- JSON Schema is structurally open (additional properties, no field order,
  `$ref` graphs) where SODL is closed and fixed-layout. Decide what subset
  imports cleanly and what is rejected.
- Instance direction: is JSON an *input* format for instance data, an
  *output*, or both?
- How SODL values with no JSON equivalent serialize: `bytes` (base64?),
  union literals (`Member(v)` → `{"Member": v}`?), `tlv`, fixed lists.
- Whether this subsumes or overlaps P10 (`json` as a *field type*). They are
  distinct — that is a type, this is a format — but the encoding rules
  should agree.

## P14 — import refinement (override on import)

Import a declared type and narrow it locally, without editing the source
schema or declaring a new type.

```sodl
import { Order } from "shared/order.sodl";

// This party's copy: version is pinned; the shared schema leaves it open.
refine Order {
    version: strict = 1;
}
```

**Motivation.** `strict` marks a field constant (semantics still open — see
`TODO.md`, Underspecified; the two are one design).
But constancy is often *party-relative*: a producer talking to several
consumers leaves a field variable, while each consumer pins it to the value
it accepts. Both views are correct simultaneously, so the pin cannot live in
the shared declaration. The intended workflow — each party keeps its own
`.sodl` importing the shared schema and overrides its copy — has no
mechanism today: imports bind names verbatim and nothing may modify them.

**Open questions.**

- Syntax and keyword: `refine`, `override`, `extend`, or a prop on the
  import statement itself.
- **Narrowing only.** A refinement should only be able to *restrict* — pin a
  value, tighten a `range`, make an `optional` field `required`. Widening,
  retyping, adding, or removing a field would fork the type rather than
  refine it, and must be a static error. Enumerate exactly which props may
  be refined.
- Wire compatibility. Refinement must not change the layout — a refined type
  stays binary-identical to its base, which holds if refinement is
  restriction-only and `strict` fields are transmitted normally.
- Is the refined type the *same* type (same name, same wire format, narrower
  validation) or a distinct subtype? Same-type is simpler and matches the
  "my copy" mental model.
- Whether refinements compose (A refines B refines C) and whether two
  refinements of one type may coexist in a file.
- Whether a refinement may target a locally declared type or only an
  imported one.
- Does the toolchain need to check a refinement against its base at import
  time — requiring real import resolution, which is still an open TODO.

---

P16 comes out of the spec audit and the C-interop requirement. P15, its
pair, landed as D16.

## P16 — externally-discriminated union

A union whose discriminant lives outside it.

```sodl
fixed struct Message {
    msgType: uint8;
    payload: Payload, discriminant = msgType;
}

union Payload {              // no inline tag; members name selector values
    Ping = 1 -> PingBody;
    Pong = 2 -> PongBody;
}
```

**Motivation.** A C union carries no discriminant. Existing C code puts the
selector in a sibling field, or derives it from a rule — if this field is
*x*, the live member is *y*. D12's mandatory inline tag cannot model that:
it places the tag *inside* the union, changing the memory image, so a D12
union can never overlay a real C union. Without this, P15's fixed tier
cannot express the C code it exists to interoperate with.

**Open questions.**

- Where the binding lives: at the use site as a field prop (as sketched —
  lets one union serve two structs with different selectors) or on the union
  declaration.
- **Selector expressiveness.** Equality against a sibling field only, or
  general predicates (ranges, multiple fields, computed conditions)? Real C
  code has all of these; each step up costs the checker a lot.
- Whether the discriminant may be a `FieldPath` into a nested struct, and
  whether an enum-typed discriminant is allowed (probably preferred).
- Exhaustiveness: must every value of the discriminant map to a member? Is
  there a default or unknown-member case, and is a gap an error?
- Ordering: must the discriminant field precede the union field in the
  declaration, so a streaming reader can select before decoding?
- Relationship to D12. Two union forms, or does the inline tag become
  optional on one construct? Two forms is clearer but doubles the surface.
- Instance data: `Member(value)` still identifies the member, but must agree
  with the discriminant field's own value — a new cross-field static check.
- Interchange: Avro and Protobuf unions are self-describing, so an
  externally-discriminated union has to be lowered (probably to the tagged
  form) on export. Add a capability-matrix row.

---

P17–P19 come from the goal in `TODO.md` ("Direction"): SODL should describe
a programming interface and the binary exchange between two endpoints well
enough that a human and an LLM can collaborate on it and generate working
code for both sides. That is a larger language than spec section 1 currently
scopes, and these are its missing pieces.

## P17 — derived and related fields

Express the relationship between one field and another, where today only
prose or hand-written code carries it.

```sodl
struct Frame {
    length:   uint32, lengthOf = payload;      // byte count of payload
    checksum: uint32, checksumOf = payload;    // over payload's bytes
    payload:  bytes;
}
```

**Motivation.** Two forces meet here. First, P15's variable tail is
**unparseable without this** — a reader reaching a `bytes` or variable list
has no way to know where it ends unless either SODL length-prefixes it
implicitly or the schema names the field that carries the length. Second,
this is the clearest case of semantics an LLM can act on: `lengthOf` states
*why* a field exists and what it governs, which is exactly the knowledge
needed to generate a correct parser and to reason about a protocol. The same
applies to `discriminant` (P16), which is the same idea for unions.

**Open questions.**

- **Does SODL self-delimit instead?** D15 says SODL owns its encoding, so it
  could length-prefix every variable field and make `lengthOf` unnecessary.
  That is simpler and self-consistent — but it forecloses overlaying existing
  C structs, which is what motivated the fixed tier. Resolve this against
  D15 before anything else here; the answer may narrow the whole proposal.
- Which relationships are worth first-class syntax: `lengthOf`, `countOf`
  (elements, not bytes), `checksumOf`, `offsetOf`, `presentIf`, `versionOf`?
  Each costs the checker and the codegen.
- Whether the derived value is *computed on write* by generated code, or
  merely *checked on read*, or both.
- Units: `lengthOf` in bytes or elements — and whether a general unit
  annotation (P18) subsumes the question.
- Whether a derived field may precede its target only, or either side.
- Cycles: `a` is the length of `b` and `b` the length of `a` must be an error.

## P18 — semantic annotations

Attach machine-readable meaning to a declaration, not just a type.

```sodl
struct Reading {
    takenAt:  uint64, unit = milliseconds, since = epoch;
    temp:     int16,  unit = celsius, scale = 0.1;
    sensorId: uint32, role = identifier;
    patient:  string, sensitivity = pii;
}
```

**Motivation.** A `uint32` tells a generator its width and nothing about its
meaning. Units, roles, and sensitivity live in `//` comments today, which
both the toolchain and an LLM discard. For the stated goal — a human and an
LLM collaborating on an interface and generating executable code — the
meaning has to be *in* the language, not beside it. It is also what lets a
generator emit correct conversions and a checker catch a milliseconds value
assigned to a seconds field.

**Open questions.**

- Fixed vocabulary or open key/value? A closed set is checkable; an open set
  is extensible and immediately useful. Perhaps a checked core plus an open
  namespace.
- Whether `doc = "..."` prose is first-class — it is the most obviously
  LLM-useful annotation and the least checkable.
- Do annotations participate in type checking (is milliseconds-into-seconds
  an error?) or are they inert metadata?
- Do they travel through an alias, like constraints do (D11)?
- How they map to targets: Avro custom attributes and Parquet KV metadata
  carry them; C codegen has nowhere to put them but comments.
- Whether `unit` and `scale` overlap `decimal<P,S>` (P7).

## P19 — endpoints (no verbs)

**Superseded before it was written.** The first draft of this proposal gave
SODL operations — `op read: device -> collector { request: …; response: …; }`.
That was wrong. SODL will have a runtime, and the runtime supplies the verbs;
the language does not need them.

The access paths already exist and are declarative: a `primary` keymap is how
an object is created, every key is how one is retrieved (D6). A runtime that
reads those can offer the behavior without SODL naming a single operation.
Adding `op` would have duplicated `keymap` in a second vocabulary.

What may still be missing is smaller and not yet urgent: whether SODL needs
any notion of an endpoint or role at all — which party holds what, and who
may reach which access path — or whether that too belongs to the runtime and
its configuration rather than to the language.

Left open deliberately. Revisit once the runtime's shape is known; designing
this before then would be guessing at the seam between the two.

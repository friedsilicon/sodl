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

P8–P11 are the **logical-type extension layer** (see `SODL_Extensions.md`,
D14). Each maps an Avro/Parquet logical type onto a core type plus
semantics; a core-only implementation may ignore or reject them.

## P8 — temporal logical types

`date`, `time`, `timestamp`, `duration`.

```sodl
struct Event {
    on:   date;                 // days since epoch
    at:   time<ms>;             // since midnight
    seen: timestamp<us, utc>;   // unit + UTC-adjusted (instant)
    ttl:  duration;
}
```

**Motivation.** Avro (date, time-millis/micros, timestamp-*,
local-timestamp-*, duration) and Parquet (DATE, TIME, TIMESTAMP with unit +
isAdjustedToUTC) all carry temporal logical types. SODL has only the
underspecified `Timestamp` basic type, so X → SODL cannot round-trip them.

**Open questions.**

- Unit parameter (`ms`/`us`/`ns`) — required, or a default?
- UTC-adjusted instant vs local. Avro splits `timestamp` / `local-timestamp`;
  model as a flag or as distinct types.
- Epoch and range: `date` = days since 1970-01-01, `time` = since midnight.
- `duration` encoding — Avro's (months, days, millis) `fixed[12]` vs a
  general interval.
- Reconcile with / absorb the core `Timestamp` when this lands (its own
  six-file change).

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

P15–P16 come out of the spec audit and the C-interop requirement. They are
paired: P16's untagged form is only meaningful inside P15's fixed tier.

## P15 — two-tier type system: `fixed` / `packed` vs free

A type is either **layout-guaranteed** or it is not, and the language says
which.

```sodl
fixed struct Header {        // natural alignment + padding, C ABI layout
    version: uint8;
    flags:   uint16;
    id:      [uint8; 16];
}

packed struct WireHeader {   // no padding, ABI-independent
    version: uint8;
    flags:   uint16;
}

struct Post {                // unmarked: free tier, no layout guarantee
    title: string;
    tags:  [string];
}
```

**The ordering rule.** Variable-length fields go last. Once a
variable-length field appears in a declaration, no fixed-length field may
follow it:

```sodl
fixed struct Packet {
    version: uint8;          // offset 0  — statically known
    length:  uint32;         // offset 4  — statically known
    id:      [uint8; 16];    // offset 8  — statically known
    payload: bytes;          // variable — must be last
}
```

Every type therefore has a **fixed prefix with statically known offsets**,
whether or not it also has a variable tail. That is what makes C overlay
work: the prefix can be cast onto a C struct, and the tail is walked. It
generalizes C99's flexible array member from one trailing array to a
trailing region.

**Variable-tailedness propagates.** A type containing a variable-length
field is itself variable-tailed, so it may only appear as the *last* field
of whatever contains it — otherwise the following field's offset would not
be computable. The rule is transitive and statically checkable.

**Motivation.** The spec currently claims a fixed layout it does not have

The `fixed` / `packed` keyword then asserts something narrower: the type is
*wholly* fixed — no variable tail at all — and its layout is pinned. Tiering
stays **explicit keyword only**, so a `fixed` type that acquires a `string`
field is a compile error rather than a silent demotion to prefix-plus-tail.

**Open questions.**

- **Arrays of variable-tailed types.** `[T; N]` where `T` has a variable
  tail cannot be indexed — element offsets are not computable. Forbid it, or
  admit it as sequential-access-only?
- **Multiple trailing variable fields.** Two `string`s at the end are
  decodable in order but the second has no static offset. Permit a variable
  *region* of several fields, or exactly one trailing variable field?
- Whether the trailing region needs a length prefix so a reader can skip the
  whole tail without decoding it field by field.
- Bounded strings. A wholly-`fixed` type needs *some* string: `string<N>` as
  a new bounded type, or require `[uint8; N]`.
- **Which ABI does `fixed` name?** Natural alignment differs across
  32/64-bit and across architectures. Pin one target, parameterize the
  declaration, or define alignment rules in-spec and let backends conform.
- **Endianness.** A C struct is host-endian; wire formats are usually
  big-endian. Does `fixed` imply host order (true memcpy compatibility) or a
  declared order (portability)? These conflict — `packed` may want one and
  `fixed` the other.
- Containment: a fixed type must not contain a free type. May a free type
  contain a fixed one? (Presumably yes.)
- Enum and union representation width in the fixed tier.
- Whether D12's union sizing rule (tag + largest member) becomes fixed-tier
  only, and what a free-tier union's size means.
- Whether `fixed`/`packed` apply to `object` too, or only `struct`/`union` —
  objects carry keys and identity, which have no C analogue.

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

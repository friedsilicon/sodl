# Capability matrix

Non-normative. What each SODL construct maps to in each interchange target,
and what it costs. Derived from the `TODO.md` requirement that X → SODL → X
round-trips losslessly while SODL → X may degrade.

Legend:

- **native** — the target has a direct equivalent.
- **annotated** — no equivalent; carried as a ride-along attribute so it
  survives a SODL round-trip, invisible to a native consumer of the target.
- **none** — no mapping and no annotation recovers it. Needs a decision.
- **P<n>** — blocked on that proposal; SODL cannot yet represent the
  target's construct at all.

Ride-along channels: Avro custom attributes (parsers ignore unknown keys),
Protobuf custom options (`extend FieldOptions`), Parquet key-value metadata,
JSON Schema unknown keywords. All four are spec-sanctioned.

## Basic types

| SODL | Avro | Parquet | Protobuf | JSON Schema |
|---|---|---|---|---|
| `bool` | native `boolean` | native `BOOLEAN` | native `bool` | native `boolean` |
| `int8` `int16` | annotated — widen to `int` + range | native `INTEGER(8\|16, signed)` | annotated — widen to `int32` + range | native `integer` + min/max |
| `int32` | native `int` | native `INT32` | native `int32` | native `integer` + min/max |
| `int64` | native `long` | native `INT64` | native `int64` | annotated — JSON numbers lose precision past 2^53 |
| `uint8` `uint16` | annotated — widen to `int` + range | native `INTEGER(8\|16, unsigned)` | annotated — widen to `uint32` + range | native `integer` + min/max |
| `uint32` `uint64` | annotated — **Avro has no unsigned type**; widen and range-annotate | native `INTEGER(32\|64, unsigned)` | native `uint32` / `uint64` | `uint64` loses precision as above |
| `float32` | native `float` | native `FLOAT` | native `float` | native `number` |
| `float64` | native `double` | native `DOUBLE` | native `double` | native `number` |
| `string` | native `string` | native `STRING` | native `string` | native `string` |
| `bytes` | native `bytes` | native `BYTE_ARRAY` | native `bytes` | annotated — base64 `string` |
| `Timestamp` | blocked — see below | blocked | blocked | blocked |

**`Timestamp` is the sharpest basic-type gap.** It has no encoding, no
precision, and no epoch (`TODO.md`, Underspecified), so it cannot be mapped
to Avro's `timestamp-millis`/`-micros` or Parquet's `TIMESTAMP(unit,
isAdjustedToUTC)` without inventing the answer. Blocked on P8, which also
reconciles it.

**Unsigned is the sharpest asymmetry.** Parquet represents all four unsigned
widths natively; Protobuf has 32/64 only; Avro has none at all. So
Parquet → SODL → Avro cannot preserve unsignedness except by annotation.

## Complex types

| SODL | Avro | Parquet | Protobuf | JSON Schema |
|---|---|---|---|---|
| `[T; N]` fixed list | annotated — `array` + size; `fixed` is bytes-only | annotated — `LIST` + size | annotated — `repeated` + size option | native `array` + `minItems`/`maxItems` |
| variable list (P5) | native `array` | native `LIST` | native `repeated` | native `array` |
| `map<K,V>` (P4) | native `map` (string keys) | native `MAP` | native `map<K,V>` | native `object` + `additionalProperties` |
| `tlv<T>` | **none** | **none** | **none** | **none** |
| `struct` | native `record` | native nested group | native `message` | native `object` |
| `object` | native `record` (+ key annotations) | native group | native `message` | native `object` |
| `enum` | native `enum` | native `ENUM` | native `enum` | native `enum` |
| discriminated `union` | native `union` — but Avro unions carry no explicit tag; tag values annotated | **none** — Parquet has no union | native `oneof` — field numbers are the tags (see P6) | native `oneOf` |
| `alias` | annotated — inlined; the name and its constraints ride along | annotated | annotated | native `$ref`/`$defs` |
| `const` | annotated — no schema-level constant | annotated | annotated | native `const` |

**`tlv<T>` is the one construct with no mapping anywhere.** It describes a
wire byte layout; all four targets abstract the wire away. The two candidate
lowerings — opaque `bytes` + a `sodl.tlv` annotation, or an explicit
tag/length/value struct — each lose something. Needs a decision (`TODO.md`).

**Union tags do not survive uniformly.** SODL's explicit tag is the wire
discriminant (D12). Avro selects a union branch positionally, Protobuf by
field number, JSON Schema not at all. Only Protobuf can carry the tag value
natively, and only if P6 lands.

## Props and identity

| SODL | All four targets |
|---|---|
| `required` / `optional` | native — Avro nullable union, Protobuf `optional`, Parquet repetition level, JSON `required` |
| `default = v` | native in Avro, Parquet, JSON Schema; Protobuf 3 dropped field defaults, so annotated |
| `range` / `pattern` | annotated everywhere except JSON Schema, which has native `minimum`/`maximum`/`pattern` |
| `key` / `keymap` | annotated — no target has an identity concept |
| `assigned = counter \| random` | annotated — behavioral, no schema home |
| `strict` | annotated — semantics still open (`TODO.md`) |
| `cascadeDelete` | annotated — relational behavior, no schema home |
| instance data (D7) | **none** — these are schema languages; values need a separate carrier (P13) |

## Extension types

Every row is blocked on its proposal; see `SODL_Extensions.md`.

| SODL | Avro | Parquet | Protobuf | Proposal |
|---|---|---|---|---|
| `decimal<P,S>` | native logical | native `DECIMAL` | annotated | P7 |
| `date` `time` `timestamp` `duration` | native logical | native logical | well-known types | P8 |
| `uuid` | native logical (string) | native `UUID` (fixed 16) | annotated | P9 |
| `json` / `bson` | annotated | native `JSON`/`BSON` | annotated | P10 |
| `float16` | **none** | native `FLOAT16` | **none** | P11 |

## Field order

Protobuf and Avro both identify fields independently of declaration order —
Protobuf by number, Avro by name — so an importer may reorder freely. That
matters if P15's ordering rule (variable-length fields last) binds imported
types: every message gets rewritten with its fixed scalars first, and the
mapping back survives only because the field identity travels with it.
For Protobuf that identity is the field number, so P15-universal implies P6.

## What this says about the plan

1. **`Timestamp` and `tlv` are the two blockers** on any honest backend.
   One is underspecified, one has no mapping. Both need decisions before a
   converter can claim correctness.
2. **P4, P5, P8 are load-bearing for the primary direction.** Without
   variable-length lists and maps, most real Avro/Protobuf schemas cannot
   enter SODL at all.
3. **Annotation is doing heavy lifting.** Roughly a third of the surface
   round-trips only through ride-along attributes. If P12 (avrotize) lands,
   every one of those must survive a *second* hop through avrotize's own
   Avro handling — which the P12 audit has to verify, not assume.

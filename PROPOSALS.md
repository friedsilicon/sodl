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

# SODL Extensions

Normative, layered on the core spec (`SODL_Specification.md`). Defines
**logical types** for interoperability with Avro, Parquet, and Protobuf —
the types those formats carry that core SODL does not.

- **Syntax:** `sodl.ebnf` (extension productions are marked)
- **Rationale for the split:** `DECISIONS.md` D14

## 1. Layering rule

Every extension type is a **core type plus semantics**: it has a defined
physical representation drawn from §4.1 of the core spec, and a meaning
layered over it — exactly as Avro and Parquet layer logical types over
primitives.

An implementation may support core only. It must then reject an extension
type, or pass it through unchanged; it must never silently mis-encode one.

Extension type names are reserved. Importing a name that collides with one
is an error, as it is for a core basic type (core spec §4.1).

Layout follows the core rules (§4.6): every extension type below is
fixed-size, so none falls under the ordering rule and all may appear in a
fixed list, in a union, or mid-declaration.

## 2. Temporal types

Core SODL has no time type. These four cover what Avro and Parquet carry.

### 2.1 Instants

    timestamp<unit>        an absolute point in time, UTC
    localTimestamp<unit>   a wall-clock reading with no zone

`unit` is one of `s`, `ms`, `us`, `ns`. **It is written, never defaulted.**

Both are `int64`: a signed count of `unit` since the Unix epoch,
1970-01-01T00:00:00Z. Alignment 8, size 8. Negative values are instants
before the epoch.

`timestamp` identifies an instant — the same value denotes the same moment
everywhere. `localTimestamp` denotes a calendar reading whose instant
depends on a zone supplied elsewhere; the two are not interconvertible
without one.

    observedAt: timestamp<ms>;      // an instant
    alarmAt:    localTimestamp<s>;  // 07:00 wherever the device is

### 2.2 Date and time of day

    date          days since 1970-01-01, int32, alignment 4
    time<unit>    time of day since midnight, unit as above

`time<ms>` and `time<s>` are `int32`; `time<us>` and `time<ns>` are `int64`,
because a day does not fit those units in 32 bits. Both are counts within a
single day: the value is at least 0 and less than one day in `unit`.

Neither carries a zone. A `date` is a calendar date, not an instant.

### 2.3 Duration

    duration      12 bytes: three uint32 — months, days, milliseconds

Alignment 4, size 12. The three components are kept separate and are *not*
normalized into one another: months vary in length and days vary across
daylight-saving boundaries, so collapsing them would change meaning. This is
Avro's `duration` and Parquet's `INTERVAL`, byte for byte.

A duration is unsigned. For a signed offset, carry a sign field alongside.

## 3. Interchange

| SODL | Avro | Parquet |
|---|---|---|
| `timestamp<ms>` `timestamp<us>` | `timestamp-millis` / `-micros` | `TIMESTAMP(unit, isAdjustedToUTC=true)` |
| `timestamp<s>` `timestamp<ns>` | annotated `long` | `TIMESTAMP(NANOS, true)` for `ns` |
| `localTimestamp<ms>` `<us>` | `local-timestamp-millis` / `-micros` | `TIMESTAMP(unit, isAdjustedToUTC=false)` |
| `date` | `date` | `DATE` |
| `time<ms>` `time<us>` | `time-millis` / `-micros` | `TIME(unit, …)` |
| `duration` | `duration` (`fixed[12]`) | `INTERVAL` (`fixed[12]`) |

Neither Avro nor Parquet has a second-resolution timestamp; `timestamp<s>`
maps to an annotated 64-bit integer and round-trips through SODL but is not
native on either side.

## 4. Planned

Not yet normative. Each lands with a decision record, a production, and
examples, as any construct does.

| Type | Representation | Sources | Proposal |
|---|---|---|---|
| `decimal<P, S>` | integer or bytes + precision, scale | Avro, Parquet | P7 |
| `uuid` | 16 bytes | Avro, Parquet | P9 |
| `json` / `bson` | opaque nested document | Parquet | P10 |
| `float16` | half-precision float | Parquet | P11 |

Already core, so no extension is needed — the format's logical type maps
straight onto a core construct: `enum` (Parquet ENUM), `string` (UTF8),
integer widths (Parquet INTEGER), `map` (P4), variable-length list (P5).

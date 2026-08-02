# SODL Extensions

Normative, layered on the core spec (`SODL_Specification.md`). Defines
**logical types** for interoperability with Avro, Parquet, and Protobuf —
the types those formats carry that core SODL does not.

- **Syntax:** `sodl.ebnf` (extension productions are marked)
- **Rationale for the split:** `DECISIONS.md` D14

## Layering rule

Every extension type desugars to a **core type plus semantics** — a logical
annotation over a core physical type, exactly as Avro and Parquet layer
logical types over primitives. An implementation may support core only; it
must then reject or pass an extension type through unchanged, never silently
mis-encode it. The extension spec builds on core and never contradicts it.

## Status

This layer is populated from proposals. Nothing here is normative until its
proposal lands with a decision record, a production, and examples.

## Types

Planned (see `PROPOSALS.md`):

| Type | Base + semantics | Sources | Proposal |
|---|---|---|---|
| `decimal<P, S>` | integer/bytes + precision, scale | Avro, Parquet | P7 |
| `date` `time` `timestamp` `duration` | integer + unit, UTC flag, epoch | Avro, Parquet | P8 |
| `uuid` | 16 bytes / string | Avro, Parquet | P9 |
| `json` / `bson` | opaque nested document | Parquet | P10 |
| `float16` | half-precision float | Parquet | P11 |

Already in core, so no extension is needed — the format's logical type maps
straight onto a core construct: `enum` (Parquet ENUM), `string` (UTF8),
integer widths (Parquet INTEGER), `map` (P4), variable-length list (P5).

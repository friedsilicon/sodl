# SODL — Structured Object Definition Language

A typed language for data models: structures, relationships, constraints,
and the populated values themselves. One `.sodl` file carries schema and
data together.

```sodl
object Endpoint {
    name: string, key;
    url:  string, required;
}

key EndpointKey {
    name: string;
}

keymap EndpointKey:Endpoint {
    name -> name
}, primary, name = "EndpointLookup";

Endpoint local = {
    name: "local",
    url:  "http://127.0.0.1:8080"
};
```

## Layout

```
spec/           the language definition
  SODL_Specification.md   core spec — normative
  SODL_Extensions.md      interop logical types, layered on core — normative
  sodl.ebnf               grammar — normative
  DECISIONS.md            why the language is shaped this way
  PROPOSALS.md            constructs under consideration — non-normative
  Primer.md               introduction by example — non-normative
  TODO.md                 known gaps, bugs, and the toolchain plan
  CAPABILITY_MATRIX.md    per-target construct mapping — non-normative
examples/       example.sodl (core), advanced-examples.sodl (constraints,
                TLV, bytes, qualified names, instance data)
scripts/        check-sodl.py — static checks the grammar cannot express
crates/sodl/    the toolchain (Rust) — parser, IR, backends. Skeleton only.
CLAUDE.md       working conventions: what is normative, what a change touches
```

## Tooling

The toolchain lives in `crates/sodl/` (Rust) and is a skeleton — no parser,
no code generation yet. The plan is in `spec/TODO.md`, section "Toolchain".

```
cargo test          # requires a Rust toolchain (https://rustup.rs)
```

Until the parser exists, `scripts/check-sodl.py` lints the example files
against the rules EBNF cannot state — key/keymap coherence, redundant props,
basic-type collisions. It reads concrete syntax by regex rather than
parsing; a real front end will check these on the AST.

```
scripts/check-sodl.py          # defaults to the examples/ corpus
```

## Status

The grammar and examples were reconciled against a full audit; every defect
it found is either fixed or recorded as a decision in `spec/DECISIONS.md`.
The language is specified but not implemented. Known gaps, bugs, and the
toolchain plan are in `spec/TODO.md`.

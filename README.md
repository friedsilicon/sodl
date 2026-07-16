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

## Repo

| File | |
|---|---|
| `SODL_Specification.md` | The spec. Normative. |
| `sodl.ebnf` | Grammar. Normative. |
| `DECISIONS.md` | Why the language is shaped this way. |
| `Primer.md` | Introduction, by example. Non-normative. |
| `example.sodl` | Core constructs. |
| `advanced-examples.sodl` | Constraints, TLV, `bytes`, qualified names, instance data. |
| `check-sodl.py` | Static checks the grammar cannot express. |

## Tooling

There is no parser yet. `check-sodl.py` lints the example files against the
rules in the spec that EBNF cannot state — key/keymap coherence, redundant
props, basic-type collisions:

```
./check-sodl.py example.sodl advanced-examples.sodl
```

It reads the concrete syntax by regex rather than parsing, and exists to
keep the examples honest. A real front end would check these on the AST.

## Status

The grammar and examples were reconciled against a full audit; every defect
it found is either fixed or recorded as a decision in `DECISIONS.md`. The
language is specified but not implemented — no parser, no code generation.

# SODL

A specified-but-unimplemented language. There is no parser and no code
generation; the artifacts are the grammar, the spec, and the examples that
keep them honest. Treat all three as the product.

## Which file is authoritative

`SODL_Specification.md` and `sodl.ebnf` are **normative**. Where they
disagree, that is a bug in one of them.

Everything else is not, and non-normative content must not be written into
either:

| File | Holds |
|---|---|
| `DECISIONS.md` | Settled calls, with the reasoning. One record per decision, `D<n>`. |
| `PROPOSALS.md` | Constructs under consideration, `P<n>`. Nothing here is in the grammar. |
| `TODO.md` | Known gaps and bugs. |
| `Primer.md` | Tutorial. |

A proposal moves from `PROPOSALS.md` to normative status by acquiring a
decision record, a production, spec prose, examples, and primer coverage —
not by being edited in place.

## Changing the language

Any change to a construct touches all six of these. A change that lands in
fewer is almost certainly incomplete:

1. `sodl.ebnf` — the production, plus any static check the EBNF cannot
   express (there is a numbered list at the foot of the file for those).
2. `SODL_Specification.md` — the normative rules, in prose.
3. `DECISIONS.md` — a new `D<n>` record: what was decided, what was
   rejected, and why. Do not renumber existing records.
4. `example.sodl` and `advanced-examples.sodl` — the construct in use.
   `example.sodl` is core constructs; `advanced-examples.sodl` is
   constraints, TLV, `bytes`, qualified names, and instance data.
5. `Primer.md` — how to teach it.
6. `TODO.md` — remove anything the change resolves; add anything it opens.

## Implementing a proposal

When asked to implement a `P<n>` from `PROPOSALS.md`:

- Resolve **every** open question the proposal lists. Decide; do not defer
  and do not ask. A proposal that lands with open questions still open is
  not implemented.
- The decision record states what you chose *and what you rejected*, with
  the reasoning. A record that only describes the winner is half a record.
- Where a resolution contradicts existing normative text, edit that text.
  Leaving the contradiction standing is the one unacceptable outcome.
- Remove the `P<n>` section from `PROPOSALS.md` — the proposal has left.
- Commit when the six files above are consistent and the checker passes.

## Checking

```
./check-sodl.py example.sodl advanced-examples.sodl
```

This must pass before committing. It enforces the rules EBNF cannot state —
key/keymap coherence, redundant props, basic-type collisions. It reads
concrete syntax by regex rather than parsing, so it is easy to defeat by
accident; if a new construct needs a check it cannot see, extend it or note
the gap in `TODO.md` explicitly rather than leaving it silent.

## House style

Prose is terse and declarative. Say what the rule is, then what it resolves.
The existing records in `DECISIONS.md` set the register — match it. Examples
carry their weight: every construct in the grammar should appear in at least
one example file, and no example should reference a name that is never
declared.

# SODL

A specified language whose toolchain is a skeleton. The language artifacts —
grammar, spec, examples — are the product today; the Rust toolchain in
`crates/sodl/` is where it becomes real.

## Layout

- `spec/` — the language definition (see the table below).
- `examples/` — `example.sodl`, `advanced-examples.sodl`.
- `scripts/` — `check-sodl.py`, the regex linter.
- `crates/sodl/` — the toolchain (Rust). Parser, IR, backends will grow
  here; `cargo test` runs it. The plan is `spec/TODO.md`, "Toolchain".

## Which file is authoritative

`spec/SODL_Specification.md` and `spec/sodl.ebnf` are **normative**. Where
they disagree, that is a bug in one of them.

Everything else is not, and non-normative content must not be written into
either:

| File | Holds |
|---|---|
| `spec/DECISIONS.md` | Settled calls, with the reasoning. One record per decision, `D<n>`. |
| `spec/PROPOSALS.md` | Constructs under consideration, `P<n>`. Nothing here is in the grammar. |
| `spec/TODO.md` | Known gaps, bugs, and the toolchain plan. |
| `spec/Primer.md` | Tutorial. |

A proposal moves from `spec/PROPOSALS.md` to normative status by acquiring a
decision record, a production, spec prose, examples, and primer coverage —
not by being edited in place.

## Changing the language

Any change to a construct touches all six of these. A change that lands in
fewer is almost certainly incomplete:

1. `spec/sodl.ebnf` — the production, plus any static check the EBNF cannot
   express (there is a numbered list at the foot of the file for those).
2. `spec/SODL_Specification.md` — the normative rules, in prose.
3. `spec/DECISIONS.md` — a new `D<n>` record: what was decided, what was
   rejected, and why. Do not renumber existing records.
4. `examples/example.sodl` and `examples/advanced-examples.sodl` — the
   construct in use. `example.sodl` is core constructs;
   `advanced-examples.sodl` is constraints, TLV, `bytes`, qualified names,
   and instance data.
5. `spec/Primer.md` — how to teach it.
6. `spec/TODO.md` — remove anything the change resolves; add anything it opens.

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
scripts/check-sodl.py          # defaults to the examples/ corpus
cargo test                     # once the toolchain has anything to test
```

`check-sodl.py` must pass before committing. It enforces the rules EBNF
cannot state — key/keymap coherence, redundant props, basic-type collisions.
It reads concrete syntax by regex rather than parsing, so it is easy to
defeat by accident; if a new construct needs a check it cannot see, extend it
or note the gap in `spec/TODO.md` explicitly rather than leaving it silent.

Scripting is Python (match `check-sodl.py`); the toolchain proper is Rust.

## House style

Prose is terse and declarative. Say what the rule is, then what it resolves.
The existing records in `DECISIONS.md` set the register — match it. Examples
carry their weight: every construct in the grammar should appear in at least
one example file, and no example should reference a name that is never
declared.

# Examples

The corpus, grouped by what each file is for. `scripts/run-checks.py` runs
all of it; `cargo test` additionally compares any file beside a `.tree`
golden against the parser's output.

| Directory | Holds |
|---|---|
| `core/` | One core construct per file: `alias`, `const`, `enum`, `struct`, `union`, `keys`, `instance`. |
| `layout/` | D16 layout: `packed`, `fixed`, the ordering rule, byte order. |
| `extensions/` | Extension types (`SODL_Extensions.md`): temporal. |
| `integration/` | The two originals, showing the constructs composed at length. |
| `invalid/` | Files that **must fail**, each with the error codes it must produce. |

## Invalid examples

Each `foo.sodl` has a `foo.expected` naming the error codes it must
produce — `E012`, not the message text. Codes are stable identifiers listed
in `scripts/check-sodl.py`; asserting on them means rewording a diagnostic
does not churn the tests, while a rule that stops firing, or starts firing
for the wrong reason, still fails.

This half of the corpus is the one that matters. A checker that quietly
stops firing is worse than no checker, and the regex implementation is
prone to exactly that: adding D16's layout modifiers silently made every
`packed struct` invisible to every check, and only `invalid/` caught it.

## Golden files

A `foo.tree` beside a `foo.sodl` is the parser's rendering of it, compared
on every `cargo test`. Regenerate with:

```
cargo run --example dump -- examples/core/alias.sodl > examples/core/alias.tree
```

Read the diff before committing a regenerated golden — that is the entire
point of the format being human-readable.

Most of the corpus has no golden yet, because the parser covers only part of
the grammar. The test prints how many files are still uncovered; that number
should fall as the parser grows.

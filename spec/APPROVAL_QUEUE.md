# Approval queue

Items the autonomous loop reached but must not do unattended — each needs a
decision, a normative-spec edit, or a proposal landing to a `D`-record. The
loop drafts and queues; you approve, then it (or you) implements via
TODO → PROPOSAL → DECISION.

## Open

- **`strict` semantics + example.** `strict` is in the grammar and spec but
  its meaning is undefined (TODO, Underspecified). An example cannot be
  written until it is decided: does `strict = <lit>` pin the field to that
  exact literal, and how does it interact with `default` and `required`?
  Needs a decision, then an example. Blocks the last example-coverage gap.

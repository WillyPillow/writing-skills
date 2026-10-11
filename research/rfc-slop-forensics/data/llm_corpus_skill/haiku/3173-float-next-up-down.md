# Rust RFC 3173: float_next_up_down

Document type: Rust language/tooling RFC
Status: [TODO: RFC status and tracking details; the author did not supply them]

## Context and scope

This RFC adds two methods to the floating-point types `f32` and `f64`: `next_up` and `next_down`. Both take no arguments. The operations they perform are specified in the IEEE 754 standard. Together they let a program enumerate the floating-point values of a type in order, moving from one value to its neighbor.

[TODO: How Rust code reaches a neighboring float today, and what that costs. The author has not supplied the existing approaches, such as manipulating the bit representation, or any account of why those approaches fall short.]

## Motivation

[TODO: A concrete goal or obstacle from the author. The material says the methods "provide the capability to enumerate floating point values in order" but does not name a program, library or task that needs this capability. Ask the author for one such case and the workaround it uses now.]

## Goals

- Provide the IEEE 754 successor and predecessor operations for `f32` and `f64`, as methods on each type.
- [TODO: A checkable criterion for this goal, such as a set of input values and the results they must produce. The author should supply it.]

## Non-goals

[TODO: Anything a reader might expect these methods to do that the RFC deliberately excludes. The author has not stated any.]

## Design

The RFC adds one method per direction. `next_up` returns the next representable value toward positive infinity. `next_down` returns the next representable value toward negative infinity.

Because the operations come from IEEE 754, their expected results can be checked against the standard, not only against this RFC. A reviewer who disputes a result can point to the standard's definition for that input.

[TODO: The result of each method for each special input: NaN, positive and negative infinity, positive and negative zero, and the largest finite value. The author should confirm what this RFC specifies for each case, because the material does not say.]

## Alternatives considered

[TODO: Alternatives the author evaluated. The material gives none. Do not record any alternative as considered until the author describes it and the reason it was rejected.]

## Cost

[TODO: What the addition makes harder or gives up. If the author judges that no real alternative existed, one sentence saying so is enough.]

## Reversibility

Once stable, two new public methods on primitive types become part of the public API. [TODO: Whether the RFC treats these names and signatures as expensive to change after stabilization, and the stabilization path.]

## Rollout

[TODO: The steps from this RFC to stabilization, and whether the methods ship behind a feature gate first.]

## Open questions

- [TODO: Points the author has left unresolved and wants reviewers to address.]

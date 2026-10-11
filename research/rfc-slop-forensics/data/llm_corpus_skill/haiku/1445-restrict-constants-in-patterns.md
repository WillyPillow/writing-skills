# Rust RFC 1445: structural_match

Status: [TODO: RFC status, tracking issue and date]

## Summary

The current compiler implements a broader meaning of pattern matching than was originally intended. This RFC introduces mechanisms that rein in those semantics without breaking existing code, or breaking only a little of it. The abstract says "much, if any" breakage, and this document keeps that scope as written. [TODO: how the amount of breakage was measured, on what code, and with what result.]

The abstract is cut off while describing the practical effect of the changes. [TODO: the complete practical effect. See the third mechanism below.]

## Motivation

The abstract states that the compiler's semantics are more expansive than originally intended. It does not say what the expansion permits that the original design did not. [TODO: a concrete case where the broader semantics causes a problem, drawn from the author's material. Name the code that produced the case.]

## Design

The RFC makes three changes. Each is set out below with its force and cost where the material supports them.

### Marking types with an attribute

The RFC introduces `#[structural_match]`, a feature-gated attribute. Applied to a struct or enum `T`, it indicates that constants of type `T` can be used within patterns.

Force: [TODO: the reason the permission is granted per type, rather than to all types or to none. The material does not give this.]

Options: [TODO: the other ways to grant the permission, including leaving the semantics unchanged, each with the reason it lost.]

### Deriving Eq

The second change is that `#[derive(Eq)]` applies `#[structural_match]` to the type it decorates. The abstract also says that automatically inserted attributes do not require the feature gate.

Decision reasoning: [TODO: why deriving `Eq` should grant the permission. The abstract states the rule without the reason for it.]

Cost: any type that derives `Eq` now carries the permission. [TODO: whether any existing type gains the permission through this rule, and whether the author intends that.]

Cost of the feature gate decision: users may see the attribute appear without opting in. [TODO: whether that matters for stability, and the author's judgment of it.]

### Expanding constants

The third change concerns how the compiler expands constants. When a constant of struct or enum type is expanded into an equivalent pattern, the type must carry the attribute. Constants of builtin types are always expanded.

This change decides which constants still work in patterns. The abstract says the practical effect is to prevent some uses of constants in patterns, but the sentence is cut off before saying which uses. [TODO: the complete practical effect, with an example of a constant that stops working and the code it appears in.]

## The central tension

The abstract frames the problem as narrowing what pattern matching accepts while leaving existing code working. The two aims pull against each other, because every narrowing risks breaking something. [TODO: which aim the author judges harder to meet, and the evidence for that judgment.]

## Compatibility

[TODO: the compatibility analysis. The abstract's "much, if any" is a scoped claim, and the document has to say what supports it. State the set of code examined and the method used.]

## Drawbacks

[TODO: the drawbacks of the change, each in its strongest form. The material does not include a drawbacks section.]

## Alternatives

[TODO: the alternatives considered, including keeping the current semantics, each with the reason it lost.]

## Unresolved questions

[TODO: the open points the author has not settled, including the list of types affected by the derive rule and the schedule for the feature gate.]

# Rust RFC 2316: safe_unsafe_trait_methods

## Summary

This RFC allows an `impl` to implement a trait's `unsafe` method without marking the method in the `impl` as `unsafe`. The RFC calls this overconstraining the method in the `impl`. When the trait's `unsafe` method is called on a specific type for which the method is known to be safe, the call does not need an `unsafe` block.

## Motivation

[TODO: Motivation. The summary states what the RFC allows but not the problem it solves. Name the obstacle that forces an implementor to write `unsafe` on a method whose body is safe, and give a concrete example from the material. Without one, the reader cannot judge whether the change is needed.]

## Guide-level explanation

Under this RFC, a trait can declare a method as `unsafe`, and an implementation of that trait can supply the method without the `unsafe` keyword. The implementation is then more constrained than the trait's declaration. That is the sense of "overconstraining" in the summary: the impl promises more than the trait requires.

The effect shows at the call site. A call through the concrete type, where the impl is known, does not require an `unsafe` block. [TODO: Give a short code example with a trait, one `unsafe` method, one overconstrained impl, and a call site on the concrete type. The reader needs a case to test the definition against.]

[TODO: State what a call through a generic bound, or through a trait object, requires. The summary says the call needs no `unsafe` block when the method "is known to be safe" for a specific type, which implies that calls where the type is not known still require one. The material should confirm this.]

## Reference-level explanation

[TODO: Reference-level explanation. The material does not describe how the compiler checks that an overconstrained impl is safe, how the check is applied to the body of the method, or what diagnostic is produced when the check fails. Supply this from the full RFC.]

## Soundness

The rule rests on the claim that an impl may drop `unsafe` only when the method is in fact safe. That claim is the whole safety argument for the RFC, so it needs the most support. [TODO: State the condition under which the method is known to be safe, and the reasoning that establishes it. Do not claim the change is sound until the author has supplied that reasoning.]

## Drawbacks

[TODO: Drawbacks. The summary names no cost. Ask the author what the change makes harder: for example, whether a reader of the trait now has to inspect each impl to learn whether a method requires `unsafe`, and whether the change gives implementors a way to hide an unsafe body.]

## Alternatives

[TODO: Alternatives. The material does not record any alternative to overconstraining, such as leaving the rule as it is, or requiring a separate marker. Ask the author which alternatives were considered and why each was rejected. Do not list options the author has not named.]

## Open questions

The material leaves open how an overconstrained method interacts with other language features that depend on the trait's signature, such as default method bodies and associated types. [TODO: Name each interaction the RFC addresses, or state that the RFC leaves it unspecified.]

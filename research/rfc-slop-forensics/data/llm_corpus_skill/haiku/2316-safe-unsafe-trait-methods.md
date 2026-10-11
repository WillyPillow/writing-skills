# Rust RFC 2316: safe_unsafe_trait_methods

Document type: Rust language/tooling RFC
Status: [TODO: status]
Author: [TODO: author names]
Date: [TODO: date]

## Summary

This RFC allows an `impl` of a trait to implement a method marked `unsafe` in the trait without marking that method `unsafe` in the `impl`. The abstract calls this overconstraining the method in the `impl`: the implementation promises more than the trait requires. When the trait's `unsafe` method is called on a specific type whose method is known to be safe, the call does not need an `unsafe` block.

The abstract is short, and the RFC is best read as one rule with three consequences. The rule is that an `impl` may drop `unsafe` from a method. The first consequence is that a call on the concrete type needs no `unsafe` block. The second and third consequences depend on how calls through generic code and trait objects are handled, which the abstract does not describe. [TODO: author to confirm the consequences and state the rule in one sentence.]

## Motivation

The abstract does not say why an implementor would want a safe body for a method that the trait declares `unsafe`. The reader needs the reason before the rule can be judged. [TODO: the problem. State a concrete case in which a type's implementation has no preconditions, and explain what the current rule requires the author to write.]

Under the current rule, the `impl` must carry the `unsafe` marker as well. The cost of that requirement is the thing this RFC removes, and the text should say what the cost is for a user of the trait. For example, a caller who knows the concrete type gets no benefit from the marker, but must still write an `unsafe` block at each call site. [TODO: confirm this case from the author's material, with a real crate or codebase where it happens, and the number of call sites affected if the author has counted them.]

## Terminology

Several terms need one meaning throughout this document.

- An *unsafe trait* is a trait whose contract the implementor must uphold for the program to be sound.
- An *unsafe method* is a method declared `unsafe` in a trait or in an `impl`.
- *Overconstraining* is the abstract's term for implementing an `unsafe` trait method without the `unsafe` marker in the `impl`.
- *Known to be safe* appears in the abstract without a definition. The whole rule depends on it. [TODO: define what makes the compiler treat a method on a specific type as known to be safe, and whether the definition is made by the `impl`, by the type checker, or by both.]

## Design

The overview is the rule from the summary. An `impl` may leave the `unsafe` marker off a method that the trait marks `unsafe`. The shape of the code the abstract describes is the following. This is an illustration of the rule, and the exact syntax is for the author to confirm. [TODO: confirm the syntax with the author, and replace this sketch with the RFC's own example.]

```rust
unsafe trait Example {
    unsafe fn run(&self);
}

impl Example for Thing {
    fn run(&self) {
        // body with no preconditions
    }
}
```

Three points need answers in the text. First, the soundness of the trait's contract. The `unsafe` marker on the trait declares that the implementor takes on a proof obligation. The abstract does not say who carries the obligation for a method implemented without `unsafe`. [TODO: state who must uphold the contract for each implementation, and whether a safe `impl` method changes that obligation.]

Second, calls through a generic bound. A function that takes `T: Example` and calls `run` on its argument does not know the concrete type. The abstract says a call needs no `unsafe` block only when the type is known. [TODO: state whether a generic call still requires `unsafe`. This decides whether the rule helps generic code at all.]

Third, trait objects. [TODO: state whether a call through a trait object can use the safe `impl` method, and what the compiler checks at the point of the call.]

## Decision: Allow Overconstraining

This section records the central decision and the force behind it. The skill's template asks for five parts, and the material supplies only some of them.

The force is the case in which a type's method has no preconditions, yet a caller who uses the trait must still write `unsafe`. The abstract does not give a number. [TODO: the force, with a measured or counted case from the author's material.]

The options are to keep the current rule, which requires the `impl` to carry the marker, and to allow overconstraining, which this RFC proposes. The status quo should be stated in its strongest form, including the argument that the `unsafe` marker on every `impl` keeps the reader's attention on the boundary where the proof obligation lies. [TODO: the author's account of the status quo, and whether it was weighed.]

The deciding reason is not given. The abstract's rule is simple, but simplicity is not a reason in itself. The text must say which factor outweighs the others. [TODO: the deciding reason.]

The cost is not given. Allowing an `impl` to be safe where the trait is unsafe changes what a reader can learn from the `unsafe` keyword at the call site, and it may make the boundary of the proof obligation harder to find. Those are claims about cost, and each needs support. [TODO: the costs the author accepts, and how the author checked them.]

Reversibility is the last part. A change to what an `impl` is allowed to do becomes part of the language surface, and code written against it may stop compiling if the rule is later removed. [TODO: the author's assessment of how expensive a later removal would be, and which code would break.]

## Alternatives Considered

The material names no alternatives. Two are predictable enough that the author should address them. One is to require the `unsafe` marker on the `impl` but to allow the call site to omit the `unsafe` block when the type is known. Another is to add a separate trait for safe implementations. These are suggestions for the author to evaluate, not options that were considered. [TODO: the alternatives the author considered and rejected, each with the reason it lost.]

## Rollout and Compatibility

The abstract does not describe whether any existing code changes meaning under the rule. Allowing an `impl` to drop `unsafe` could make code that compiled before behave differently, or it could be purely additive. The author must state which, with evidence. [TODO: compatibility statement, with the basis for it.]

## Open Questions

- Whether a generic call still requires `unsafe`. [TODO: see Design.]
- Whether a trait object can use the safe `impl` method. [TODO: see Design.]
- Who carries the proof obligation for a safe `impl` method. [TODO: see Design.]
- What "known to be safe" means in the rule. [TODO: see Terminology.]

# Rust RFC 2316: safe_unsafe_trait_methods

- Start Date: 2018-01-19
- RFC PR: (placeholder)
- Rust Issue: (placeholder)

## Summary

This RFC allows an `impl` block to provide a safe implementation of a trait method that the trait declares as `unsafe`. The implementing type may *overconstrain* the method by omitting the `unsafe` qualifier. When a call is made through the concrete type, where the method is known to be safe, the call does not need to appear inside an `unsafe` block. Calls made through the trait, or through a generic parameter bounded by the trait, continue to require `unsafe`, because the caller cannot know which implementation is in use.

## Motivation

Unsafe trait methods are used to express contracts that the compiler cannot check. A trait may say that an operation is only valid under some condition, such as that a pointer is aligned or that an index is in bounds. The trait author marks the method `unsafe` so that every caller, including callers that only see the trait, is forced to acknowledge the obligation.

Some implementations do not need the obligation at all. A type that stores its data in a way that makes the condition trivially true can implement the method with no `unsafe` code, and it would be natural to mark the method safe in that case. At present the language does not allow this. The implementation must also be marked `unsafe`, even though its body contains no unsafe operations, and every caller that uses the concrete type must write an `unsafe` block to call it. This makes code noisier and gives readers the wrong impression that something dangerous is happening.

The problem appears most often in generic code that is specialized for a few types. A method on a numeric wrapper, for example, may be safe for all integer types but unsafe in a trait that is implemented for both integers and raw pointers. Authors currently work around this by writing wrapper functions that are safe and that hide the unsafe call. The workarounds are repetitive and do not help the compiler reason about the code.

## Guide-level explanation

Suppose a trait describes a conversion that is only sound when a certain invariant holds. The trait declares the conversion method as `unsafe fn`. An implementation for a type that always satisfies the invariant may write the method without the `unsafe` keyword in the `impl`, and the body may contain no unsafe operations.

```rust
trait Reinterpret {
    unsafe fn reinterpret(&self) -> u32;
}

struct Flag(u32);

impl Reinterpret for Flag {
    fn reinterpret(&self) -> u32 {
        self.0
    }
}
```

A call such as `Flag(3).reinterpret()` does not require an `unsafe` block, because the receiver type is known and the method is known to be safe. A call through a generic bound `T: Reinterpret` still requires an `unsafe` block, because the function that is called might be an unsafe implementation.

The rule is therefore that the safety of a method is determined by the implementation that is actually selected. The compiler checks each call against the most specific implementation that it can see.

## Reference-level explanation

The change affects the check that determines whether a method call requires an `unsafe` context. When the compiler resolves a method call to a specific `impl` item, it consults the signature of that item rather than the signature in the trait. If the `impl` item is not marked `unsafe`, the call is treated as safe. If the call is resolved through a trait object or through a type parameter, the signature from the trait is used, as is done today.

An `impl` that overconstrains an unsafe method must be a complete implementation of the method. It cannot add new unsafe requirements that the trait did not declare, and it cannot weaken the contract of the trait in any way that would make the safe call unsound. The compiler does not check the soundness of the implementation; it relies on the author to make that determination, just as it does for the body of any unsafe function.

The signature of an overconstrained method must otherwise match the trait declaration. Argument types, return types, generic parameters and lifetimes must agree exactly. Only the presence of the `unsafe` qualifier may differ.

The RFC does not change the rules for overriding methods in the other direction. A safe method in a trait cannot be implemented as an unsafe method, because that would widen the set of callers that need an `unsafe` block for no benefit.

## Drawbacks

The change adds a second place where the safety of a call is determined, and this may surprise readers who expect the trait to be the authority. A reader who looks only at the trait may believe a call requires `unsafe` when it does not. Tooling such as documentation and language servers will need to show the signature of the implementation when it is known.

The change also makes it easier to write code that appears safe but relies on a precondition that is enforced only by convention. An author who overconstrains a method incorrectly will not be told by the compiler. This is the same risk that exists for any unsafe block, but the risk is now more hidden, because the signature no longer announces it.

## Rationale and alternatives

The main alternative is to keep the current rules and to rely on wrapper functions. This works, but it duplicates code and makes the intent of the wrapper harder to see. It also means that the unsafe block is written in one place and then hidden from the callers that might otherwise make a mistake.

A second alternative is to allow the trait to declare that a method is unsafe only for some implementations, through a conditional mechanism. This is more expressive, but it adds complexity to the trait system and is not needed to solve the problems described in the motivation.

A third alternative is to forbid overconstraining entirely, but to allow the trait to declare a default implementation that is safe. This does not help in the common case where each implementation must be written separately.

The chosen design is the smallest change that removes the unnecessary `unsafe` qualifier from calls where the implementation is known, and it keeps the existing rules for all calls that go through the trait.

## Prior art

Other languages with explicit effect annotations generally allow an implementation to be more precise than the interface that it satisfies. The difference is that in those languages the rule is usually a subtyping rule, which the compiler applies to the value's static type. The approach taken here is less general but fits the existing structure of method resolution in the compiler.

## Unresolved questions

It is not yet decided whether the rule should apply to associated functions that do not take a receiver. Such functions are resolved through a path rather than a method call, and the implementation may need a separate check.

It is also an open question how the feature interacts with specialization. If specialization is stabilized in a form that allows a more specific impl to be selected at a call site, the overconstrained signature of the specialized impl should be used, but this has not been checked against the specialization design.

## Future possibilities

If the feature is accepted, the lints that warn about unnecessary `unsafe` blocks can be extended to cover the case where a block is written around a call that has become safe through overconstraining. Documentation for the standard library may also be updated to indicate where safe implementations of unsafe trait methods are used, although this is outside the scope of the present RFC.

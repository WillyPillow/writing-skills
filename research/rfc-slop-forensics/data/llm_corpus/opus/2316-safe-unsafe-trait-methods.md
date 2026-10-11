- Feature Name: `safe_unsafe_trait_methods`
- Start Date: 2018-01-30
- RFC PR: [rust-lang/rfcs#2316](https://github.com/rust-lang/rfcs/pull/2316)
- Rust Issue: (none yet)

# Summary
[summary]: #summary

This RFC allows safe implementations of `unsafe` trait methods. An `impl` may implement a trait whose methods are marked `unsafe` without marking those methods `unsafe` in the `impl`. We call this *overconstraining* the method in the `impl`. When the trait's `unsafe` method is called on a concrete type for which the method is known to be safe, the call does not require an `unsafe` block.

# Motivation
[motivation]: #motivation

An `unsafe fn` in a trait expresses a contract: callers must uphold some precondition that the compiler cannot check, and implementations are allowed to rely on that precondition. The `unsafe` is a property of the *trait's* interface. Nothing about that requires every implementation to actually depend on the precondition.

Many implementations do not. Consider a trait for raw indexing:

```rust
trait RawIndex {
    type Output;
    /// # Safety
    /// `i` must be less than `self.len()`.
    unsafe fn get_unchecked(&self, i: usize) -> &Self::Output;
}
```

An implementation for a type that internally bounds-checks anyway, or for a type where every index is valid (say, a function `usize -> T` stored as a lookup that wraps around), has no reason to require `unsafe` from its callers. Today the author must still write:

```rust
impl RawIndex for Wrapping {
    type Output = u8;
    unsafe fn get_unchecked(&self, i: usize) -> &u8 {
        &self.data[i % self.data.len()]
    }
}
```

and anyone using `Wrapping` directly, knowing its concrete type, must still write `unsafe { w.get_unchecked(5) }`. That has two costs:

1. **Noise.** `unsafe` blocks are meant to be rare markers that draw a reviewer's eye. Every spurious `unsafe` block dilutes that signal.
2. **Lost information.** Inside an `unsafe fn` body, the whole body is an unsafe context (in current Rust). The author of `Wrapping::get_unchecked` above gets no help from the compiler if they accidentally call some other unsafe function. Declaring the method safe would make the compiler check the body properly.

The common workaround is to write an inherent method with the safe signature and have the trait method forward to it. This works, but duplicates every method and every doc comment, and it is easy for the two to drift.

This situation already has a precedent in Rust: implementations may be *more general* than the trait requires in some respects, for example by having fewer where clauses on a method than the trait declares. Allowing a safe method where an unsafe one is declared follows the same principle: an implementation may promise more than the trait requires.

# Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

When a trait declares a method `unsafe`, it means *some* implementations may need callers to uphold extra conditions. If your implementation does not need them, you may leave off `unsafe`:

```rust
impl RawIndex for Wrapping {
    type Output = u8;
    fn get_unchecked(&self, i: usize) -> &u8 {   // no `unsafe`
        &self.data[i % self.data.len()]
    }
}
```

The body of this method is now checked as ordinary safe code.

When you call the method on a value whose type is known to be `Wrapping`, no `unsafe` block is needed:

```rust
let w = Wrapping::new(vec![1, 2, 3]);
let x = w.get_unchecked(10); // fine
```

When you call it through the trait generically, the trait's signature applies, and `unsafe` is still required:

```rust
fn first<T: RawIndex>(t: &T) -> &T::Output {
    unsafe { t.get_unchecked(0) } // still needs unsafe
}
```

This is the same reasoning you already use with generics: in generic code you only know what the trait promises; with a concrete type you know what that type promises.

# Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

## Implementation checking

When checking that an `impl` method matches the trait method, the compiler currently requires the `unsafe` qualifier to match exactly. This RFC relaxes the check:

- If the trait method is `unsafe fn`, the impl method may be either `unsafe fn` or `fn`.
- If the trait method is `fn`, the impl method must be `fn`. Adding `unsafe` in an impl remains an error, since that would weaken the trait's guarantee.

Other qualifiers (`const`, `async`, `extern "ABI"`) are unaffected by this RFC.

## Method resolution and call checking

Method resolution is unchanged. When a call resolves to a method on a concrete impl, the unsafety check uses the signature declared in that impl. When the call is resolved through a trait bound (a type parameter, an associated type projection that cannot be normalized, or a `dyn Trait` object), the unsafety check uses the trait's signature.

Concretely, the signature used for the unsafety check is the signature of the item the call resolves to after normalization. If the compiler resolves `<Wrapping as RawIndex>::get_unchecked` to the specific impl item, that item's safety applies.

## Function pointers and coercions

Taking a reference to the method through the concrete path produces a function item whose type reflects the impl's signature:

```rust
let f: fn(&Wrapping, usize) -> &u8 = <Wrapping as RawIndex>::get_unchecked;
```

is permitted. A safe `fn` item already coerces to an `unsafe fn` pointer, so taking the trait-level path still works where an unsafe pointer is expected.

## Trait objects

For `dyn RawIndex<Output = u8>`, the vtable entry is typed according to the trait. Calls through a trait object always require `unsafe`, regardless of which implementation is behind it. No vtable layout changes are needed, since a safe and an unsafe function with the same ABI are interchangeable at the machine level.

## Lints

A new allow-by-default lint, `unsafe_trait_method_overconstrained` or similar, may be added for crates that wish to be told when an impl drops `unsafe`. This is left as an implementation detail.

# Drawbacks
[drawbacks]: #drawbacks

- **Semver hazard.** Once an impl is published with a safe method, removing that safety (adding `unsafe` back) is a breaking change for downstream users who call it on the concrete type. Library authors need to understand that dropping `unsafe` is a public commitment. This mirrors the existing situation for inherent methods.
- **Readers must look at the impl.** Someone reading `w.get_unchecked(10)` without an `unsafe` block, who knows the trait method is unsafe, may be briefly surprised. Tooling (rustdoc, IDE hover) mitigates this by showing the impl's signature.
- **Increased complexity** in the compiler's comparison of impl and trait items, though the change is small.

# Rationale and alternatives
[rationale-and-alternatives]: #rationale-and-alternatives

**Do nothing.** The forwarding-method workaround remains available. It is verbose and error-prone, and it hides the fact that the trait method is safe for this type.

**An attribute instead of dropping the keyword.** Something like `#[safe] unsafe fn ...` was considered. It adds a new concept where simply omitting `unsafe` reads naturally and matches how the impl would be written for an ordinary safe trait.

**Generalize to refinement of all signature aspects.** A broader "refined impls" feature, where an impl may return a more specific type or have a more permissive signature and callers on concrete types see the refined version, would subsume this RFC. That is a larger design question. This RFC is deliberately limited to `unsafe` because it has no interaction with type inference and is easy to explain, and it is forward compatible with a more general mechanism.

# Prior art
[prior-art]: #prior-art

Rust already allows impl methods to have fewer where clauses than the trait method. Many languages with checked exceptions (Java) allow an overriding method to declare fewer exceptions than the method it overrides, and callers using the subclass type benefit. Covariant return types in Java and C++ follow the same idea of an implementation promising more than its interface.

# Unresolved questions
[unresolved-questions]: #unresolved-questions

- Should rustdoc show the trait's or the impl's safety on the implementor's page? This RFC suggests the impl's, with a note.
- Should the lint mentioned above exist, and should it be on by default for public impls?
- How does this interact with a future `unsafe` on associated constants or types, if those are ever introduced?

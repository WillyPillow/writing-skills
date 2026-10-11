# Rust RFC 2316: safe_unsafe_trait_methods

## Summary

This RFC allows an `impl` to implement an `unsafe` trait method with a method that is not marked `unsafe`. The method in the `impl` is then said to *overconstrain* the trait's method: it demands less of its caller than the trait's signature does. When code calls the method on a concrete type whose `impl` is safe, the call does not need an `unsafe` block. Calls made through the trait, for example in generic code, still need one.

## Motivation

A trait method is marked `unsafe` when some implementations can be called correctly only if the caller upholds a condition the compiler cannot check. The trait declares the strictest contract, and every caller of the trait method must meet it.

Many implementations do not need that strictness. Consider a trait whose `unsafe` method reads from a pointer, with the caller promising the pointer is valid. An implementation for a type that owns its data and never touches a raw pointer has no such precondition. Today that implementation must still be written as `unsafe fn`, and every direct call on that type must sit in an `unsafe` block, although nothing in the call is unsafe.

The consequence is that an `unsafe` block appears where the reader has no obligation to check anything. `unsafe` blocks mark the places where a reviewer must verify an invariant. Blocks that carry no invariant dilute that signal. [TODO: give a concrete trait from the author's material, with the real implementations that motivated the RFC. The example above is invented for illustration and must be replaced.]

The RFC removes the false obligation for calls on types that are known to be safe.

## Guide-level explanation

Take a trait with an unsafe method:

```rust
trait Frobnicate {
    unsafe fn frob(&self);
}
```

An `impl` may write the method without `unsafe`:

```rust
struct Quiet;

impl Frobnicate for Quiet {
    fn frob(&self) { /* no precondition */ }
}
```

This is overconstraining, and the rest of the type system follows from it:

* `Quiet.frob()` compiles without an `unsafe` block, because the compiler resolves the call to the `impl`'s own method, which is safe.
* A generic function `fn go<T: Frobnicate>(t: &T) { t.frob() }` still needs `unsafe`, because inside `go` the compiler knows only the trait's signature.

The same type can be used both ways. Calling through the concrete type is safe. Calling through the trait is not.

The reverse is not allowed. A trait method declared safe cannot be implemented with an `unsafe` method, because that would let safe code reach an unsafe operation. [TODO: confirm with the author that this is already an error today and is not changed by the RFC. The sentence follows from the existing rule that an impl must be at least as permissive as its trait.]

## Reference-level explanation

The check that an `impl` method matches its trait signature currently requires the `unsafe` qualifier to be equal. This RFC relaxes it to: the `impl` method may drop `unsafe` when the trait method has it. [TODO: state the exact change in the compiler, including which diagnostics are removed and which stay. If the RFC covers `unsafe` inherent items in the same way, say so.]

Method resolution does not change. Whether a call needs `unsafe` is decided by the signature of the item the call resolves to. For a call on a concrete type, that item is the `impl`'s method. For a call through a type parameter or a trait object, it is the trait's method.

[TODO: state how this interacts with trait objects, `dyn Frobnicate`, and with default method bodies. For a trait object, the vtable entry comes from the `impl`, but the call site only knows the trait, so the RFC presumably keeps the `unsafe` requirement there. Ask the author to confirm.]

## Drawbacks

The same method name now has two different safety contracts depending on the path used to call it. A reader who sees `x.frob()` without `unsafe` cannot tell from the call site whether `x` is a concrete type with a safe `impl`, or whether the code is missing a block. The compiler enforces the distinction, so this is a question of readability and not of soundness. [TODO: the soundness claim needs the author's argument or reference to the Rust reference. As written it is an assertion.]

A library author who changes an `impl` from safe back to `unsafe` breaks callers who relied on the safe form. The relaxation thus adds a new thing to the public API surface of a type: whether each trait method on it is safe. [TODO: ask the author how semver treatment of this change is expected to work.]

The RFC also adds a rule the language teaches. Beginners who learn that an `impl` must match the trait now meet an exception.

## Rationale and alternatives

The RFC proposes to allow overconstraining in the `impl` and leave the trait unchanged. A reader will reasonably ask why not the simpler option of leaving things as they are. The answer given in the motivation is the noise from needless `unsafe` blocks. The cost of the status quo is thus a loss of signal in code review, and no number is available for it. [TODO: ask whether the author has counts of needless `unsafe` blocks in real crates.]

[TODO: list the alternatives actually considered. Candidates to ask about, none of which can be presented as considered without confirmation:
* Split the trait into a safe and an unsafe version.
* Provide a safe inherent method on the type that wraps the trait method.
* Add an attribute to the trait method that marks it as safe to override.]

Of these, the inherent-method option needs no language change, and any rationale must explain why it falls short. The material available gives no such explanation.

## Prior art

[TODO: the author has supplied no references to other languages or earlier Rust RFCs. If the RFC builds on an earlier discussion of `unsafe` in traits, cite it here.]

## Unresolved questions

1. How does overconstraining interact with trait objects and default method bodies?
2. Does the lint set warn about an `unsafe` block around a call that no longer needs one? Such a block would now trigger `unused_unsafe`. [TODO: confirm that the existing lint behaves this way.]
3. Is the same relaxation wanted for other qualifiers, such as `const`?
4. What documentation change is needed in the Reference and the Nomicon?

## Future possibilities

None are stated in the material. [TODO: ask whether the author intends to extend overconstraining to associated types or to trait bounds.]

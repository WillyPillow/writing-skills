- Feature Name: `safe_unsafe_trait_methods`
- Start Date: 2018-01-24
- RFC PR: rust-lang/rfcs#2316
- Rust Issue: rust-lang/rust#87

# Summary
[summary]: #summary

This RFC allows safe implementations of `unsafe` trait methods. An `impl` may implement a trait with methods marked as `unsafe` without marking the methods in the `impl` as `unsafe`. This is referred to as *overconstraining* the method in the `impl`. When the trait's `unsafe` method is called on a specific type where the method is known to be safe, that call does not require an `unsafe` block.

# Motivation
[motivation]: #motivation

Some trait methods are `unsafe` because a generic caller cannot know whether the call is sound for every implementor. The trait author has to write down the strongest requirement that any implementor might need. In practice, many implementors need no such requirement at all.

Take a trait for reading from a raw buffer:

```rust
trait Buffer {
    /// Returns the byte at `index`.
    ///
    /// # Safety
    /// `index` must be less than `self.len()`.
    unsafe fn get_unchecked(&self, index: usize) -> u8;
    fn len(&self) -> usize;
}
```

A type that wraps a fixed-size array and ignores the index in a way that is always in bounds, or a type that does bounds checking internally, can implement this method with no precondition at all. Today the implementation looks like this:

```rust
impl Buffer for Zeros {
    unsafe fn get_unchecked(&self, _index: usize) -> u8 { 0 }
    fn len(&self) -> usize { usize::MAX }
}
```

The `unsafe` here is noise. It tells readers the method has a contract when it does not. Worse, callers who hold a concrete `Zeros` must still write:

```rust
let z = Zeros;
let b = unsafe { z.get_unchecked(5) };
```

This `unsafe` block is also noise. The compiler could see that the method called is safe, but it must treat the call as unsafe because the trait signature says so. Unnecessary `unsafe` blocks weaken the signal that `unsafe` is supposed to send. A reader scanning for dangerous code has more to wade through, and the `unused_unsafe` lint does not fire, because the lint only knows about the trait method.

The same pattern appears in the standard library and in the wider ecosystem. For instance, trait methods like `GlobalAlloc::dealloc` or methods on `Searcher` have many implementations where a given method is trivially safe. A library author wants to say: this trait has a method with a precondition in general, but for my type there is none.

# Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

When a trait declares a method as `unsafe`, implementors are normally required to write `unsafe` as well. This RFC relaxes the rule in one direction. An implementor may drop the `unsafe` and provide a safe method that accepts the same arguments and returns the same type.

```rust
trait Foo {
    unsafe fn foo(&self);
}

struct Bar;

impl Foo for Bar {
    fn foo(&self) {
        // This implementation is safe to call under any circumstances.
    }
}
```

Think of it as follows. The trait says "calling `foo` might have a precondition". The implementation says "for `Bar`, there is no precondition". A safe function can be used anywhere an unsafe function with the same signature is expected, because a function that has no requirements satisfies any set of requirements.

When you call the method through the concrete type, no `unsafe` block is needed:

```rust
let bar = Bar;
bar.foo(); // OK, resolves to the safe impl
```

When you call it through a generic parameter or a trait object, the compiler only knows the trait signature, so `unsafe` is still required:

```rust
fn call_foo<T: Foo>(t: &T) {
    unsafe { t.foo() } // required
}
```

The `unsafe` block above is not removed, even if `T` happens to be `Bar`. Generic code must be written against the trait contract.

The reverse is not allowed. An implementation cannot declare a method `unsafe` if the trait declares it safe, because callers of the trait would then be able to invoke unsafe behavior without an `unsafe` block.

# Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

## Impl checking

When checking that an `impl` item matches the corresponding trait item, the compiler currently requires that the `unsafe`ness of the two be equal. This RFC changes the check as follows:

- If the trait method is `unsafe` and the impl method is `unsafe`, accepted.
- If the trait method is `unsafe` and the impl method is safe, accepted.
- If the trait method is safe and the impl method is `unsafe`, rejected, with the existing error.
- If both are safe, accepted.

All other parts of the signature comparison are unchanged.

The same rule applies to associated functions that have no `self` parameter, and to default method bodies that are overridden.

## Method resolution

Method resolution happens before the `unsafe` check. When the receiver type is concrete and the selected impl method is safe, the call expression is not considered an unsafe operation. When resolution goes through a type parameter bound or a trait object, the method selected is the trait's declaration, and the call is unsafe.

When a path expression such as `<Bar as Foo>::foo` names a specific impl, it resolves to the impl's item and has a safe function type. If the path is `Foo::foo` with an inferred `Self`, it has unsafe function type until `Self` is known. If `Self` is later inferred to be `Bar`, the call remains unsafe, because the decision was made when type checking the path against the trait. Implementations may choose to refine this, but this RFC does not require it.

## Function pointers

A function item for a safe impl method has the type `fn(&Bar)` and can be coerced to `unsafe fn(&Bar)`, as is already true for any safe function item. This lets code store such methods in tables of `unsafe fn` pointers.

## Lints

The `unused_unsafe` lint fires on an `unsafe` block that wraps only calls to safe impl methods. Since this is the point of the RFC, that is expected behavior.

Rustdoc shows the impl method as safe, which is accurate.

# Drawbacks
[drawbacks]: #drawbacks

**The signature on the impl differs from the signature on the trait.** Readers who learned "an impl must match its trait" may be surprised. However, Rust already allows an impl to be more specific in some ways, for example by using a concrete lifetime where the trait uses a generic one in limited cases, or by returning a more specific `impl Trait` in the future. The `unsafe` relaxation fits the same pattern.

**Semver hazards.** If a library implements a trait method safely, and downstream users call it without `unsafe`, then changing the impl to `unsafe` is a breaking change. Authors who want to keep room to add preconditions should keep the method `unsafe`. This is a cost the author opts into by dropping the keyword.

**Trait authors lose some control.** A trait author may want every implementation to be marked `unsafe` so that every call site has a visible marker. They can still write the documentation to say so, but the compiler will not enforce it. The authors of this RFC think this is rare. Traits that must have unsafe implementors can use `unsafe trait`, which is a different mechanism and is unaffected.

# Rationale and alternatives
[rationale-and-alternatives]: #rationale-and-alternatives

The main rationale is principled: `unsafe` on a function says "the caller has obligations". A function with fewer obligations is always a valid substitute for one with more, in the same way that a function that accepts more inputs can substitute for one that accepts fewer.

**Alternative: do nothing.** Authors continue to write unneeded `unsafe` in impls. Callers continue to write unneeded `unsafe` blocks. The cost is small per instance but persistent.

**Alternative: an attribute.** An attribute such as `#[safe_impl]` could mark the relaxation explicitly. This adds ceremony without clear value. Dropping a keyword is already a visible act, and the compiler is able to check that the body does not contain unsafe operations without an `unsafe` block.

**Alternative: allow it only for the type's own inherent methods.** This does not help with trait-based APIs, which is where the pattern occurs.

**Alternative: apply the same idea to other properties.** For example, a trait method could be declared `const` and the impl non-const, or the reverse. This RFC covers only `unsafe`.

# Prior art
[prior-art]: #prior-art

Many languages allow a method override to weaken preconditions and strengthen postconditions, a rule known as contravariance of arguments and covariance of results, or the Liskov substitution principle. Eiffel enforces this for contracts directly. Here, "safe" corresponds to an empty precondition.

# Unresolved questions
[unresolved-questions]: #unresolved-questions

- Should `unused_unsafe` have a special message when the block only contains such calls?
- Should the path form `Foo::foo` refine to safe once `Self` is known?

# Future possibilities
[future-possibilities]: #future-possibilities

The same relaxation could be applied to `unsafe` blocks inside `async` functions, and to trait objects of a sealed set of types, if Rust ever supports closed trait hierarchies. Neither is proposed here.

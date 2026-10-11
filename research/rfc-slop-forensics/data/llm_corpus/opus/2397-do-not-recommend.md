- Feature Name: `do_not_recommend`
- Start Date: 2018-04-07
- RFC PR: rust-lang/rfcs#2397
- Rust Issue: (none yet)

# Summary

Add a new attribute, `#[do_not_recommend]`, that may be placed on trait implementations. When an impl carries this attribute, the compiler will not mention that impl, or the bounds it requires, when explaining why some other trait obligation could not be satisfied. The canonical use is the blanket impl `impl<T: Iterator> IntoIterator for T`: with the attribute in place, a failed `T: IntoIterator` obligation produces an error about `IntoIterator` alone, instead of suggesting that the user implement `Iterator`.

# Motivation

When trait resolution fails, rustc tries to be helpful. If there is exactly one impl that could apply to the type in question, the compiler follows that impl and reports the first nested obligation it could not prove. Most of the time this produces a better error. If a user writes `foo(x)` where `foo` requires `T: Display` and there is an impl `impl<T: Debug> Display for Wrapper<T>`, being told that `T: Debug` is unsatisfied gets to the real cause faster than being told that `Wrapper<T>: Display` is unsatisfied.

For some blanket impls, though, this behaviour actively misleads. Consider:

```rust
struct Config { /* ... */ }

fn main() {
    let c = Config { /* ... */ };
    for item in c {
        println!("{:?}", item);
    }
}
```

Today the error reads roughly:

```text
error[E0277]: the trait bound `Config: std::iter::Iterator` is not satisfied
  |
  |     for item in c {
  |                 ^ `Config` is not an iterator; maybe try calling `.iter()` or a similar method
  |
  = help: the trait `std::iter::Iterator` is not implemented for `Config`
  = note: required by `std::iter::IntoIterator::into_iter`
```

The user did not ask for an `Iterator`. The `for` loop desugars to a call to `IntoIterator::into_iter`, and the compiler saw that the only impl that could possibly apply to `Config` is the blanket `impl<T: Iterator> IntoIterator for T`, so it reported the nested obligation. A user who wants to make their type usable in a `for` loop should almost always implement `IntoIterator` (often for `&Config` as well), not `Iterator`. Implementing `Iterator` directly on a collection type is a known anti-pattern because it forces the collection to carry iteration state.

The same problem shows up across the ecosystem. Diesel, for instance, has blanket impls like `impl<T: Expression> AsExpression<T::SqlType> for T`. When a user passes the wrong type to a query builder function, the error mentions `Expression`, a trait that is an implementation detail from the user's point of view, rather than the `AsExpression` bound that actually appears in the signature they called. Library authors have no way today to say "this impl exists for convenience; don't use it to explain errors".

The attribute gives library authors that control while leaving the default heuristics unchanged for everyone else.

# Guide-level explanation

A trait implementation may be annotated with `#[do_not_recommend]`:

```rust
#[do_not_recommend]
impl<T: Iterator> IntoIterator for T {
    type Item = T::Item;
    type IntoIter = T;
    fn into_iter(self) -> T { self }
}
```

This has no effect on whether code compiles. The impl still applies to every `T: Iterator`, coherence still treats it exactly as before, and method resolution is unaffected. The only thing that changes is the content of error messages.

When the compiler cannot prove `Config: IntoIterator`, it would ordinarily notice that the blanket impl is the sole candidate and descend into it, reporting `Config: Iterator` as the failure. With `#[do_not_recommend]`, the compiler stops at the outer obligation and reports:

```text
error[E0277]: `Config` is not iterable
  |
  |     for item in c {
  |                 ^ `Config` cannot be iterated over
  |
  = help: the trait `std::iter::IntoIterator` is not implemented for `Config`
```

A good rule of thumb for library authors: put `#[do_not_recommend]` on a blanket impl when the trait in the impl's bounds is not something you want your users to implement in order to satisfy the outer trait. If implementing the inner trait is a reasonable and intended way to satisfy the outer one, leave the attribute off.

# Reference-level explanation

The attribute `#[do_not_recommend]` is accepted only on `impl Trait for Type` items. Placing it on an inherent impl, a function, or any other item is an error.

During error reporting for an unfulfilled obligation `O`, rustc currently walks the chain of obligations from the one the user wrote down to the leaf that failed, and reports the leaf (with "required by" notes for the intermediate steps). This RFC modifies that walk as follows:

1. When walking from obligation `O` into a nested obligation `N` that arose because impl `I` was selected (or was the unique candidate) for `O`, check whether `I` has the `#[do_not_recommend]` attribute.
2. If it does, stop the walk at `O` and report `O` as the unsatisfied obligation. `N` and any obligations beneath it are not mentioned, including in "required by" notes.
3. If it does not, continue as today.

The check happens per step of the walk, so a chain that passes through several impls is truncated at the outermost marked impl.

The attribute has no effect on:

- trait selection, candidate assembly, or coherence;
- type inference;
- whether code compiles;
- diagnostics produced for errors that are not trait-bound failures.

Because the attribute affects only diagnostics, it is permitted to have no effect at all. An implementation that ignores it entirely is conforming. This keeps the attribute from becoming a semantic commitment that the trait solver must respect in perpetuity, and leaves room for future changes to the trait system (for example, a new solver) to approximate its behaviour.

Initially the attribute is unstable and gated behind `#![feature(do_not_recommend)]`. The standard library may use it internally before stabilization.

# Drawbacks

- It is another attribute, and another thing for library authors to learn about. The cost is mitigated by the fact that ignoring it is harmless.
- Misapplying the attribute can make errors worse. If a library author marks an impl whose inner bound really is the thing a user should implement, users lose a useful hint. This is a quality issue in the library, not unsoundness, but it is still a cost.
- Diagnostics are already one of the more intricate areas of rustc. Adding a user-visible knob to the error-reporting walk adds another case to maintain and test.

# Rationale and alternatives

**Do nothing.** We could try to improve the heuristic so that it guesses which impls are "convenience" impls. Possible signals include: the impl is a blanket impl over a bare type parameter, or the inner trait is a supertrait-like relative of the outer trait. Every heuristic we have considered either fails on the `IntoIterator` case or fires on cases where descending is correct. The library author has information the compiler does not, so a declaration is better than a guess.

**`#[rustc_on_unimplemented]` instead.** The existing unstable attribute allows customizing the message for a trait, but it is applied at the trait level and cannot stop the compiler from descending into a nested obligation. It also cannot be used by third-party crates on stable. The two attributes are complementary: `do_not_recommend` controls which obligation is reported; `on_unimplemented` controls how it is phrased.

**Put the attribute on the trait instead of the impl.** A trait-level attribute such as "never report this trait as a nested failure" would be too coarse. `Iterator` is a perfectly reasonable thing to report in many contexts; it is only via the particular blanket `IntoIterator` impl that reporting it misleads.

**A more general diagnostics DSL.** We could design a full language for library authors to describe error messages. That is a much larger project. This RFC solves a concrete, common problem with a small mechanism and does not preclude a larger design later.

# Prior art

GHC offers custom type errors through the `TypeError` type family, which allows library authors to replace an unsolved constraint with a message of their choosing. That mechanism is more expressive but also changes typechecking, since the error is triggered by instance resolution. The approach here is deliberately weaker: it never affects whether a program typechecks.

Within Rust, `#[rustc_on_unimplemented]` is the closest analogue and has proven valuable inside the standard library, which is evidence that author-supplied hints improve diagnostics meaningfully.

# Unresolved questions

- Should the attribute live in a `diagnostic::` namespace (for example `#[diagnostic::do_not_recommend]`) alongside future diagnostic attributes, to signal that it carries no semantic weight?
- Should rustc warn when the attribute is placed on an impl that is not a blanket impl, where it is unlikely to have any effect?
- What should happen when a marked impl is one of several candidates rather than the unique one? The proposed rule only matters in the unique-candidate case, but the exact wording should be confirmed during implementation.

# Future possibilities

Once a namespace for diagnostic-only attributes exists, it could host further tools for library authors: attributes to suggest specific alternative traits, to attach notes to particular impls, or to customize labels at call sites. Each of these would share the property that ignoring them is always a valid implementation.

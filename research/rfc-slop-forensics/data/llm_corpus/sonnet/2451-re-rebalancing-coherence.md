# RFC 2451: re_rebalancing_coherence

- Feature Name: `re_rebalancing_coherence`
- Start Date: 2018-06-30
- RFC PR: rust-lang/rfcs#2451
- Rust Issue: rust-lang/rust#55437

## Summary

This RFC seeks to clarify some ambiguity from RFC #1023, and expands it to allow type parameters to appear in the type for which the trait is being implemented, regardless of whether a local type appears before them. More concretely, it allows `impl<T> ForeignTrait<LocalType> for ForeignType<T>` to be written.

## Motivation

Rust's coherence rules exist to guarantee that for any trait and type there is at most one applicable impl, and that adding code in one crate cannot break an unrelated crate. These are the *overlap* rule and the *orphan* rule. The orphan rule says that an impl is permitted only if the trait or at least one of the types involved is local to the current crate, subject to some further conditions on type parameters.

RFC #1023, "rebalancing coherence", relaxed the original rules. Before it, an impl like `impl<T> Foo<T> for Bar` where `Foo` and `T` are foreign was subject to ad hoc restrictions. RFC #1023 replaced them with the following statement: given `impl<P1..=Pn> Trait<T1..=Tn> for T0`, the impl is allowed if either the trait is local, or at least one of the types `T0..=Tn` is a local type, and no uncovered type parameters appear in `T0..Ti` where `Ti` is the first local type.

A type parameter is "covered" when it appears as an argument inside some other type, such as the `T` in `Vec<T>`. It is "uncovered" when it appears bare, as `T`.

The phrase "no uncovered type parameters appear before the first local type" is where two problems arise.

First, the RFC text was ambiguous about whether `ForeignType<T>` counts as covering `T`. In practice the compiler treated `T` in `ForeignType<T>` as covered, but not all readers agreed that this was the intention, and the text said that type parameters could "appear" in `T0` only if a local type came first. This RFC makes the interpretation explicit.

Second, and more importantly, the restriction is stronger than it needs to be. Consider:

```rust
// in crate `app`
struct Local;

impl<T> From<Local> for Vec<T> { /* ... */ }
```

Here the trait `From` is foreign, the type `Vec<T>` is foreign, and `Local` is local, appearing as a trait argument. The type parameter `T` appears in `T0 = Vec<T>`, which comes before the first local type `Local` (as `T1`). Under the strict reading of RFC #1023, this is rejected, because a type parameter appears before the local type. In practice the compiler accepted a `T` in a covered position in some cases and rejected it in others, producing a rule that was hard to predict.

There is no soundness reason to reject this impl. The purpose of the "no uncovered parameters" condition is to prevent an upstream crate from adding a blanket impl that overlaps with the downstream impl. But `impl<T> From<Local> for Vec<T>` can only overlap with an impl of the form `impl From<Local> for Vec<X>` or a blanket one `impl<U> From<U> for V`. Any such impl in the upstream crate would have to name `Local`, which upstream cannot do, or be a blanket impl over the trait's argument, which would already be a breaking change for any implementors in downstream crates.

In practice, users hit this limitation when writing conversions and operator impls between their own types and standard library containers:

```rust
impl<T> PartialEq<Local> for Option<T> { /* ... */ }
impl<T> Add<Local> for Wrapper<T> where Wrapper is foreign { /* ... */ }
```

Today, they must work around the limitation through newtypes or by flipping the roles of the types, which is often impossible.

## Guide-level explanation

You may implement a foreign trait for a foreign type if a local type appears among the trait's type arguments, even when the foreign type has type parameters.

```rust
// crate `app`
use std::fmt::Debug;
use other::{Convert, Container};  // foreign trait and foreign type

struct Meters(f64);

impl<T> Convert<Meters> for Container<T> {
    fn convert(self) -> Meters { Meters(0.0) }
}
```

This is allowed because `Meters` is local. The parameter `T` is covered by `Container`, and since no uncovered type parameter appears before `Meters`, the impl is accepted.

The impl below remains rejected:

```rust
impl<T> Convert<Meters> for T { /* ... */ }  // error
```

Here the type parameter `T` is the Self type, uncovered, and it comes before the first local type. This would permit the upstream crate to add its own `impl<T> Convert<X> for T` later, which could overlap, so it is still forbidden.

Also still rejected is `impl<T> Convert<T> for Local`? No: this one is accepted, since `Local` is the Self type and appears first, and uncovered `T` follows it. This was already allowed by RFC #1023.

## Reference-level explanation

### The orphan rule

Given an impl `impl<P1..=Pn> Trait<T1..=Tn> for T0`, the impl is permitted if at least one of the following holds:

* `Trait` is a local trait.
* At least one of the types `T0..=Tn` is a local type. Let `Ti` be the first such type, and let `F` be the set of types `T0..Ti` that precede it. Then no type parameter `Pj` may appear *uncovered* in any type in `F`, other than `Ti` itself.

A type parameter is said to be *covered* if it appears as a type argument to some type constructor. It is *uncovered* if it appears as the type itself, or only behind a type constructor that is *fundamental*: `&`, `&mut`, `Box`, and `Pin`.

This is the rule in RFC #1023, with the following clarification and one change.

**Clarification.** For the purposes of the rule, a type is local if it is defined in the current crate, or if it is a fundamental type constructor applied to a local type, for example `&Local` or `Box<Local>`. A type such as `Vec<Local>` is not local. Type parameters appearing inside a non-fundamental foreign type are covered.

**Change.** The condition that no uncovered parameter appear before the first local type is replaced by the condition above, where covered parameters are permitted anywhere. The relevant difference from the previous behaviour is that a covered parameter in `T0..Ti-1` no longer disqualifies the impl.

In effect: `impl<T> ForeignTrait<LocalType> for ForeignType<T>` is accepted, because `T` is covered by `ForeignType` and `LocalType` is local.

### Overlap

The overlap checker is unchanged. Two impls overlap if there is some instantiation of their type parameters that makes both applicable. The new orphan rule permits more impls but does not weaken overlap detection among them.

### Negative reasoning

The existing guarantee for negative reasoning still applies. A crate may assume that a foreign type does not implement a foreign trait for a local type argument unless the foreign crate could add such an impl without it being a breaking change. Since the upstream crate cannot name the downstream local type, it cannot add an impl that mentions it; the only possible overlapping impls would be blanket impls, which are already treated as breaking changes under Rust's API evolution rules (RFC 1105).

### Examples

Accepted:

```rust
impl<T> ForeignTrait<Local> for ForeignType<T> {}
impl<T> ForeignTrait<Local, T> for ForeignType<T> {}   // T covered in Self, later in args
impl<T> ForeignTrait<T, Local> for Local2<T> {}        // Local2 is local, first
impl<T> ForeignTrait<Local> for &ForeignType<T> {}     // & fundamental, T still covered
```

Rejected:

```rust
impl<T> ForeignTrait<Local> for T {}                   // T uncovered, before Local
impl<T> ForeignTrait<T, Local> for ForeignType {}      // T uncovered in T1, before Local
impl<T> ForeignTrait<Local> for &T {}                  // & is fundamental: T uncovered
```

## Drawbacks

The rule is subtle, and adding to the list of cases that are accepted makes the document of record longer. Users who learned "type parameters must come after the local type" may now need to learn the nuance about covering.

The relaxation also commits the ecosystem to more behaviours that library authors must avoid breaking. Specifically, a library that adds a blanket impl for a foreign trait on a type with a type parameter, such as `impl<T, U> Convert<U> for Container<T>`, will now break downstream crates that have used the new allowance. Previously, such a downstream impl was impossible, so the addition was safe from that perspective. This is accepted since blanket impls are already regarded as major changes in the API evolution guidelines.

## Rationale and alternatives

**Leave the rule as is.** The cost is that users continue to need newtype wrappers, which are tedious and sometimes impossible when a foreign trait is parameterized by a local type.

**Remove the ordering requirement entirely.** One could permit uncovered parameters anywhere provided some local type appears. This is unsound with respect to the overlap guarantee, as the `impl<T> ForeignTrait<Local> for T` example shows, because the upstream crate could add a blanket impl for all `T` and a single generic parameter.

**Weaken only the case of fundamental types.** This is narrower but leaves the arbitrary distinction between `Vec<T>` and `T` unaddressed.

## Prior art

Haskell's orphan instance rules are looser and permit instances in any module, at the cost of warnings and potential incoherence. Scala's implicit resolution handles ambiguity with priority rules rather than a global uniqueness check. Rust's coherence approach is deliberately stricter, and this RFC remains within it.

## Unresolved questions

* How should the error message for rejected cases explain covering? An example-driven diagnostic is preferred.
* Should a future lint warn crate authors who add blanket impls for foreign-parameterized types?
* Are there interactions with specialization and `default impl` that require a separate analysis?

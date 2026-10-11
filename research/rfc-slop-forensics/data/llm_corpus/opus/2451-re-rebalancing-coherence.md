- Feature Name: `re_rebalancing_coherence`
- Start Date: 2018-05-30
- RFC PR: [rust-lang/rfcs#2451](https://github.com/rust-lang/rfcs/pull/2451)
- Rust Issue: [rust-lang/rust#55437](https://github.com/rust-lang/rust/issues/55437)

# Summary

This RFC clarifies an ambiguity in RFC 1023 ("Rebalancing coherence") and extends the orphan rules so that type parameters may appear in the self type of an impl, as long as a local type appears somewhere in the trait's type parameters before any uncovered type parameter. Concretely, it allows impls of this form:

```rust
impl<T> ForeignTrait<LocalType> for ForeignType<T> { }
```

# Motivation

The orphan rules decide which crate may implement a given trait for a given type. Their job is to make sure two crates can never both write impls that overlap, since that would make the program ambiguous once both crates are linked together.

RFC 1023 stated the rule as follows. Given `impl<P1..=Pn> Trait<T1..=Tn> for T0`, the impl is allowed if `Trait` is local, or if:

- at least one of `T0..=Tn` is a local type. Let `Ti` be the first such type.
- no uncovered type parameter `P1..=Pn` appears in `T0..Ti` (excluding `Ti`).

A type parameter is "uncovered" if it appears bare, not as an argument to some other type. In `Vec<T>`, `T` is covered; in `T` alone, it is uncovered.

The rule as written allows `impl<T> ForeignTrait<LocalType> for ForeignType<T>`: `T` is covered by `ForeignType`, so it is not an uncovered parameter appearing before `LocalType`. However, the implementation in `rustc` was stricter. It required that no type parameter appear at all in `T0..Ti`, covered or not. The text of RFC 1023 was ambiguous enough that both readings were defensible, and the compiler picked the conservative one.

This matters in practice. A common case is implementing a standard conversion trait involving a local type and a generic foreign container:

```rust
struct MyString(String);

impl<T> From<MyString> for Vec<T> where T: From<char> {
    fn from(s: MyString) -> Vec<T> {
        s.0.chars().map(T::from).collect()
    }
}
```

Today this is rejected even though no other crate could write an overlapping impl. The user's only option is to introduce a newtype around `Vec<T>`, which pushes awkwardness onto every caller.

Similar examples come up with `PartialEq`, `Add`, and other operator traits:

```rust
impl<T> PartialEq<Meters> for Box<T> where T: AsRef<f64> { /* ... */ }
impl<T> Add<Duration> for Wrapper<T> { /* ... */ }
```

These are sound and useful, and people run into the restriction often enough that it shows up repeatedly in issue trackers and forums.

# Guide-level explanation

You can implement a foreign trait for a foreign type as long as one of the trait's type parameters, or the self type, is a local type, and no *bare* type parameter shows up before it.

The order is: the self type first, then the trait's type parameters left to right. The first local type in that order is the anchor. Before the anchor, type parameters are allowed only if they are wrapped inside some other type.

Allowed:

```rust
impl<T> ForeignTrait<LocalType> for ForeignType<T> {}   // T is covered
impl<T> ForeignTrait<LocalType, T> for ForeignType {}   // T comes after the anchor
impl ForeignTrait<LocalType> for ForeignType {}         // no params at all
impl<T> ForeignTrait for LocalType<T> {}                // self type is local
```

Not allowed:

```rust
impl<T> ForeignTrait<LocalType> for T {}                // bare T before the anchor
impl<T> ForeignTrait<T, LocalType> for ForeignType {}   // bare T before the anchor
```

The reason for the second group is that another crate, perhaps the one that defines `ForeignTrait`, could write `impl<U> ForeignTrait<U> for SomeType` and those impls could overlap with yours for some choice of `T`.

# Reference-level explanation

## The orphan rule

Given `impl<P1..=Pn> Trait<T1..=Tn> for T0`, the impl is valid only if at least one of the following holds:

- `Trait` is a local trait.
- At least one of `T0..=Tn` is a local type. Let `Ti` be the first such type. No uncovered type parameter `P1..=Pn` may appear in `T0..Ti` (excluding `Ti`).

The only change from current behavior is the second clause: covered type parameters are permitted in `T0..Ti`. Previously, any appearance of a type parameter in `T0..Ti`, covered or not, caused rejection.

## Covered and uncovered parameters

A type parameter `P` is covered by a type `T` if `T` is not `P` itself and `P` appears inside the generic arguments of `T`. For example, `P` is covered in `Vec<P>`, `HashMap<String, P>`, and `(P, u8)`. Tuples are not local to any crate and are treated as foreign types, so `P` inside a tuple counts as covered.

References are treated specially for fundamental types. `&P`, `&mut P`, `Box<P>`, and `Pin<P>` are `#[fundamental]`, meaning they do not cover their arguments. `impl<T> ForeignTrait<LocalType> for Box<T>` is therefore still rejected, since `Box<T>` is treated as if it were `T` for coherence purposes. This preserves the guarantees fundamental types already have.

## Why this is sound

The orphan rules must ensure that for any two crates that can be compiled independently, no pair of their impls overlaps. Consider the crate `A` that defines `ForeignTrait`, crate `B` that defines `ForeignType`, and our crate `C` with `LocalType`.

For an impl in another crate to overlap with `impl<T> ForeignTrait<LocalType> for ForeignType<T>` in `C`, it must apply when the first trait parameter is `LocalType`. Crates `A` and `B` do not know about `LocalType`, so the only way they could match it is with an uncovered type parameter in that position, such as `impl<U, V> ForeignTrait<U> for V`. But such a blanket impl is exactly what RFC 1023's rules already account for: adding it to `A` is a breaking change, and `B` is not allowed to write it at all because neither the trait nor any anchor type is local to `B`.

A sibling crate `D` with its own local type cannot overlap either, because its anchor type differs from `LocalType`.

## Compatibility

This change only accepts more programs. No previously valid program becomes invalid. Previously valid programs keep the same meaning.

However, it does change what counts as a breaking change for crate authors. Adding a blanket impl like `impl<T, U> ForeignTrait<U> for ForeignType<T>` in the crate that owns `ForeignType` was previously a minor change in some cases; under these rules it can conflict with downstream impls and should be considered breaking. The Rust API evolution guidelines (RFC 1105) will be updated accordingly.

# Drawbacks

- The coherence rules become a bit more complicated to explain. The "no type parameters before the anchor" rule is simpler to state than "no *uncovered* type parameters before the anchor."
- Upstream crates lose a small amount of freedom to add blanket impls without a major version bump.

# Rationale and alternatives

**Leave the rules as implemented.** Users continue to need newtypes for these cases. The workaround is well known but costly in ergonomics, and the restriction does not buy any soundness.

**Go further and allow uncovered parameters after a local type in the self position.** This RFC already allows parameters after the anchor. Allowing uncovered parameters before it is unsound for the reasons above.

**Introduce explicit negative reasoning or "crate-local" markers.** These would be more expressive but are much larger designs; this RFC is a small fix that can stand on its own.

# Prior art

Haskell's orphan instance rules are looser but produce warnings rather than guarantees. Rust's coherence model is stricter by design, and this RFC stays within that model.

# Unresolved questions

- Exact diagnostic wording when an impl is rejected, so that it points at the specific uncovered parameter.

# Future possibilities

Further work on coherence, such as a formal model in Chalk, could verify these rules mechanically and suggest additional sound relaxations.

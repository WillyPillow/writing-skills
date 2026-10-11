# Rust RFC 2089: `implied_bounds`

- Feature Name: `implied_bounds`
- Start Date: 2024-02-14
- Status: Proposed

## Summary

This RFC removes the need to write redundant bounds on functions and impls when those bounds can be inferred from the types in the signature and from other bounds already present. Consider a type `Foo<T>` whose declaration requires `T: Clone`. Under this RFC, writing `impl<T> Foo<T> { ... }` is sufficient, because the bound on `T` is implied by the well-formedness of `Foo<T>`. The compiler currently supports implied bounds for lifetime outlives relations, for supertraits, and for projections. This RFC extends the mechanism to all where clauses that appear on traits and types.

## Motivation

Rust requires a programmer to state every bound that a generic item relies on. This is a deliberate choice that keeps signatures explicit, but in practice it produces a lot of repetition. A struct declared with a bound must be mentioned with that same bound in every impl block, and every function that accepts the struct must repeat the bound in its own where clause. The repetition is a source of noise and a source of errors, because a bound that is written in one place and forgotten in another leads to a confusing compiler error.

The compiler already performs some inference of this kind. When a signature mentions `&'a T`, the compiler knows that `T: 'a` holds, so the programmer does not need to write it. When a trait has a supertrait, the programmer does not need to repeat the supertrait bound on every use. Extending the same reasoning to general where clauses would bring the language into line with what programmers already expect.

## Guide-level explanation

Suppose a type is declared as follows:

```rust
struct Foo<T: Clone> {
    value: T,
}
```

Today an impl block for this type must repeat the bound:

```rust
impl<T: Clone> Foo<T> {
    fn duplicate(&self) -> (T, T) {
        (self.value.clone(), self.value.clone())
    }
}
```

With this RFC, the bound is implied by the declaration of `Foo`, so the impl may be written without it:

```rust
impl<T> Foo<T> {
    fn duplicate(&self) -> (T, T) {
        (self.value.clone(), self.value.clone())
    }
}
```

The body still type checks, because the bound `T: Clone` is available inside the impl by virtue of being implied by the type `Foo<T>`. The programmer does not have to restate it. Readers can find the implied bounds by looking at the declarations of the types that appear in the signature.

The rule applies only to bounds that are well-formedness requirements of the types mentioned. It does not add bounds that the programmer did not intend. A function that takes `Foo<T>` as an argument gains the same implied bound, so it can call methods that require `T: Clone` without repeating the bound.

## Reference-level explanation

The compiler already computes a set of implied bounds for each signature by walking the types that appear in it and collecting the where clauses of their declarations. Under this RFC, the walk is extended to include all where clauses of the declarations of traits and types, not only the lifetime and supertrait bounds handled today.

For each type constructor that appears in a signature, the compiler adds the instantiated where clauses of its declaration to the environment in which the signature is checked. These clauses are treated as assumptions for the body of the item and as obligations that the caller must satisfy at the use site. The caller obligation is discharged automatically when the type is well formed, because well-formedness of the type already requires the bound.

Projections are handled in the same way as before. A projection whose trait has a where clause contributes that clause to the implied set. Cycles in the implied set are detected and rejected, so that the mechanism cannot be used to prove a bound from itself.

The change interacts with the coherence checker and the orphan rules only through the set of assumptions available during checking. It does not alter which impls exist, and it does not change method resolution, except that some methods become callable where previously they required an explicit bound.

## Drawbacks

Implied bounds make signatures less self-contained. A reader who looks only at a function's where clause may not see every requirement that applies, and must consult the declarations of the types involved. Tooling such as documentation generators must be updated to show implied bounds, or the rendered signatures will appear to be missing constraints. There is also a risk of subtle changes in inference when a bound that was previously assumed is now implied, because some programs may depend on the exact set of bounds in scope.

## Rationale and alternatives

The main alternative is to keep the current rule and accept the repetition. This is a defensible choice, and the RFC does not claim that repetition is always wrong. However, the cases where the bound is obvious from the type are the ones where repetition adds the least information, and removing it reduces the chance of inconsistent bounds.

A second alternative is to introduce a new syntax, such as a keyword that asks the compiler to copy the bounds of a type into a signature. This makes the implied set explicit, but it adds syntax for a convenience that the compiler can handle automatically. The RFC prefers to keep the language small.

A third alternative is to restrict implied bounds to where clauses on types and not traits. This would be simpler to specify, but it would leave a common case unaddressed, and the asymmetry would be difficult to explain to users.

## Prior art

Several languages with generic programming support infer constraints from type declarations in a similar way. The experience of those languages suggests that the mechanism is useful but that diagnostics must explain where an inferred bound came from, so that users can find it when something goes wrong.

## Unresolved questions

- How should the compiler report the origin of an implied bound in an error message?
- Should a lint be provided that suggests removing a redundant explicit bound that is already implied?
- How will rustdoc present implied bounds in rendered documentation?

## Future possibilities

If implied bounds are adopted for all where clauses, a later change could allow a type author to mark a bound as not implied, for cases where the bound is an implementation detail that should not leak into signatures. The mechanism proposed here would remain the default, and the marker would be an opt-out for specific cases.

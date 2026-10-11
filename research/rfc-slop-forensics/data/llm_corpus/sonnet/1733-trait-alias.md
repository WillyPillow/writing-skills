# RFC 1733: Trait alias

- Feature Name: `trait_alias`
- Start Date: 2016-08-31
- RFC PR: rust-lang/rfcs#1733
- Rust Issue: rust-lang/rust#41517

## Summary

Traits can be aliased with the `trait TraitAlias = …;` construct. Currently, the right hand side is a bound: a single trait, or a combination with `+` of traits and lifetimes. Type parameters and lifetimes can be added to the *trait alias* if needed.

## Motivation

### First motivation: `impl`

Sometimes, some traits are defined with parameters. For instance:

```rust
pub trait Foo<T> {
    // ...
}
```

It is not uncommon to make an alias in `impl` blocks. In that case, the `impl` block is generic in `T`, but a more specialized alias is wanted:

```rust
impl<T> Foo<T> for Bar { /* ... */ }
```

Today the only way to give a name to a recurring combination of bounds is to define a new trait and add a blanket implementation. This is a well-known trick:

```rust
trait Service: Send + Sync + 'static {}
impl<T: Send + Sync + 'static> Service for T {}
```

The trick works but it has drawbacks. It creates a distinct trait, so the alias and the original bounds are different things in the type system. Items in the alias must be separately implemented, and the blanket impl occupies the "one implementation" slot, so users cannot add their own specializations. Documentation also has to explain that the trait exists only as shorthand.

### Second motivation: bound repetition

Real-world code frequently repeats the same set of bounds. A function working with numeric generics might carry the following on every signature:

```rust
fn dot<T: Copy + Add<Output = T> + Mul<Output = T> + Default>(a: &[T], b: &[T]) -> T { /* ... */ }
fn norm<T: Copy + Add<Output = T> + Mul<Output = T> + Default>(a: &[T]) -> T { /* ... */ }
fn scale<T: Copy + Add<Output = T> + Mul<Output = T> + Default>(a: &mut [T], k: T) { /* ... */ }
```

The repetition is noisy, error-prone, and makes changes laborious. If the group needs to include another bound, each site must be edited. Authors want a name for the collection.

### Third motivation: semantic naming

A trait alias lets library authors capture intent. `Serializable` might stand for `Serialize + DeserializeOwned + Send`. `AsyncTask` might stand for `Future<Output = ()> + Send + 'static`. A reader seeing the name knows what role the type plays without scanning the bounds.

### Fourth motivation: trait objects

Trait objects in Rust can have at most one non-auto trait. A common request is to write `Box<dyn Read + Write>`, which is not allowed. The blanket trait trick makes this possible but causes upcasting problems. A trait alias would not solve the multi-trait object problem by itself, but it would make a related pattern clearer, namely aliasing a single trait with auto traits and lifetimes, e.g. `trait Handler = Fn(Request) -> Response + Send + Sync;`.

## Detailed design

### Syntax

```rust
trait TraitAlias = Foo + Bar + 'static;
```

The grammar adds a new item form:

```
trait_alias := 'trait' IDENT generics? '=' bounds where_clause? ';'
```

The alias may be public with `pub`. It may have type parameters and lifetime parameters, and may have a `where` clause:

```rust
pub trait Sendable<T> = Into<T> + Send where T: Clone;
trait Callback<'a, A> = Fn(&'a A) + 'a;
```

### Semantics

A trait alias is a name for a set of bounds. Wherever a bound `T: Alias<...>` is written, it is exactly equivalent to writing the right-hand side with type and lifetime arguments substituted. The alias introduces no new trait, no new type-level entity that can be implemented, and no new vtable.

The consequences:

- `T: Alias` is satisfied if and only if all the aliased bounds are satisfied.
- Where a bound `T: Alias` is assumed in a function body, all the aliased bounds may be assumed, including those on supertraits and associated types.
- An alias cannot be implemented. `impl Alias for T` is an error. Authors implement the underlying traits individually.
- Aliases can refer to other aliases, but cycles are an error.

### Where aliases may be used

Aliases may appear in any bound position:

- Type parameter bounds: `fn f<T: Alias>(x: T)`.
- `where` clauses: `where T: Alias`.
- `impl Trait` in argument and return position: `fn f() -> impl Alias`.
- Trait object types: `Box<dyn Alias>`, subject to the constraint that the expansion has at most one non-auto trait. If the expansion contains more than one non-auto trait, the use of `dyn Alias` is an error, with a diagnostic pointing at the expansion.
- Supertrait positions: `trait Foo: Alias { }`.

They may not appear in `impl Alias for ...` position, nor in paths in expression position like `Alias::method`. Method calls on a value through an alias resolve through the underlying traits.

### Associated items

Aliases cannot define associated items. However, associated types of the aliased traits may be named through the alias if exactly one underlying trait defines that name, or constrained in the alias itself:

```rust
trait IntIter = Iterator<Item = i32>;

fn total<I: IntIter>(it: I) -> i32 { it.sum() }
```

When using the alias in a bound with equality constraints, e.g. `T: IntIter<Item = i32>`, the constraint must be consistent with the alias. An alias with fixed associated types can't be re-bound to something else.

### Name resolution and visibility

Trait aliases are items living in the type namespace alongside traits. A trait alias and a trait cannot share a name in the same module. Visibility is controlled with `pub` in the same way as for traits. An alias may mention private traits only if they are no less visible than the alias, following the existing private-in-public rules.

### Documentation

`rustdoc` shows trait aliases in their own section, with the expanded bounds. Links from the traits to the aliases that mention them are not required.

### Interaction with `?Sized`

A relaxed bound like `?Sized` may appear in an alias, and it applies where the alias is used. An alias used on a parameter that has an implicit `Sized` bound removes that bound if the alias contains `?Sized`. This behaviour is as if the bound were written out in full.

## How We Teach This

We can teach trait aliases as "type aliases for bounds". The existing `type Name = ...;` item gives a short name to a type; the new `trait Name = ...;` gives a short name to a bound. The Book should present it in the chapter on traits, after introducing multiple bounds and `where` clauses, as a tool to reduce repetition.

An example from the standard library domain: a project working with I/O may define

```rust
trait Stream = Read + Write + Send;
```

and use it throughout its signatures. When a requirement changes, only one line needs editing.

The guide should call out the main differences from the blanket-trait trick: an alias is not implementable, is transparent to the type system, and is not usable for method definitions.

## Drawbacks

- **Another item kind to learn.** Rust already has a lot of syntax. The distinction between traits and aliases adds to it.
- **Opaque error messages.** If an alias expands to many bounds and one is unsatisfied, the diagnostic must show which underlying bound failed, not just the alias name.
- **Possible confusion with the blanket trait trick.** Users who see aliases and traits that look similar might not know which to use. Guidance should say: use alias unless you need to add methods or distinct implementations.
- **Implementation effort.** The compiler must expand aliases everywhere bounds are processed, including inference of implied bounds, `dyn` handling and rustdoc.
- **Limits.** The alias cannot be implemented, which some will find restrictive. Users will ask why they cannot write an `impl` for the alias, and the answer is that it is merely a name.

## Alternatives

### Do nothing

The blanket trait trick remains available. It is clumsy but workable, and does not require compiler changes.

### Use macros

Macros could expand to bounds, but they cannot appear in bound position on stable Rust and would hinder error messages and tooling.

### Allow implementations of aliases

One could define `impl Alias for T` as a shorthand for implementing every aliased trait. This requires a syntax for supplying all methods and conflicts with the idea of an alias as pure naming. It could be explored in a future extension.

### Make the alias a real trait automatically

Automatically generating the blanket impl would give a first-class trait. But it would be a different semantics, leaving the alias unable to expand in `dyn` contexts and creating the same coherence issues as the manual approach.

## Unresolved questions

- Should alias definitions be allowed to carry `where` clauses on `Self`, and if so how do they interact with implied bounds?
- Should `dyn Alias` with several non-auto traits be allowed in a future extension in which multi-trait objects are supported?
- What should the syntax be for aliasing with associated type defaults?
- Should the alias be allowed in `impl Trait for T` header as a bound, e.g. `impl<T: Alias> Foo for T`? The proposal says yes since it is a bound position.
- How should lints such as `unused` and `missing_docs` treat aliases?

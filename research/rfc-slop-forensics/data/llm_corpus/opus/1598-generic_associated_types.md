- Feature Name: `generic_associated_types`
- Start Date: 2016-04-29
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

Allow associated types in traits to have their own generic parameters, making them type constructors rather than plain types. For example:

```rust
trait StreamingIterator {
    type Item<'a>;
    fn next<'a>(&'a mut self) -> Option<Self::Item<'a>>;
}
```

This is a step toward what is usually called higher-kinded types, which Rust users often request. It covers one of the most common uses of higher-kinded polymorphism, it is a fairly small extension to the type system, and it is forward compatible with more general forms of higher-kinded types should they ever be added.

# Motivation

## Streaming iterators

The standard `Iterator` trait has an associated type `Item` that cannot depend on the borrow of the iterator in `next`:

```rust
trait Iterator {
    type Item;
    fn next(&mut self) -> Option<Self::Item>;
}
```

This means an iterator cannot return a reference into itself. A common example is an iterator that reads lines into an internal buffer and yields `&str` slices of that buffer. Each item is only valid until the next call to `next`, which overwrites the buffer. There is no way to express that with `Iterator`, because `Item` is a single type fixed for the whole iterator, with no connection to the `&mut self` borrow.

What we want is for the item type to take the lifetime of the borrow:

```rust
trait StreamingIterator {
    type Item<'a> where Self: 'a;
    fn next<'a>(&'a mut self) -> Option<Self::Item<'a>>;
}

impl StreamingIterator for LineReader {
    type Item<'a> = &'a str;
    fn next<'a>(&'a mut self) -> Option<&'a str> { ... }
}
```

Today this cannot be written. Workarounds exist, but they involve unsafe code or extra helper traits with higher-ranked bounds that are hard to read and harder to use.

## Collection families

Generic code over collections often wants to say "a collection of the same kind as this one, but holding a different element type." For example, a `map` method on a generic container trait should return the same container with a new element type:

```rust
trait Container {
    type Elem;
    type Mapped<U>: Container<Elem = U>;
    fn map<U>(self, f: impl FnMut(Self::Elem) -> U) -> Self::Mapped<U>;
}

impl<T> Container for Vec<T> {
    type Elem = T;
    type Mapped<U> = Vec<U>;
    ...
}
```

With generic associated types (GATs), `Mapped<U>` is a type constructor provided by each implementation.

## Pointer families

Library code that wants to be generic over `Rc` versus `Arc` has a similar need: a trait that provides a type `Pointer<T>` for any `T`:

```rust
trait PointerFamily {
    type Pointer<T>: Deref<Target = T>;
    fn new<T>(value: T) -> Self::Pointer<T>;
}
```

A persistent data structure library could then be written once and instantiated for single-threaded or multi-threaded use.

## Why not full higher-kinded types

Full higher-kinded types would let a type parameter itself be a type constructor: `fn foo<F<_>>(x: F<u8>)`. That raises hard design questions in Rust: how to handle partial application, how inference should work, what syntax to use, and how it interacts with lifetimes and traits. GATs avoid most of those questions. The type constructors they introduce are always projections from a trait, so they are always named through a concrete implementation, and inference does not need to guess a type constructor from its applications.

# Guide-level explanation

An associated type may declare generic parameters, both lifetimes and types, and where clauses:

```rust
trait Lender {
    type Loan<'a> where Self: 'a;
    fn lend<'a>(&'a mut self) -> Self::Loan<'a>;
}
```

An implementation must provide the associated type with the same parameters:

```rust
impl<T> Lender for Vec<T> {
    type Loan<'a> = &'a mut [T] where T: 'a;
    fn lend<'a>(&'a mut self) -> &'a mut [T] { self }
}
```

Uses of the associated type supply arguments: `Self::Loan<'a>`, `<V as Lender>::Loan<'x>`, `T::Mapped<String>`.

Bounds on the associated type can refer to its parameters:

```rust
trait Container {
    type Elem;
    type Iter<'a>: Iterator<Item = &'a Self::Elem> where Self: 'a;
    fn iter<'a>(&'a self) -> Self::Iter<'a>;
}
```

When writing generic code over a trait with a GAT, bounds can constrain the associated type for all arguments using higher-ranked syntax:

```rust
fn print_all<C>(c: &C)
where
    C: Container,
    for<'a> C::Iter<'a>: ExactSizeIterator,
{ ... }
```

# Reference-level explanation

## Syntax

An associated type declaration in a trait accepts a generics list and a where clause:

```
AssocType := 'type' IDENT Generics? (':' Bounds)? WhereClause? ';'
```

The same applies in `impl` blocks, with `= Type` before the where clause.

## Well-formedness

An implementation's associated type must have the same number and kinds of generic parameters as the trait's declaration. Its where clauses may be no stricter than the trait's.

For the type `<T as Trait>::Assoc<P1, ..., Pn>` to be well formed, `T: Trait` must hold, and the where clauses on `Assoc` must hold when instantiated with `P1, ..., Pn`.

## Projection and normalization

Today, a projection `<T as Trait>::Assoc` is normalized by finding the impl of `Trait` for `T` and substituting. With GATs, the projection carries additional arguments, and normalization substitutes both the impl's parameters and the associated type's own parameters. Nothing else in the normalization algorithm changes.

Internally, the compiler represents the projection as applying the associated item to a combined list of substitutions: the trait's parameters followed by the associated type's parameters. This matches how generic methods on traits are already represented, so much of the existing machinery can be reused.

## Higher-ranked bounds

A bound such as `for<'a> T::Item<'a>: Debug` is a higher-ranked bound over a projection. The compiler already supports higher-ranked trait bounds over lifetimes. This RFC permits them to quantify over the arguments to a GAT. Quantifying over types (`for<U> ...`) is not part of this RFC.

## Object safety

A trait with a generic associated type is not object safe in this RFC, since a trait object would need to specify the associated type for every possible argument. This restriction can be revisited later.

# Drawbacks

- **Complexity.** This adds a new concept that interacts with traits, lifetimes, and higher-ranked bounds, all of which are already difficult parts of the language.
- **Implementation cost.** Normalization of projections with higher-ranked arguments has known weaknesses in the current trait solver. Some useful programs may be rejected until the solver improves.
- **Required where clauses.** Patterns like `type Item<'a> where Self: 'a` are needed for soundness in common cases but are easy to forget, and the resulting errors may be confusing.

# Rationale and alternatives

**Full higher-kinded types.** More expressive but much harder to design and implement. GATs cover the most requested cases and do not prevent adding HKT later; a future `F<_>` type parameter could be modeled as a trait with a GAT.

**Family traits with higher-ranked bounds.** Many of these patterns can be encoded today with a helper trait such as `trait ItemFamily<'a> { type Item; }` and bounds like `for<'a> Self: ItemFamily<'a>`. The encoding works only for lifetimes, is verbose, and produces poor error messages.

**Lifetime-only GATs first.** We could allow only lifetime parameters initially. Streaming iterators need only lifetimes, but collection and pointer families need type parameters, and implementing both together avoids designing the feature twice.

# Unresolved questions

- Should the compiler infer `where Self: 'a` clauses on GATs, or require them to be written?
- Should GATs eventually be object safe, and with what syntax for specifying them in a trait object?
- How should defaults for generic associated types work?

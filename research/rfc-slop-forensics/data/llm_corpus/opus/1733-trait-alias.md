- Feature Name: `trait_alias`
- Start Date: 2016-08-31
- RFC PR: rust-lang/rfcs#1733
- Rust Issue: rust-lang/rust#41517

# Summary

This RFC lets traits be aliased with a `trait TraitAlias = ...;` declaration. The right-hand side is a bound: a single trait, or several traits and lifetimes joined with `+`. The alias can take its own type and lifetime parameters where needed.

```rust
trait Service = Fn(Request) -> Response + Send + Sync + 'static;
trait IntIter = Iterator<Item = i32>;
trait Store<K> = Map<K, String> + Clone;
```

# Motivation

Rust code often repeats the same bound in many places. A web framework might write `F: Fn(Request) -> Response + Send + Sync + 'static` on every function that accepts a handler. A numeric library might write `T: Add<Output = T> + Mul<Output = T> + Copy + Default` on every generic function. Repeating these is tedious, it makes signatures long, and it makes a change hard: tightening one bound means editing every copy.

Types have `type` aliases for this. Traits have no direct equivalent. The usual workaround is a new trait with a blanket impl:

```rust
trait Service: Fn(Request) -> Response + Send + Sync + 'static {}
impl<T> Service for T where T: Fn(Request) -> Response + Send + Sync + 'static {}
```

This mostly works, but it falls short:

- **Boilerplate.** Every alias needs two items, with the bound written twice.
- **It is a new trait.** `Service` is a separate trait, not a name for the bound. A function that takes `T: Service` can't be called with a value known only to satisfy the expanded bound unless the blanket impl applies, which can fail in generic contexts where the solver can't prove the full where-clause.
- **Associated-type bounds don't carry over.** If the "alias" is `trait IntIter: Iterator<Item = i32> {}`, then in `fn f<I: IntIter>(i: I)`, the compiler doesn't know that `I::Item == i32` when it uses the bound. That makes the workaround useless for one of the most common needs.
- **No trait objects for multi-trait bounds.** `dyn Service` works only because `Service` is one trait. The trait-object rules still forbid `dyn Read + Write` because both are non-auto traits. An alias doesn't lift that restriction, but where it is legal an alias should be usable in `dyn`.

A true alias, expanded wherever it is used, avoids all of this.

# Guide-level explanation

## Declaring an alias

```rust
trait Name = Bound1 + Bound2 + 'a;
```

The right-hand side is any bound that could appear after `:` in a where-clause. Wherever `Name` appears in a bound, the compiler replaces it with the right-hand side.

```rust
trait Shareable = Clone + Send + Sync;

fn spawn_all<T: Shareable>(items: Vec<T>) { ... }
// same as
fn spawn_all<T: Clone + Send + Sync>(items: Vec<T>) { ... }
```

## Associated types

An alias can fix associated types:

```rust
trait IntIter = Iterator<Item = i32>;

fn total<I: IntIter>(iter: I) -> i32 {
    iter.sum()     // `I::Item` is known to be `i32`
}
```

## Parameters

Aliases can take type and lifetime parameters:

```rust
trait Lookup<K> = Fn(&K) -> Option<String>;
trait Borrows<'a, T> = Iterator<Item = &'a T> + 'a;

fn find<F: Lookup<u32>>(f: F) { ... }
```

## Where-clauses on the alias

An alias can carry `where` clauses that become part of the expanded bound:

```rust
trait Graph<N> = GraphBase<Node = N> where N: Eq + Hash;
```

Using `T: Graph<N>` requires `N: Eq + Hash` too.

## Trait objects

When the expansion consists of a single non-auto trait plus any number of auto traits and lifetimes, the alias can be used as a trait object type:

```rust
trait Handler = Fn(Request) -> Response + Send + Sync;

let handlers: Vec<Box<dyn Handler>> = Vec::new();
```

`dyn Handler` expands to `dyn Fn(Request) -> Response + Send + Sync`.

## What an alias is not

- **You can't implement an alias.** `impl Shareable for Foo {}` is an error. Implement the traits it names.
- **An alias defines no methods.** Methods come from the underlying traits, and calling them through a value bounded by the alias works as it would with the expanded bound.
- **An alias doesn't bring trait methods into scope.** Importing `Shareable` doesn't make `clone()` callable unless the underlying traits are in scope, though for `Clone` they always are through the prelude. Whether importing an alias should import its traits is listed as an open question.

# Reference-level explanation

## Grammar

```
TraitAlias:
    'trait' IDENT Generics? '=' TypeParamBounds WhereClause? ';'
```

A trait alias is an item. It can have visibility and attributes like any other item, and it lives in the type namespace, so it can't share a name with a trait or type in the same module.

## Expansion

During type collection, a bound `T: Alias<Args>` is replaced by the alias's right-hand side, with the alias's generic parameters substituted. The where-clauses of the alias are added as predicates. Expansion is recursive, so aliases can refer to other aliases. A cycle (`trait A = B; trait B = A;`) is an error.

## Well-formedness

An alias is well-formed if its right-hand side is a well-formed bound given the alias's own where-clauses. Generic parameters that don't appear on the right-hand side are allowed but produce an unused-parameter lint.

## Trait objects

`dyn Alias` is permitted if, after expansion, the bound has at most one non-auto trait, any number of auto traits, and at most one lifetime. The usual object-safety rules apply to the non-auto trait.

## `Self` in an alias

`Self` on the right-hand side refers to the type being bounded. For example, `trait Eq2 = PartialEq<Self> + Eq;` is allowed.

# Drawbacks

- **Another kind of item.** Aliases share a namespace with traits but behave differently. You can't implement them, and they don't always work as trait objects. Error messages need to explain this clearly.
- **Readability.** An alias hides what a bound requires. Readers have to look up the alias to know which traits a generic function needs. The same is true of type aliases and generally accepted.
- **Overlap with the blanket-impl pattern.** Some code will keep using that pattern, so the ecosystem will have two ways to do similar things.

# Rationale and alternatives

## Keep the blanket-impl pattern

It doesn't carry associated-type equality and needs boilerplate. Fixing its shortcomings would mean special-case solver rules for "marker" traits, which is more complicated than adding a real alias.

## Use `type` for trait aliases

`type Service = Fn(...) + Send;` was considered. It would confuse types with bounds, and `type` already gives a meaning to the bare form (the deprecated bare trait object type). A `trait` keyword makes it clear the item names a bound.

## Allow implementing aliases

Letting `impl Alias for T` implement each component trait was considered but turns out awkward: which methods belong to which trait, and what does an alias with associated-type constraints mean in an impl? This could be revisited.

# Prior art

- **C++20 concepts** let a named concept combine other concepts and requirements, and generic code is constrained by the name.
- **Haskell** supports constraint synonyms with the `ConstraintKinds` extension: `type Shareable a = (Eq a, Show a)`.
- **Swift** can compose protocols as `typealias Codable = Encodable & Decodable`, which is essentially this feature.

# Unresolved questions

- Should importing an alias also import its component traits for method resolution?
- Should `impl Alias for T` eventually be allowed for single-trait aliases?
- How should rustdoc show aliases, expanded or by name?

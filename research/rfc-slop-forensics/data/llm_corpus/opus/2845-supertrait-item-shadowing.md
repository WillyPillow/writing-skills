- Feature Name: `supertrait_item_shadowing`
- Start Date: 2020-01-14
- RFC PR: rust-lang/rfcs#2845
- Rust Issue: rust-lang/rust#89151

# Summary

This RFC changes how items are resolved for generics and trait objects. When a subtrait defines an item with a given name, a bound on the subtrait no longer brings into scope any supertrait items of the same name. The subtrait's item shadows them.

# Motivation

Consider a library that defines a trait:

```rust
// crate `base`
pub trait Shape {
    fn area(&self) -> f64;
}
```

A second crate extends it:

```rust
// crate `ext`
pub trait FancyShape: base::Shape {
    fn describe(&self) -> String;
}

fn print<T: FancyShape>(s: &T) {
    println!("{}", s.describe());
}
```

Later, `base` adds a method in a minor release:

```rust
pub trait Shape {
    fn area(&self) -> f64;
    fn describe(&self) -> String { format!("shape with area {}", self.area()) }
}
```

The new method has a default body, which the API evolution guidelines treat as a minor, non-breaking change. Yet `ext` no longer compiles:

```
error[E0034]: multiple applicable items in scope
  --> src/lib.rs
   |
   |     println!("{}", s.describe());
   |                      ^^^^^^^^ multiple `describe` found
```

The bound `T: FancyShape` brings the items of both `FancyShape` and its supertrait `Shape` into scope, and both now define `describe`. The method call is ambiguous.

This is a real hazard for ecosystem evolution. The standard library has run into it more than once: new methods on `Iterator` have collided with methods of the same name on extension traits in crates like `itertools`. For `itertools` the collisions are on concrete types and involve trait imports. The generic case is worse, because the author of `ext` did everything right. They named a method on their own trait. The breakage comes from a supertrait they don't control.

The fix is to say that a subtrait's own items take precedence over its supertraits' items when resolving through a bound on the subtrait. The author of `FancyShape` meant `describe` to be `FancyShape::describe`, and the compiler should resolve it that way.

# Guide-level explanation

When you call a method or name an associated item through a generic bound or a trait object, the compiler looks for it in the bound trait and, transitively, its supertraits. With this RFC, the lookup stops at the most specific trait that defines the name.

```rust
trait Super {
    fn hello(&self) -> &'static str { "super" }
}

trait Sub: Super {
    fn hello(&self) -> &'static str { "sub" }
}

fn call<T: Sub>(x: &T) -> &'static str {
    x.hello()   // calls Sub::hello
}

fn call_dyn(x: &dyn Sub) -> &'static str {
    x.hello()   // calls Sub::hello
}
```

To call the supertrait's item, write it out:

```rust
Super::hello(x)
<T as Super>::hello(x)
```

### Only bounds that name the subtrait

Shadowing only applies when the subtrait is in the bound. If you also bound on the supertrait directly, both items are in scope at equal priority and the call is still ambiguous:

```rust
fn both<T: Sub + Super>(x: &T) {
    x.hello();  // error: ambiguous
}
```

That is deliberate. Writing `Super` out in the bound is an explicit request for its items.

### A lint

Silently picking one item could hide a mistake in a few cases. So the compiler emits a warn-by-default lint, `supertrait_item_shadowing_usage`, when a call resolves to a shadowing item, and an allow-by-default lint, `supertrait_item_shadowing_definition`, at the definition of a shadowing item. Authors who intended the shadowing can silence the lint at the definition.

# Reference-level explanation

## Resolution through generics and trait objects

For a method call `recv.name(..)` where the receiver's type is a type parameter `T` or a trait object `dyn Trait`, the compiler collects candidate traits from the bounds on `T` (or the principal trait of the object). Today all supertraits are expanded and every matching item is a candidate.

With this RFC, candidates are filtered as follows. For each candidate item `I` defined in trait `A`, if some other candidate item with the same name and namespace is defined in a trait `B` where `B` has `A` as a (transitive) supertrait, then `I` is removed. If exactly one candidate remains, resolution succeeds. Otherwise it is ambiguous, as today.

The same rule applies to associated types and constants named through a bound, as in `T::Output` and `T::CONST`.

## Diamond hierarchies

```rust
trait A { fn f(&self); }
trait B: A { fn f(&self); }
trait C: A { fn f(&self); }
trait D: B + C {}

fn g<T: D>(x: &T) { x.f() }
```

`B::f` and `C::f` both shadow `A::f`, but neither shadows the other, so the call is ambiguous. Ambiguity remains the right answer whenever there is no single most specific item.

## Concrete types

This RFC doesn't change resolution on concrete types. There, candidates come from trait imports and inherent impls, not from a chain of bounds, so "most specific" has no clear meaning. If `Shape` and `FancyShape` are both in scope and a concrete type implements both, `shape.describe()` is still ambiguous. Changing that would need a separate design.

## Fully qualified syntax

`<T as Trait>::item` always names the item on exactly `Trait`, and is not affected.

# Drawbacks

- **It hides ambiguity.** Some calls that are an error today would compile and pick the subtrait item, even if the programmer expected the supertrait's. The warn-by-default lint reduces this risk, and in the motivating case the subtrait item is almost always what was meant.
- **Generic and concrete contexts differ.** The same method call might be resolved in a generic function and ambiguous in a concrete one. That inconsistency may surprise people, though the concrete case can be fixed by adjusting imports, which the generic case can't.
- **More rules.** Method resolution is already intricate, and this adds another step.

# Rationale and alternatives

## Do nothing

Library authors would have to treat adding any trait item as a potentially breaking change for downstream subtraits. In practice that means new methods on popular traits like `Iterator` or `Read` keep breaking code, or the standard library avoids good names to sidestep collisions.

## Supertraits shadow subtraits

The opposite rule, preferring the supertrait, would bring back exactly the breakage this RFC is meant to prevent.

## Shadow only for items added after the subtrait

Tracking when each item was added is not possible in the compiler. Version-aware resolution has been floated but would be far more involved.

## Hard error at the subtrait definition

The compiler could reject a subtrait that defines an item with the same name as a supertrait item. That moves the breakage from the call site to the definition but doesn't remove it, and it rules out legitimate deliberate shadowing.

# Prior art

- **Object-oriented languages** such as Java, C#, and C++ resolve member names to the most derived declaration. Rust traits aren't classes, but the intuition that the more specific definition wins is familiar.
- **Scala traits** use linearization to decide which member wins in multiple inheritance. That is more involved than this proposal, which declares a tie an ambiguity rather than linearizing.
- **Haskell type classes** don't allow two classes in scope to share a method name unqualified. The module system enforces this through qualified imports.

# Unresolved questions

- Should the usage lint be warn-by-default or allow-by-default? This RFC proposes warn so the change is visible at first, with room to relax it later.
- Should the same rule eventually apply to concrete types when the candidates are related by a supertrait relationship? This might be considered as follow-up work.

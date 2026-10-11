# Rust RFC 2845: supertrait_item_shadowing

- Feature Name: `supertrait_item_shadowing`
- Start Date: [TODO: date]
- RFC PR: [TODO]
- Rust Issue: [TODO]

## Summary

Change item resolution for generics and trait objects so that a trait bound does not bring its supertraits' items into scope if the subtrait defines an item with the same name itself.

## Motivation

A trait bound `T: Sub` makes the methods of `Sub` callable on values of type `T`. If `Sub` has a supertrait `Super`, the bound also makes the methods of `Super` callable. When both traits define a method with the same name, a call is ambiguous:

```rust
trait Super {
    fn describe(&self) -> String;
}

trait Sub: Super {
    fn describe(&self) -> String;
}

fn show<T: Sub>(x: &T) -> String {
    x.describe() // error: multiple applicable items in scope
}
```

The same happens for a trait object, `&dyn Sub`. [TODO: confirm the current error for both the generic and the trait object case, with its error code.]

The caller can resolve the ambiguity by naming the trait, `Sub::describe(x)`. The problem is that the ambiguity can appear without any change to the code that now fails. Suppose `Super` is defined in crate A and `Sub` in crate B, which depends on A. Crate B defines `Sub::describe` and calls `x.describe()` in generic code. Then crate A adds a method `describe` to `Super`, with a default body, in a minor release. Adding a defaulted method to a trait is generally treated as a compatible change. [TODO: cite the API evolution guideline that classifies it.] Crate B nevertheless stops compiling, although nothing in crate B changed.

[TODO: whether this scenario is the author's main motivation, and one or more real occurrences, for example a method added to a standard library trait that broke downstream subtraits. If the motivation is different, for example a specific feature that needs this rule, replace this paragraph.]

## Guide-level explanation

When a generic parameter or trait object is bounded by a trait, method calls on it look first at that trait's own items. If the trait defines an item with the requested name, that item is used, and supertraits are not consulted for that name. If the trait defines no item with that name, its supertraits are searched as before.

With this RFC, the example above compiles, and `x.describe()` calls `Sub::describe`:

```rust
fn show<T: Sub>(x: &T) -> String {
    x.describe()          // calls Sub::describe
}

fn show_super<T: Sub>(x: &T) -> String {
    Super::describe(x)    // calls Super::describe
}
```

To call the supertrait's item, name the trait, as in `show_super`. That syntax already works today and is unchanged.

A name that only the supertrait defines still resolves to the supertrait. A subtrait shadows only the names it defines.

## Reference-level explanation

The rule applies when method or associated item lookup goes through a trait bound: a generic parameter with bounds, an associated type with bounds, or a trait object type. When the lookup finds candidates from a trait `Sub` and from one of its supertraits, directly or through a chain of supertraits, and `Sub` is a subtrait of the other trait, the candidate from the trait lower in the hierarchy wins.

[TODO: the rule for diamonds. If `Sub: A + B` and both `A` and `B` define `describe`, but `Sub` does not, the call should remain ambiguous, because neither candidate is lower than the other. Confirm.]

[TODO: the rule for a chain. If `C: B` and `B: A`, and all three define `describe`, `C::describe` is used for a `T: C` bound. If only `A` and `B` define it, `B::describe` is used. Confirm that shadowing is transitive in this way.]

### Scope of the change

The abstract limits the change to generics and trait objects. For a concrete type that implements both traits, method lookup goes through the traits that are imported with `use`, not through a bound. That case is not changed by this RFC. If both `Super` and `Sub` are in scope and implemented for a concrete type `S`, `s.describe()` remains ambiguous. [TODO: the author's reason for excluding concrete types, so that readers can judge whether the exclusion is deliberate or left for later.]

### Explicit bounds on the supertrait

A generic parameter can name both traits, `T: Sub + Super`. Then `Super` is brought into scope by its own bound, not only as a supertrait of `Sub`. [TODO: whether `x.describe()` is ambiguous in that case. Two readings are possible. Under one, `Sub` still shadows `Super`, because `Sub` is lower in the hierarchy. Under the other, the explicit bound shows that the writer wants `Super`'s items, and the call is ambiguous. The RFC must choose, because the choice decides whether adding a redundant bound can change which method is called.]

### Associated types and constants

The abstract speaks of items, not only methods. [TODO: confirm that the rule applies in the same way to associated types and associated constants, for example to `T::Output` where both traits define `Output`.]

## Drawbacks

The rule can select a different method than the writer meant, without an error. Today, the ambiguity forces the writer to choose. Under this RFC, the compiler chooses the subtrait's item. If the writer meant the supertrait's, the code still compiles, and the bug appears at run time. This matters most when the two items have the same signature but different behavior. When the signatures differ, a type error is likely.

The rule also creates a version of the problem it fixes, in the other direction. If crate B's generic code calls `x.describe()` and today resolves to `Super::describe`, because `Sub` has no `describe`, then adding `describe` to `Sub` silently changes which method is called. The RFC moves the hazard from the supertrait's author to the subtrait's author. [TODO: whether the author considers that acceptable, and why. A plausible argument for the author to confirm is that the subtrait's author is the one who chose the name and can see the call sites, while the supertrait's author cannot.]

The behavior for concrete types and the behavior for bounds now differ. The same call `x.describe()` can be ambiguous when `x: S` and unambiguous when `x: T` with `T: Sub`, even if `S` is the type later substituted for `T`.

## Rationale and alternatives

[TODO: the alternatives the author actually considered and why each lost. Suggestions for the author to evaluate, not yet considered:

1. Keep the ambiguity error, and rely on fully qualified syntax. This keeps behavior explicit but leaves the breakage described in Motivation.
2. Resolve to the subtrait's item, but emit a warning, so that writers can see the choice without a build failure.
3. Apply the rule to concrete types as well, for consistency.]

## Prior art

[TODO: how other languages with interface inheritance resolve a method defined in both an interface and its parent, if the author wants to cite any.]

## Unresolved questions

1. Diamonds and chains of supertraits (Reference-level explanation).
2. Explicit bounds on the supertrait (Explicit bounds on the supertrait).
3. Associated types and constants (Associated types and constants).
4. Whether a warning accompanies the new resolution (Rationale and alternatives).

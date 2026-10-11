# RFC 2845: supertrait_item_shadowing

- Feature Name: `supertrait_item_shadowing`
- Start Date: [TODO]
- RFC PR: [TODO]
- Rust Issue: [TODO]

## Summary

This RFC changes item resolution for generics and trait objects. A trait bound no longer brings the items of its supertraits into scope when the subtrait defines an item with the same name itself.

## Motivation

A method call such as `x.len()` on a generic value `x: T` is resolved against the traits that bound `T`. A bound `T: Sub` makes the methods of `Sub` available, and also the methods of every supertrait of `Sub`. If `Sub` and one of its supertraits both define a method named `len`, the call has two candidates.

Today that situation is an ambiguity error. [TODO: author to confirm the current behavior. The abstract does not state it. It states only the change, which implies the present rule treats both items as in scope.]

Consider:

```rust
trait Base {
    fn describe(&self) -> String;
}

trait Derived: Base {
    fn describe(&self) -> String;
}

fn show<T: Derived>(x: &T) -> String {
    x.describe()
}
```

The function `show` asks for `describe` on a type known only by its bound `Derived`. Under the current rule, both `Derived::describe` and `Base::describe` are candidates. Under this RFC, `Derived` defines its own `describe`, so the bound does not bring the supertrait's `describe` into scope, and the call resolves to `Derived::describe`. [TODO: author's real example. This one is constructed to show the rule and is not drawn from the material.]

[TODO: the author's motivating case. A likely source is a library that adds a method to a subtrait whose name already exists on a supertrait, or a supertrait that gains a method later and breaks downstream code. The material does not say which, and the RFC should not guess.]

The question this RFC answers is which of two methods with the same name a reader expects the call to mean. The abstract's rule is that the more specific trait wins: the trait that declares the bound shadows the traits it extends. This mirrors how a name defined in an inner scope hides a name of the same spelling in an outer scope.

## Guide-level explanation

When a generic parameter or a trait object has the bound `Sub`, a lookup of a name proceeds in this order:

1. Items defined by `Sub` itself.
2. Items of the supertraits of `Sub`, only for names that `Sub` did not define.

Each step shadows the next. A name found at step 1 ends the search. The supertrait items with that name stay reachable through a fully qualified path:

```rust
<T as Base>::describe(x)
```

The same rule applies to `dyn Sub`.

The rule is limited to the effect of a bound. It does not change which items are in scope for a concrete type that implements both traits, where the usual trait-in-scope rules continue to apply. [TODO: author to confirm.]

## Reference-level explanation

Item resolution for a path or method call on a type parameter `T` or a trait object `dyn Tr` collects the items named by the bounds in scope.

1. For each bound `B` on the parameter, gather the items that `B` defines with the given name.
2. If any bound defines an item with that name, use only those items and skip the supertraits of the bounds that define it.
3. Otherwise gather the items of the supertraits of each bound, as is done today.

[TODO: author to specify the case with several bounds, where `T: A + B` and `A` defines the name while `B`'s supertrait also defines it. The abstract speaks of "a trait bound" and "the subtrait", in the singular, and the multi-bound case needs its own sentence. The rule above is one reading, and the author must confirm it.]

[TODO: specify the case of a name defined in two unrelated supertraits of `Sub` when `Sub` itself does not define it. State whether the ambiguity error remains.]

[TODO: specify associated types and constants, which are also items. The abstract says "items", which includes them, so the same rule applies, but the author should confirm.]

## Drawbacks

The change makes the meaning of a call depend on whether a subtrait defines a name. When a library adds a method to a subtrait, a call in downstream generic code can change from resolving to the supertrait method to resolving to the new subtrait method, with no error. A silent change in meaning is a worse failure than an ambiguity error, which at least stops the build. [TODO: author's response, such as a lint, and the evidence on how likely the case is. The material has no data.]

The rule also gives subtrait and supertrait authors an interaction they must now track: a method added to either trait can change which one a generic call reaches.

## Rationale and alternatives

The status quo is an ambiguity error, which the programmer fixes with a qualified path. It makes the programmer's intent explicit and costs a longer call at each ambiguous site. The RFC prefers shadowing because [TODO: the author's reason; the abstract states the change but gives no argument for it].

[TODO: alternatives. Questions for the author: keeping the error and improving its message, warning on the shadowed call, applying shadowing only to trait objects, and requiring an attribute on the subtrait to opt into shadowing. State each only if it was weighed and say why it lost.]

## Compatibility

[TODO: author to state the effect on existing code. The calls this RFC touches are exactly the calls that compile today only if no name is shared, or that already fail for ambiguity. If so, the programs that compile today keep their meaning, and only previously ambiguous programs change. The material does not confirm this analysis, and the RFC makes no claim about it until the author does.]

## Prior art

[TODO: any language with a similar rule, such as shadowing of inherited members in class-based languages. The material cites none and this document adds none.]

## Unresolved questions

1. The behavior with several bounds.
2. The behavior with unrelated supertraits that share a name.
3. Whether a lint accompanies the change.
4. The effect on existing code.

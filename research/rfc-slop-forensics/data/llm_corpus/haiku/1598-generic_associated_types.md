# Rust RFC 1598: generic_associated_types

- Feature Name: `generic_associated_types`
- Start Date: 2016-09-06
- RFC PR: (to be assigned)
- Rust Issue: (to be assigned)

## Summary

This RFC allows type constructors to be associated with traits. An associated type may take its own generic parameters, so that a trait can describe a family of types indexed by a lifetime or a type. This is an incremental step toward higher-kinded types, a feature that many Rust users have ranked highly. The specific feature described here, associated type constructors, resolves one of the most common motivating examples for higher-kindedness, and it extends the type system in a comparatively modest way. The design is forward compatible with richer forms of higher-kinded polymorphism that may be introduced later.

## Motivation

Associated types let a trait name a type that each implementation chooses. An iterator trait, for example, has an associated `Item` type, and each iterator decides what that type is. This works well when the associated type is a single type. It works poorly when the associated type must vary with a lifetime or with another type parameter.

Consider a trait that lends out a view into some underlying data. The view should borrow from the implementor, so its type depends on the lifetime of the borrow. Today the trait cannot express this relationship directly. The trait must either fix the lifetime in advance, which is too restrictive, or it must pass the borrow through a separate generic parameter, which moves the relationship outside the trait where it cannot be enforced in each implementation.

A similar problem arises with collections that return pointer-like wrappers. A trait that abstracts over smart pointers would like to say that for each pointer type there is a corresponding wrapper parameterized by the element type. Without associated type constructors, the trait can name only one wrapper type for each implementation and cannot vary it with the element.

These examples share a common shape. The associated type needs to be a function from some parameters to a type, rather than a single type. Higher-kinded types would give the full generality of such functions. Associated type constructors give the part that solves the common cases, and they do so without introducing the full machinery that a complete solution would require.

## Guide-level explanation

An associated type may now declare its own generic parameters. The declaration appears in the trait, and each implementation supplies the type for each choice of parameters. A trait that lends a view might be written as follows:

```rust
trait Lender {
    type View<'a> where Self: 'a;

    fn lend<'a>(&'a self) -> Self::View<'a>;
}
```

Here `View` is an associated type constructor. Each implementation chooses what `View<'a>` means, and the chosen type may depend on the lifetime. A where clause limits the parameters to those for which the type is well formed, so the implementor's data outlives the view.

Users of the trait write `Self::View<'a>` wherever the associated type is needed, and they supply the lifetime as they would for any generic type. The compiler checks that each use is consistent with the implementation, and it reports an error if a required bound is missing.

The feature does not, at this stage, allow an associated type to take a higher-kinded parameter, meaning a parameter that is itself a type constructor. That extension is left for future work.

## Reference-level explanation

### Syntax

An associated type declaration may include generic parameters, which may be lifetimes or types, following the name of the type. The declaration may also include a where clause that constrains those parameters, using the same rules as for generic items. Implementations provide the type with the same parameter list, and the parameter names in the implementation need not match those in the trait.

### Projection

A projection of the form `<T as Trait>::Assoc<Args>` names the type that the implementation of `Trait` for `T` provides for the given arguments. The arguments must satisfy the bounds declared on the associated type. Projections are normalized in the same way as ordinary associated type projections, so that the compiler replaces the projection with the concrete type when it knows the implementation.

### Where clauses

The where clauses on an associated type may refer to the parameters of the type and to the implementing type. A common pattern requires that the implementing type outlive the lifetime parameter, so that the associated type cannot outlive the data it borrows. The compiler checks these clauses at each implementation and at each use.

### Object safety

A trait that contains an associated type constructor with type parameters is not object safe, because the type of each method's result would depend on parameters that a trait object cannot supply. Traits with associated type constructors that take only lifetime parameters may remain object safe in some cases. The rules for this distinction are described in the reference and will be refined during implementation.

### Interaction with existing features

The feature composes with generic methods, default type parameters, and trait bounds on associated types. It does not change the meaning of associated types that have no parameters, so existing code is unaffected.

## Drawbacks

The feature adds complexity to the trait system. Implementors must understand where clauses on associated types, and the compiler must reason about projections with parameters. Error messages for mismatched bounds may be harder to read than those for ordinary associated types.

The feature also sets a precedent. Once associated type constructors exist, users will expect them to work in more places, and the team will face pressure to extend the design toward full higher-kinded types. The RFC accepts this pressure as a reason for careful staging.

## Rationale and alternatives

One alternative is to wait for full higher-kinded types. That design would cover associated type constructors and more, but it requires a larger body of theory and implementation work. The incremental approach delivers a useful feature sooner and tests the design in practice.

A second alternative is to use the existing workarounds, such as passing the varying type as a separate generic parameter of the trait. These workarounds are sound, but they move the relationship out of the trait and make it harder for users to write generic code. They also do not extend to the lifetime case in a clean way.

A third alternative is to restrict the feature to lifetime parameters only. This would be simpler, but it would leave the collection and pointer examples unsolved. The RFC therefore allows type parameters as well, with the restrictions noted above.

## Prior art

Several languages and research systems have explored type constructors in traits or interfaces, with varying degrees of generality. The experience from those systems suggests that the most common uses are covered by a restricted form, and that the full generality is needed only rarely. This RFC follows that suggestion.

## Unresolved questions

The rules for object safety are not yet settled in detail. The RFC proposes a conservative default, but the precise conditions under which a trait with associated type constructors may be used as a trait object will be refined during implementation.

The interaction with specialization and with certain forms of trait bounds is also open. The team expects to resolve these questions as the feature is implemented and tested against real code.

## Future possibilities

The natural next step is to allow associated types to take higher-kinded parameters, which would make it possible to express traits over type constructors directly. Such a feature would build on the syntax and the projection rules introduced here, and it would extend the reach of the design without requiring a new model of the type system.

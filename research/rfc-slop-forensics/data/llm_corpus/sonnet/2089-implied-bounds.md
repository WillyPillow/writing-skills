# RFC: Implied bounds

- Feature Name: `implied_bounds`
- Start Date: 2017-07-10
- RFC PR: rust-lang/rfcs#2089
- Rust Issue: rust-lang/rust#44491

## Summary

Eliminate the need for "redundant" bounds on functions and impls where those bounds can be inferred from the input types and other trait bounds. For example, in this simple program, the impl would no longer require a bound, because it can be inferred from the `Foo<T>` type:

```rust
struct Foo<T: Debug> {
    x: T,
}

// Today this needs `T: Debug` repeated.
impl<T: Debug> Foo<T> {
    // ...
}
```

Hence, simply writing `impl<T> Foo<T> { ... }` would suffice. We currently support implied bounds for lifetime bounds, super traits and projections. We propose to extend this to all where clauses on traits and types, as was already discussed in earlier design conversations.

## Motivation

### Redundant bounds are boilerplate

Rust requires that a type be well-formed wherever it is written. For `Foo<T>` to be well-formed, `T: Debug` must hold. Whenever the programmer writes `Foo<T>` in the signature of a function or impl, the compiler checks that `T: Debug` can be proven from the where clauses in scope. If it cannot, the code is rejected, and the user must add `T: Debug`.

But the compiler has learned something by looking at the signature. If a function takes a `Foo<T>` as a parameter, then callers must have supplied a well-formed `Foo<T>`, and so `T: Debug` is known to hold inside the body. The bound is therefore redundant in two senses: it is implied by the types in the signature, and it adds no new restriction at call sites, since callers need to satisfy it to construct the argument anyway.

Despite this, today the user writes the bound anyway:

```rust
fn print_all<T: Debug>(items: &[Foo<T>]) { ... }
```

This duplication is a common complaint. It creates maintenance cost, because adding a bound to a struct requires touching every impl and function that mentions it. It also creates a pitfall for library authors who want to evolve a type definition.

### Existing precedent

Rust already infers some bounds from signatures. A reference type `&'a T` implies `T: 'a`, so the user writes `fn f<'a, T>(x: &'a T)` and need not add the outlives bound. Supertraits are implied: if `T: Ord`, then `T: PartialOrd`, `T: Eq` and `T: PartialEq` are available. Associated type projections are normalized under assumptions drawn from where clauses. The proposal here generalizes this existing behavior; it does not introduce a new concept.

### Alignment with the trait system implementation

The ongoing work on a new trait solver, based on Chalk, models the environment of a function as a set of "program clauses". In that formulation, well-formedness of the input types naturally produces facts that can be added to the environment. Implementing implied bounds for all where clauses is a small step once this is in place.

## Detailed design

### Terminology

A *where clause* is any predicate of the form `T: Trait`, `T: 'a`, or `<T as Trait>::Assoc == U`. A type or trait definition may carry where clauses, including those written in bound position, as in `struct Foo<T: Debug>`. A type is *well-formed* in an environment if every where clause on its definition, instantiated with its actual arguments, can be proven in that environment.

### The rule

When checking an item (a function, impl, or trait), the compiler constructs an *environment* consisting of the explicit where clauses written on the item and its parents. We extend the environment with the following *implied clauses*:

For each type `Ty` appearing in the signature of the item, namely the types of inputs, the return type for functions, and the self type and trait reference for impls, we add the well-formedness conditions of `Ty`. Concretely, if `Ty = Foo<A, B>` and `Foo` is defined with where clauses `W1, ..., Wn`, then `W1[A, B], ..., Wn[A, B]` are added to the environment.

The rule is applied transitively to nested types. For `Vec<Foo<T>>`, the conditions of `Foo<T>` are added; the conditions of `Vec` are as defined by its own where clauses.

Importantly, implied clauses are assumed only *inside* the item. They are not added to the item's own *requirements as seen by callers*. A caller must still demonstrate that the arguments it passes are well-formed, which by construction entails the implied clauses.

### Impls

For an impl, the types in the header (`Self` and the trait reference) contribute implied clauses to the impl's environment. Thus:

```rust
impl<T> Foo<T> {
    fn show(&self) { println!("{:?}", self.x); }
}
```

The compiler infers `T: Debug` from `Foo<T>` and the body type-checks.

For trait impls, implied clauses from the header apply to each method in the impl. Implied clauses do *not* flow across the impl boundary to the trait: callers using the trait through a generic parameter only get the bounds stated on that parameter.

### Traits

For a trait definition, implied bounds from the types in method signatures are available only within default method bodies and do not extend the trait's public contract. In other words, they do not turn into additional supertraits.

### Which clauses are *not* implied

To keep the rule sound and avoid surprising inference, the following are not implied:

- Bounds appearing only in the *body* of a function.
- Bounds on type aliases, as aliases are expanded before well-formedness is computed, and bounds on aliases are not enforced.
- Bounds from `impl Trait` in argument position that refer to anonymous parameters, to avoid leaking hidden bounds.

### Soundness

The key observation is that implied clauses are only assumed for types the compiler can see in the signature, and callers must prove well-formedness of the arguments they provide. There is one subtlety: *higher-ranked* types and function pointers. A value of type `fn(Foo<T>)` can be obtained without proving that `T: Debug` if the value was created in a different environment. The known soundness hole associated with implied bounds on function pointer types (where lifetime bounds are inferred from a `for<'a>` signature) must be kept in mind. This RFC does not extend implied bounds to nested positions under binders, and restricts itself to the top-level types of signatures.

## How We Teach This

The primary message is: "You don't need to repeat bounds that the type already requires." In the Book, the section on generics would be updated to say that when a struct has a bound, functions that take that struct do not need to repeat it.

Existing code that includes the redundant bounds continues to compile. A future lint, `redundant_bounds`, could suggest removals, but that is not part of this RFC.

Error messages must change. When a bound is missing in a situation where it is not implied, the compiler should mention the possibility of the user adding the bound, as it does now.

## Drawbacks

- The signature of an item no longer fully documents the requirements of its body. A reader must look at the definition of every type in the signature to know what is assumed.
- Changing a type's where clauses becomes a more subtle semver event. Adding a bound to a struct is already a breaking change; with implied bounds, removing one can also break downstream code that relied on inferring it.
- Diagnostics may be harder to produce, as the environment is now larger and error messages must decide which clauses to display.
- It makes the trait solver's work somewhat larger, since the environment gets bigger for every function with generic types.

## Alternatives

**Do nothing.** Users continue to repeat bounds. This has no cost to the compiler but remains a recurring papercut.

**Only imply bounds on the `Self` type of impls.** This addresses the most common complaint, impl blocks on constrained structs, with a smaller change. However, it would leave functions out, and would be an odd half-measure.

**Remove bounds from struct definitions.** Some propose removing the practice of putting bounds on structs at all, putting them only on impls. This is a style preference, not a language change, and it would not help with associated types or types in existing libraries.

## Unresolved questions

- Should implied bounds apply to associated type bounds defined in trait definitions?
- How should the feature behave with respect to `?Sized`?
- Is the restriction against inference under binders adequate to avoid known soundness issues, or are further limits needed?
- Should a lint exist to detect redundant explicit bounds, and should it be enabled by default?

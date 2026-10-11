# RFC 2093: infer_outlives

- Feature name: `infer_outlives_requirements`
- Start date: [TODO: date]
- RFC PR: [TODO: link]
- Tracking issue: [TODO: link]

## Summary

Remove the need to write `T: 'a` bounds on structs. The compiler infers them from the struct's fields: if the struct contains a reference to `T` with lifetime `'a`, directly or through other types, the compiler adds the requirement `T: 'a`. Explicit annotations remain allowed. They still control the default lifetime of trait objects, and existing code that writes them keeps compiling.

## Motivation

A struct that holds a reference to a generic type must currently say that the type outlives the reference:

```rust
struct Ref<'a, T: 'a> {
    value: &'a T,
}
```

The bound `T: 'a` is required because the type `&'a T` is only well formed when `T` outlives `'a`. The compiler checks that the struct's fields are well formed using only the struct's declared bounds, so the bound must be declared. Leaving it out is an error:

```text
error[E0309]: the parameter type `T` may not live long enough
```

The bound carries no information the reader does not already have. Anyone who sees the field `&'a T` knows that `T` must outlive `'a`. The compiler knows it too, since that is the rule it uses to reject the version without the bound. The bound exists only to satisfy the check.

The requirement spreads. A struct that contains `Ref<'a, T>` must also declare `T: 'a`, because `Ref<'a, T>` is only well formed under that bound:

```rust
struct Wrapper<'a, T: 'a> {
    inner: Ref<'a, T>,
}
```

So the bounds in one struct depend on the bounds in every struct it contains. When a field's type changes, bounds in other structs may need to change too. [TODO: add examples from real code, or reports from users, of the error and of the bounds it forces. Numbers on how often `T: 'a` appears on structs in crates.io code would show the scale.]

The bounds also surprise new users. Many structs with references follow the same pattern, and the error message tells the user to add a bound that the struct's fields already imply. [TODO: cite the learning material or issues that show this, if the author has them.]

## Guide-level explanation

After this change, both structs above can be written without the bounds:

```rust
struct Ref<'a, T> {
    value: &'a T,
}

struct Wrapper<'a, T> {
    inner: Ref<'a, T>,
}
```

The compiler infers `T: 'a` for both. The bounds still exist; they are no longer written. Code that uses `Ref<'a, T>` must still satisfy `T: 'a`, and an error that mentions the bound points at the field that requires it.

Writing the bound explicitly is still allowed. It is needed in one case, described below: when the bound should change the default lifetime of a trait object.

## Reference-level explanation

### What is inferred

The compiler computes a set of outlives requirements for each struct, enum and union. The requirements are predicates of two forms, `T: 'a` and `'b: 'a`, where `T` is a type and `'a` and `'b` are lifetimes.

The set is computed from the field types:

1. For a field of type `&'a T` or `&'a mut T`, add `T: 'a`, then process `T`.
2. For a field whose type is another ADT, `Foo<'x, U>`, take the inferred requirements of `Foo`, substitute the arguments, and add the results.
3. For a field whose type is a projection, such as `<T as Trait>::Assoc`, combined with a lifetime, such as `&'a <T as Trait>::Assoc`, add `<T as Trait>::Assoc: 'a`.
4. Bounds that the struct declares explicitly are added as well.

Requirements that mention only the struct's own generic parameters are kept. Requirements on concrete types, such as `u32: 'a`, are always true, and are dropped. [TODO: confirm how requirements on types that mention both a parameter and a concrete type are handled, for example `Vec<T>: 'a`.]

### Fixed point

Rule 2 makes the requirements of one type depend on those of another, and types can be recursive:

```rust
struct List<'a, T> {
    head: &'a T,
    tail: Option<Box<List<'a, T>>>,
}
```

The compiler computes all requirements together, starting with the empty set for every type and applying the rules until no set changes. Each step only adds predicates, and the predicates are drawn from a finite set for each type, so the computation stops. [TODO: confirm the bound on iterations, or state the algorithm the implementation uses.]

### Where inferred requirements apply

The inferred requirements are added to the struct's predicates wherever the compiler checks that a use of the struct is well formed. They behave the same as written bounds for type checking and borrow checking.

### Trait object defaults

The default lifetime of a trait object depends on explicit bounds on the type parameter that contains it. Given

```rust
struct Ref<'a, T: ?Sized + 'a> {
    value: &'a T,
}
```

the type `Ref<'a, dyn Display>` means `Ref<'a, dyn Display + 'a>`. Without the explicit bound, it means `Ref<'a, dyn Display + 'static>`.

Inferred requirements do not change these defaults. Only explicit bounds do. If inference changed the default, removing an explicit bound from a struct would keep the same meaning, but adding a field to a struct could change the meaning of `dyn Trait` written elsewhere, in code that never mentions the field. Keeping the defaults tied to explicit bounds means that a struct's declaration controls them, as it does today.

This is the main reason to keep writing the bound explicitly after this change: to request the `'a` default for trait objects.

### Scope

Inference applies to structs, enums and unions. [TODO: decide whether it also applies to type aliases, impls, functions, and trait declarations. Functions already get implied bounds from their argument types, so the question is mainly about impls and traits.]

## Drawbacks

Inferred bounds are part of the type's interface without appearing in its declaration. Today, a library author who changes a private field from `T` to `&'a T` must add `T: 'a` to the struct, and that edit shows that the struct now requires something new of its users. After this change, the same field change adds the requirement silently. A user who wrote `Ref<'a, T>` for some `T` that does not outlive `'a` gets an error that was not there before, and the library's diff shows only a field change. Changes to private fields can therefore break semver compatibility without any change to public items. [TODO: decide whether this needs a lint, for example in a semver checking tool, or a note in the API guidelines.]

Error messages become harder to read. An error about `T: 'a` may now refer to a bound that is not written anywhere. The message must point to the field, possibly in another crate, that causes the requirement.

Readers who knew the old rule may look for the bound and not find it.

## Rationale and alternatives

The bounds this RFC removes are ones the compiler already derives in order to reject the code. Inferring them removes no check: code that was rejected because a bound was missing is now accepted with the same bound in place.

[TODO: Was a smaller change considered, such as inferring only from direct `&'a T` fields and not through other ADTs? It would avoid the fixed-point computation and make the semver issue local to one struct, but would leave `Wrapper` needing its bound. Record whether it was considered and why it lost.]

[TODO: Was improving the error message, with a suggested fix, considered as an alternative to inference? Record why it was judged insufficient, if it was.]

## Compatibility

All code that compiles today keeps compiling, since explicit bounds are still accepted and inference adds only bounds that the field types already required. [TODO: confirm with a Crater run.] Trait object defaults are unchanged, because they depend only on explicit bounds.

## Unresolved questions

- Whether inference extends to impls and traits.
- How requirements on types that mix parameters and concrete types are simplified.
- Whether a lint should suggest removing explicit bounds that inference would add, given that some of them affect trait object defaults.

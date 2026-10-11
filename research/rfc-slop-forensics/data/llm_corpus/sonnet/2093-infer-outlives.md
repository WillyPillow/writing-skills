# RFC 2093: infer_outlives

- Feature Name: `infer_outlives`
- Start Date: 2017-04-20
- RFC PR: rust-lang/rfcs#2093
- Rust Issue: rust-lang/rust#44493

## Summary

Remove the need for explicit `T: 'x` annotations on structs. We will infer their presence based on the fields of the struct. In short, if the struct contains a reference, directly or indirectly, to `T` with lifetime `'x`, then we will infer that `T: 'x` is a requirement. Explicit annotations remain as an option used to control trait object lifetime defaults, and simply for backwards compatibility.

## Motivation

Consider a struct that holds a reference:

```rust
struct Ref<'a, T> {
    r: &'a T,
}
```

Under the rules adopted by RFC 1214, this definition is an error. The type `&'a T` is well-formed only if `T: 'a`, meaning that every reference inside `T` outlives `'a`. The struct definition does not state this, so the compiler requires the programmer to add it:

```rust
struct Ref<'a, T: 'a> {
    r: &'a T,
}
```

The annotation `T: 'a` is pure boilerplate. It is forced by the field `r`, it can be derived by a mechanical process, and the compiler already knows what it has to be, because it tells the user in the error message. Nothing is gained from asking the programmer to retype it, and in practice it is one of the most frequently reported papercuts in the language. Beginners are confused by it: the error mentions a "may not live long enough" condition on a type parameter that appears nowhere in the field's description of the type's purpose, and the fix looks arbitrary.

The problem compounds. A struct that contains a `Ref<'a, T>` must itself have `T: 'a`:

```rust
struct Wrapper<'a, T: 'a> {
    inner: Ref<'a, T>,
}
```

Here the bound is not even visible from the field's type syntax, since `Ref<'a, T>` does not look like a reference. The programmer must open the definition of `Ref`, discover its requirement, and replicate it. If `Ref` is in another crate and the library author later adds a requirement of its own, every downstream struct that wraps it will break, although those downstream definitions did nothing wrong.

Finally, the pattern interacts with generics over several parameters and trait bounds. In a struct such as

```rust
struct Parser<'a, I: 'a, O: 'a> where I: Iterator<Item = &'a O> { ... }
```

the annotations clutter the declaration and obscure the real bounds.

## Guide-level explanation

After this RFC, you will no longer need to write `T: 'a` on structs, enums and unions when the requirement follows from their fields. The following compiles as written:

```rust
struct Ref<'a, T> {
    r: &'a T,
}

struct Wrapper<'a, T> {
    inner: Ref<'a, T>,
}
```

The compiler looks at the fields and decides that `Ref` requires `T: 'a`, and that `Wrapper` requires the same.

What does this mean for users of these types? When you write `Ref<'x, U>`, the compiler checks that `U: 'x`. This is the same check as before. If you write `Ref<'x, Vec<&'y str>>`, it checks `Vec<&'y str>: 'x`, which holds only if `'y: 'x`. The difference is entirely in what the *definition* has to say.

Explicit annotations are still permitted. They are never an error even if they are redundant. They continue to be useful in one case: they affect the default object lifetime bound for trait objects. Given

```rust
struct Foo<'a, T: 'a + ?Sized> {
    r: &'a T,
}
```

the type `Foo<'a, dyn Trait>` has its object lifetime default derived from the `T: 'a` bound, so it means `Foo<'a, dyn Trait + 'a>`. Under the RFC, inferred bounds do not influence this default, so for a struct written as `struct Foo<'a, T: ?Sized>`, the default is the normal one that applies when no bound is present. This keeps the behaviour of existing code unchanged and avoids making inference visible in the interpretation of types.

## Reference-level explanation

### Inference

For each struct, enum, or union, the compiler computes a set of outlives predicates by examining every field type. The set is the least solution of the following constraints.

For a field of type `&'a T`, add `T: 'a`. For a field of type `&'a mut T`, add the same. For a field whose type is `S<P1..Pn>` where `S` is another struct, enum, or union defined in the program, take the predicates inferred for `S` and substitute `P1..Pn` for its parameters. For fields of type `[T; N]`, `[T]`, `(T, U)`, and `Box<T>`, recurse into the component types. For a field of type `fn(T) -> U`, no requirement is added, because function pointers carry no references of their own.

Predicates may also arise from projections. For a field of type `<T as Trait>::Assoc` or a `T::Assoc`, the inference adds nothing. The requirements for associated types are derived from the trait's own where clauses and the existing rules for well-formedness. Where a reference to a projection appears, as in `&'a T::Assoc`, we add `T::Assoc: 'a`, which, using the existing outlives rules for projections, reduces to `T: 'a` together with outlives bounds on the trait's other parameters.

### Recursion

Structs may refer to each other, including cyclically. Inference proceeds as a fixed-point iteration. Each struct begins with an empty set of predicates. The predicates are recomputed from the fields using the current sets for referenced structs, and the process is repeated until no set changes. Since the number of possible predicates is finite for a program, the iteration terminates.

### Trait objects

If a field is of the form `Box<dyn Trait + 'b>`, the bound `'b` is part of the type and imposes no requirement on parameters in the struct definition, aside from the usual condition that `'b` is in scope. Where the object lifetime is elided and defaults to a bound that depends on an enclosing reference, as in `&'a dyn Trait` which means `&'a (dyn Trait + 'a)`, that lifetime is the same lifetime already written and so adds nothing further.

### Where clauses and explicit bounds

Explicit `T: 'a` bounds, whether in the parameter list or in a `where` clause, continue to be accepted. They are combined with the inferred predicates when checking uses of the type. Because inferred predicates are a subset of what is provable from the fields, adding an explicit bound can only add requirements; it never removes inferred ones.

### Effect on well-formedness

The well-formedness check for a type `S<Args>` now includes the inferred predicates of `S`. A type that was well-formed before, because the user wrote the necessary bounds, remains well-formed, since those explicit bounds are at least as strong as the inferred ones for any program that compiled.

### Impls

An `impl` for a struct need not restate the inferred predicates. `impl<'a, T> Trait for Ref<'a, T>` is accepted, whereas under the old rules it required `T: 'a` to be implied or stated. The implied bound is taken from the struct's inferred predicates. This matches the existing behaviour for explicit bounds, which are likewise implied in impl headers by RFC 2089's accepted direction on implied bounds.

## Drawbacks

Inference makes the requirements of a type less visible at the definition. A reader of `struct Wrapper<'a, T> { inner: Ref<'a, T> }` must know the definition of `Ref` to understand the implied bound. This is the same sort of non-local reasoning already required for variance, which is also inferred from fields.

It also means that a change to a struct's fields can alter its outlives requirements, which is a potentially breaking change to downstream code that instantiates the struct. Previously, this was visible in the signature because the annotation had to change. It is now a semver subtlety. This is similar to variance and auto traits, which are also computed from fields, and the community has already accepted this tradeoff there.

Finally, the exception for trait object defaults introduces a distinction between explicit and inferred bounds that can surprise users. The alternative of having inferred bounds affect defaults would change the meaning of existing code, which is not acceptable.

## Rationale and alternatives

**Do nothing.** The boilerplate remains. This is the status quo and it is widely disliked.

**Make the bound implied but require a keyword.** Something like `struct Ref<'a, T: infer>` would be explicit but just as noisy as the status quo.

**Allow inference only within a crate.** This avoids cross-crate semver concerns but yields inconsistent behaviour and would require extra metadata handling. Because the work is done on declared field types, which are already stored in crate metadata, cross-crate inference costs nothing extra.

**Infer on functions as well.** Functions already receive implied bounds from their argument types under RFC 2089, and are outside the scope of this RFC.

## Prior art

Variance inference in Rust is computed from struct fields without annotations. Haskell infers type class constraints for functions, though not for data type declarations. Languages with no lifetime system have no analogous requirement.

## Unresolved questions

* Should the compiler lint redundant explicit `T: 'a` bounds? Doing so would encourage migration but could be noisy.
* How should the diagnostics surface inferred bounds when a user violates one? The message should name the field that caused the requirement.
* Are there cases involving higher-ranked trait bounds in fields where inference is ambiguous? The current plan is to ignore such fields conservatively and add no predicate, falling back on the explicit annotation.

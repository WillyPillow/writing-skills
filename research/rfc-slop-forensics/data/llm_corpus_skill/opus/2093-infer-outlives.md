# RFC 2093: `infer_outlives`

- Feature Name: `infer_outlives`
- Start Date: [TODO: date]
- RFC PR: [TODO: link]
- Rust Issue: [TODO: link]

## Summary

Remove the need to write `T: 'x` annotations on structs. The compiler infers them from the struct's fields. If a struct contains a reference with lifetime `'x` to `T`, directly or through another type, the compiler infers the requirement `T: 'x`. Explicit annotations remain allowed. They are still needed to control the default lifetime of trait objects, and they keep existing code compiling.

## Motivation

Today this struct does not compile:

```rust
struct Ref<'a, T> {
    value: &'a T,
}
```

The compiler reports that `T` may not live long enough and suggests adding `T: 'a`. The fix is mechanical:

```rust
struct Ref<'a, T: 'a> {
    value: &'a T,
}
```

The annotation carries no information the compiler did not already have. The field `&'a T` is only well-formed if `T: 'a`, and the compiler reads the field to produce the error. The programmer adds the bound because the compiler asks for it, and every reader of the struct then has to skip over it.

The annotation also spreads. A struct that contains a `Ref<'a, T>` needs `T: 'a` too, and so does a struct that contains that struct:

```rust
struct Wrapper<'a, T: 'a> {
    inner: Ref<'a, T>,
}

struct Outer<'a, 'b, T: 'a, U: 'b> {
    left: Wrapper<'a, T>,
    right: &'b U,
}
```

Each of these bounds follows from the fields, and each one has to be written by hand. [TODO: author to give a measure of how often these annotations appear, for example a count of `T: 'a` bounds on structs in a sample of crates, or links to issues where users were confused by the error.]

## Guide-level explanation

You no longer need to write outlives requirements that follow from a struct's fields. This compiles:

```rust
struct Ref<'a, T> {
    value: &'a T,
}
```

The compiler infers that `Ref<'a, T>` requires `T: 'a`. The requirement still exists. Code that names `Ref<'a, T>` must still satisfy it, just as if it had been written. The only change is that you do not write it.

The inference sees through other types. This compiles too:

```rust
struct Wrapper<'a, T> {
    inner: Ref<'a, T>,
}
```

`Wrapper<'a, T>` contains a `Ref<'a, T>`, which requires `T: 'a`, so `Wrapper<'a, T>` requires `T: 'a` as well.

You may still write the bound. `struct Ref<'a, T: 'a>` remains valid and means the same thing. Writing the bound has one effect that inference does not have, which concerns trait objects and is described in the reference section.

## Reference-level explanation

### What is inferred

For each struct, the compiler computes a set of inferred outlives requirements, each of the form `T: 'x` or `'y: 'x`. It computes them from the types of the struct's fields with these rules:

1. A field of type `&'x T` or `&'x mut T` contributes `T: 'x`.
2. A field whose type is another struct, `S<...>`, contributes the requirements of `S`, explicit and inferred, with `S`'s parameters replaced by the arguments given.
3. The rules apply recursively inside a field type. A field of type `Option<&'x T>` contributes `T: 'x`.
4. A requirement that mentions a lifetime or type that is not a parameter of the struct being defined is not inferred.

The compiler infers requirements only of these two forms. It does not infer trait bounds, such as `T: Clone`. [TODO: author to state whether enums and unions are covered. The rules apply to them unchanged, and this draft assumes they are.]

### Recursive structs

Rule 2 makes the requirements of one struct depend on those of another. Structs can be mutually recursive:

```rust
struct A<'a, T> { b: Option<Box<B<'a, T>>> }
struct B<'a, T> { a: Option<Box<A<'a, T>>>, r: &'a T }
```

The compiler computes the requirements of all structs together as a fixed point. It starts with the empty set for every struct, applies the rules, and repeats until no set changes. Here the first pass gives `B` the requirement `T: 'a` from its field `r`, and the second pass gives it to `A` through `b`. Each requirement mentions only the struct's own parameters, and each struct has finitely many, so the sets can only grow to a finite limit and the iteration terminates.

### Where inferred requirements apply

Inferred requirements are used everywhere explicit ones are used when the compiler checks that a type is well-formed. A function that takes a `Ref<'a, T>` may assume `T: 'a`, as it does today when the bound is explicit. Code that names `Ref<'a, T>` with a `T` that does not outlive `'a` is rejected, as today.

### Trait object lifetime defaults

When a struct has a parameter with an explicit `T: 'a` bound, and `T` is instantiated with a trait object type written without a lifetime, such as `Ref<'a, dyn Trait>`, the trait object's lifetime defaults to `'a`. Inferred requirements do not take part in this default. Only explicitly written bounds do.

The reason is stability. If inferred requirements changed the default, then changing a private field of a struct could change the meaning of `dyn Trait` in a crate that uses the struct. Programmers who want the default from the bound keep writing the bound. [TODO: author to confirm this is the intended rule; the abstract states that explicit annotations control the default but does not say that inferred ones do not.]

## Compatibility

Code that compiles today has, on every struct, every outlives requirement that the inference rules would add. The compiler rejects the struct otherwise. Inference therefore adds no requirement that is not already present, and since trait object defaults are unchanged, it does not change the meaning of any existing program. [TODO: author to confirm there is no case where the current well-formedness check accepts a struct without a bound that the rules above would infer. If such a case exists, inference adds a new requirement to that struct, and code using it could stop compiling.]

## Drawbacks

The central cost is that the requirements of a struct are no longer visible in its definition. Today, the generics list of `Ref` shows `T: 'a`, and a reader who uses `Ref` knows the requirement without reading the fields. With inference, the requirement is still there but appears nowhere in the source. Rustdoc can show inferred requirements. [TODO: author to say whether rustdoc will display them, and how.]

The invisibility has a consequence for library authors. A struct's inferred requirements are computed from all its fields, including private ones. Suppose a public struct `Cache<'a, T>` has a private field of type `Vec<T>`. Its author later changes that field to `Vec<&'a T>`. The inferred requirement `T: 'a` appears on `Cache`, and a downstream crate that used `Cache<'a, T>` with a `T` that does not outlive `'a` stops compiling. Today the same change would not compile until the author added `T: 'a` to the definition, so the requirement would appear in the public signature and in review. Under inference, the change to a private field silently changes the public requirements. The author of a semver-sensitive library may want to keep writing the bounds for this reason. [TODO: author to decide whether a lint should warn when a public type's inferred requirements depend on private fields.]

Mixing explicit and inferred bounds raises a style question. If both forms are allowed, codebases will contain both, and a reader cannot tell from the presence of a bound whether it is there for the trait object default, for documentation, or by habit.

## Rationale and alternatives

The status quo keeps the requirements visible at the cost of mechanical annotations. The drawbacks section states what inference gives up.

[TODO: author to list the alternatives actually considered. Suggestions for the author to evaluate, not recorded alternatives:
- Infer only from fields of reference type (rule 1), not through other structs (rule 2). This keeps the inference local and avoids the fixed point, but `Wrapper` in the guide example would still need its bound written out, which removes much of the benefit.
- Keep the requirement explicit, and have the compiler offer a machine-applicable suggestion to insert it. This removes the need to work out the bound by hand without hiding it.]

## Unresolved questions

- Whether enums and unions are covered.
- Whether rustdoc displays inferred requirements.
- Whether to lint on public types whose inferred requirements depend on private fields.
- Whether to lint on explicit bounds that inference makes redundant, and if so, how the lint tells them apart from bounds written for the trait object default.

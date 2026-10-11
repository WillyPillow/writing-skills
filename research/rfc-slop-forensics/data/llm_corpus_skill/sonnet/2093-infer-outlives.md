# Rust RFC 2093: infer_outlives

## Summary

This RFC removes the need for explicit `T: 'x` annotations on structs. The compiler infers them from the fields of the struct. If the struct contains a reference to `T` with lifetime `'x`, directly or indirectly, the compiler infers the requirement `T: 'x`. Explicit annotations remain available. They control the default lifetime of trait objects, and they keep old code valid.

## Motivation

A reference `&'a T` is only well formed if `T` outlives `'a`: the data behind the reference must be valid for as long as the reference is. The compiler checks this when it sees a type like `&'a T`. For a struct that holds such a reference, the struct definition must therefore declare the same fact about its parameters. Today the declaration is written by hand.

```rust
struct Ref<'a, T: 'a> {
    r: &'a T,
}
```

The bound `T: 'a` adds no information for the reader. The field `r: &'a T` already implies it, and the compiler rejects the struct if the bound is missing. The annotation is a restatement that the compiler demands. [TODO: the author should confirm that the current error occurs for every struct of this form, and should quote the error message.]

The burden grows with nesting. A struct that wraps `Ref` must repeat the bound, because the compiler needs it for the wrapper to be well formed.

```rust
struct Wrapper<'a, T: 'a> {
    inner: Ref<'a, T>,
}
```

In this case the field type `Ref<'a, T>` does not contain a visible reference at all. The author of `Wrapper` has to look at the definition of `Ref` to learn that `T: 'a` is needed. If `Ref` later gains a different requirement, every wrapper breaks. This is the "indirect" case that the abstract names. [TODO: the author should supply a count of how many such annotations exist in the standard library or in a sample of crates, or an issue showing that the annotations confuse learners. None were supplied.]

The goal of the RFC is to remove this restating work: after the change, the declarations above need no bounds, and a struct is accepted whenever the bounds would be implied by its fields.

## Guide-level explanation

After the RFC, the first example is written as follows.

```rust
struct Ref<'a, T> {
    r: &'a T,
}

struct Wrapper<'a, T> {
    inner: Ref<'a, T>,
}
```

The compiler reads the field `r: &'a T` and concludes that `Ref` requires `T: 'a`. It reads the field `inner: Ref<'a, T>` and concludes that `Wrapper` requires `T: 'a`, because `Ref<'a, T>` carries that requirement. A user of `Ref<'a, X>` must show that `X: 'a`, exactly as before. Only the place where the bound is written changes.

Explicit annotations stay legal. A programmer can still write `T: 'a` on the struct. The abstract gives two reasons: a bound controls the default lifetime of trait objects, and old code needs to keep compiling.

The trait object case needs an example. In `Ref<'a, dyn Trait>`, the compiler has to choose a lifetime bound for `dyn Trait`. Its default depends on the bounds written on the struct's parameters. [TODO: the author should state the existing rule for the default and show how an explicit `T: 'a` selects it. The draft knows only that the abstract mentions this use.] If the compiler inferred a bound and used it to pick the default, a struct that previously chose one default would silently choose another. For that reason inferred bounds do not change the default, and an explicit bound is the only way to influence it. [TODO: confirm that this is the RFC's rule. It is the reading that follows from "explicit annotations remain as an option used to control trait object lifetime defaults".]

## Reference-level explanation

The inference works on the field types of a definition. For each struct, the compiler collects the requirements implied by its fields, and adds them to the struct's predicates.

1. For a field of type `&'x U` or `&'x mut U`, the compiler adds `U: 'x`.
2. For a field whose type is an application `S<args>` of another struct, the compiler adds the requirements that `S` has, with the arguments substituted.
3. For a field of any other form, the compiler adds the requirements of its components. [TODO: the author should list each form: tuples, arrays, function pointers, trait objects, projections of associated types, enums and unions.]

A requirement of the form `U: 'x` where `U` is not a bare parameter, such as `Vec<T>: 'x`, reduces to requirements on its components. [TODO: confirm.]

The second rule makes the requirements of one struct depend on those of another. Structs may refer to themselves or to each other, so the dependency has a cycle in general, and the compiler has to compute the requirements as the smallest set that satisfies all the rules. A fixed-point iteration, repeating the rules until no new requirement appears, produces this set. [TODO: the author should state the algorithm used by the implementation and whether it terminates in all cases. Termination follows if the number of parameters and lifetimes is finite and requirements are only ever added, but the draft has no proof from the author.]

Inference applies to structs. [TODO: the abstract says "structs". The author should state whether enums, unions, type aliases and traits are covered.]

Inference is local to the crate for crate-local types. For a type from another crate, the compiler needs the inferred requirements in the crate's metadata. [TODO: the author should describe how they are stored.]

## Drawbacks

The change moves a fact from the source text to the compiler. A reader who wants to know the exact requirements of a struct can no longer read them from the definition, and has to read the fields of that struct and of every struct it contains. Tools such as documentation generators need to print the inferred bounds if the bounds matter to users. [TODO: the author should say whether rustdoc shows inferred bounds.]

The change affects error messages. When a use of a struct fails because `T: 'a` does not hold, the message mentions a requirement that the user never wrote. [TODO: the author should say how the message points to the field that implies the requirement.]

A change to the fields of a struct can now change its public requirements without a visible edit to its signature. Adding a reference field to a struct adds a bound, and users whose types did not satisfy the bound fail to compile. Previously the same edit forced the author to write the bound, which made the change visible in review. [TODO: the author should say whether this is a concern for semver and what the project's position is.]

## Rationale and alternatives

The deciding reason in the abstract is that the bounds are redundant: they are fully determined by the fields, so the compiler can compute them and the programmer gains nothing from writing them.

Alternatives, labelled as suggestions for the author to evaluate:

- Keep the bounds explicit and improve the error message so that it suggests the exact bound. This keeps the requirements visible in the source. The programmer still writes redundant text.
- Infer bounds only for the direct case, a reference field in the struct itself. This avoids the fixed-point computation. It leaves the burden for wrappers.
- Introduce a syntax that asks for inference explicitly, such as a placeholder bound. This avoids the change in how definitions read, and adds syntax.

The change is not hard to reverse in one direction. Because explicit annotations remain valid, programs that spell out their bounds keep compiling. Removing inference later would break programs that rely on it.

## Prior art

[TODO: the author should cite earlier RFCs on lifetime bounds and trait object defaults, and any other language with region inference. None were supplied.]

## Unresolved questions

- The list of type forms covered by the rules above. [TODO]
- The interaction with the trait object default rule, as stated above. [TODO]
- Whether any lint should suggest removing now-redundant explicit annotations. [TODO]

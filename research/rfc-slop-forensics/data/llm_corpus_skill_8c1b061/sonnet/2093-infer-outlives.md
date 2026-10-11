# Rust RFC 2093: infer_outlives

## Summary

Remove the need to write explicit `T: 'x` annotations on structs. The compiler infers them from the fields of the struct. If the struct contains a reference to `T` with lifetime `'x`, directly or indirectly, the compiler infers the requirement `T: 'x`. Explicit annotations stay legal. They control the default lifetime of trait objects, and they keep existing code compiling.

## Motivation

Consider a struct that holds a reference to some generic value:

```rust
struct Ref<'a, T> {
    r: &'a T,
}
```

The type `&'a T` is only well formed when `T` outlives `'a`. A reference cannot live longer than the data it points to, so if `T` contained a shorter-lived borrow, `&'a T` could dangle. The compiler therefore needs the bound `T: 'a` on `Ref`. Under the current rules, the programmer must write it:

```rust
struct Ref<'a, T: 'a> {
    r: &'a T,
}
```

The annotation repeats something the compiler could work out by reading the field. The only information it adds is the bound itself, and a programmer who leaves it out gets an error that asks for it. The error message names the bound, which means the compiler already knows what the bound should be.

The cost compounds with nesting. A struct that holds another struct that holds a reference must carry the same annotation, and so does every struct above it, even though the programmer never wrote a reference at those levels:

```rust
struct Outer<'a, T: 'a> {
    inner: Ref<'a, T>,
}
```

Here `Outer` has no reference field, yet the bound is required because `Ref<'a, T>` needs it. A change to a field deep inside a type can force edits to every type that contains it.

[TODO: the material gives no counts, such as the number of such annotations in the standard library or in a sample of crates. Add one if available; do not describe the annotations as "common" without it.]

## Guide-level explanation

After this RFC, the program above is written without annotations:

```rust
struct Ref<'a, T> {
    r: &'a T,
}

struct Outer<'a, T> {
    inner: Ref<'a, T>,
}
```

The compiler reads the fields of each struct and works out which bounds the fields require. For `Ref`, the field `&'a T` requires `T: 'a`, so the compiler treats `Ref<'a, T>` as having that bound. For `Outer`, the field `Ref<'a, T>` requires, through `Ref`, the bound `T: 'a`, so `Outer` gets it too.

The rule is short. If a struct contains a reference, directly or indirectly, to a type parameter `T` with lifetime `'x`, then `T: 'x` is a requirement of that struct. Here "indirectly" means through the fields of other types, as `Outer` reaches `T` through `Ref`.

Explicit annotations remain legal. A programmer may still write `T: 'a`, and the program compiles as before. Two reasons to keep writing them are given in the abstract: the annotation controls the default lifetime bound of trait objects, and existing code uses it.

An example of the first reason. A trait object type `Box<dyn Trait>` gets a default lifetime bound that depends on the enclosing type. When a struct says `T: 'a` on a parameter, that bound feeds the default. [TODO: the abstract states that explicit annotations are "used to control trait object lifetime defaults" but gives no detail. The author should give the rule and an example. The sentence above is the writer's paraphrase of the abstract.]

## Reference-level explanation

Inference works over the definitions of structs, and the same rule applies to enums and unions. [TODO: the abstract says "structs" only. State whether enums and unions are in scope.]

For each type definition `S`, the compiler computes a set of outlives requirements `T: 'x` by this procedure.

1. For every field type, collect the requirements that make the field type well formed. For `&'x U`, this includes `U: 'x`. For a type `Q<..>` that is itself a struct with inferred requirements, include those requirements after substituting the actual arguments.
2. Add to `S` the collected requirements that mention only the parameters of `S`.
3. Repeat until no new requirements appear, since structs can refer to each other and a requirement found for one can produce a new one for another.

The final step is needed because type definitions may be recursive. [TODO: the material does not say how recursion is handled or whether the procedure terminates in all cases. The author should confirm that it does, and give the argument. Possible content: the set of possible requirements is finite for a given set of parameters.]

A requirement involving something other than a parameter of `S`, such as a concrete type, is not added to `S`. It is checked where `S` is defined. [TODO: confirm.]

### Interaction with explicit annotations

If a struct has an explicit `T: 'x` and the inference also produces it, the result is one bound. If the explicit annotation names a bound that the fields do not require, the bound stays: the compiler does not remove declared bounds. [TODO: confirm with the author.] The explicit bound then constrains the users of the struct more than needed, but that is the programmer's choice, and today's code does the same.

### Where the inferred bounds are visible

An inferred bound is part of the type's contract, even though it is not written. A user of `Ref<'a, T>` must show that `T: 'a`, as before. Documentation tools that print the signature of `Ref` need to decide whether to print the inferred bound. [TODO: ask the author whether rustdoc output is in scope.]

## Drawbacks

The bound is no longer visible in the struct definition. A reader who wants to know what `Outer` requires of `T` has to read `Ref` too. This is the cost of the change, and it applies exactly where nesting was the problem.

A second cost is an interaction between inference and later edits. Adding a reference field to a struct can add a bound to the struct, which is a change to the type's contract. In the current system, adding the field forces the programmer to write the bound, so the change is visible in the diff. After this RFC, the diff shows only the new field. [TODO: ask the author whether the authors of the RFC consider this a semver concern for library crates, and what they propose.]

## Rationale and alternatives

The deciding point in the abstract is that the information is redundant. The compiler is able to compute the bound from the fields, so requiring the programmer to write it adds effort and no information.

Alternatives and the questions a reviewer will raise:

- Keep the requirement and improve the error message into a suggestion that can be applied automatically. This lowers the cost of writing the bound, but leaves it in every definition. [TODO: ask whether this was considered and why it lost.]
- Infer bounds only for direct references, not through nested structs. This is simpler to explain and leaves the nesting cost. [TODO: ask.]
- Infer the bounds but forbid explicit annotations. This is not what the abstract proposes, since annotations stay for trait object defaults and compatibility.

Reversibility: once the compiler infers bounds, programs can depend on the inference by omitting annotations. Removing inference later would break them. Adding it is easier to undo while no code relies on it.

## Compatibility

The abstract says explicit annotations remain as a way to keep existing code working. It gives no evidence on whether any currently valid program becomes invalid. In principle, inference only adds bounds that the compiler would have demanded as errors, which suggests that valid programs are unaffected. [TODO: this is the writer's inference, not a supported claim. The author should confirm it and say how it was checked, for example by building a large set of crates.]

## Unresolved questions

- Whether enums and unions are included.
- How recursive definitions are handled.
- Whether documentation shows inferred bounds.
- The exact interaction with trait object defaults.

## Future possibilities

The same reasoning applies to other bounds that follow from field types, such as bounds on type parameters used in associated types. This RFC does not propose them. [TODO: ask the author whether the RFC wants to name any follow-up.]

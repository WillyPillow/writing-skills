# RFC 2093: Infer Outlives

- Feature Name: `infer_outlives`
- Start Date: 2017-08-03
- Tracking Issue: (to be assigned)
- Status: Proposed

## Summary

This RFC removes the need for explicit `T: 'x` annotations on struct definitions. Instead, the compiler infers the outlives requirements from the fields of the struct. If a struct contains a reference, directly or indirectly, to a type `T` with lifetime `'x`, the compiler infers that `T: 'x` is a requirement of the struct. Explicit annotations remain available. They continue to control the default lifetime of trait objects, and they are kept for backwards compatibility.

## Motivation

When a struct holds a reference, the reference has a lifetime, and the types it refers to must live at least as long as that lifetime. This requirement is written in Rust as an outlives bound, `T: 'a`, meaning that every reference to `T` inside the struct is valid for `'a`. Today the programmer must write these bounds explicitly on the struct definition whenever a generic parameter appears under a reference.

Consider a struct that holds a reference to a value of a generic type. Without the bound, the struct is rejected, because the compiler cannot prove that the reference is valid. The programmer must add `T: 'a` to the struct's where clause. This is correct but repetitive, since the bound follows directly from the fields. The compiler already knows the fields, so the annotation records information it could compute itself.

The burden is most noticeable in code with several generic parameters and several lifetimes. Each combination that appears under a reference needs its own bound, and the list of bounds grows quickly. Newcomers find the requirement puzzling, because the reason for the bound is not visible in the definition, and the error message about a missing bound does not always make the cause clear.

Inferring the bounds from the fields removes this repetition. It also aligns the struct case with function signatures, where the compiler already infers many lifetime relationships from the types of the arguments and the body.

## Guide-level explanation

Under the proposal, a struct that holds a reference to a generic value needs no explicit bound:

```rust
struct Borrowed<'a, T> {
    value: &'a T,
}
```

The compiler infers that `T: 'a`, because the field is a reference with lifetime `'a` to a value of type `T`. The programmer does not need to write the bound. The struct can be used as before, and its validity is checked in the same way.

The inference applies transitively. If a field holds a type that itself contains a reference to `T` with lifetime `'a`, the bound is inferred for that field as well. A programmer who wants the bound to be visible in the documentation may still write it explicitly, and the explicit form is accepted.

Trait objects are the exception. The default lifetime of a trait object depends on the bounds of the struct that contains it, and changing how those bounds are written can change the meaning of the trait object. For this reason, explicit annotations remain the way to control that default, and the proposal does not alter the rule for trait objects.

## Reference-level explanation

For each struct definition, the compiler collects the outlives requirements implied by its fields. A field of type `&'x U` implies the requirement `U: 'x`. A field whose type is a path to another type with its own outlives requirements implies the requirements of that type, after substitution of the generic arguments. The collection proceeds recursively through the field types until no further requirements arise.

The inferred requirements are added to the struct's predicates. They are checked at each use of the struct in the same way as explicit requirements. An explicit requirement that is also inferred is accepted without error, and the explicit form is retained in the struct's signature.

Requirements are inferred only from the fields. They are not inferred from methods or from implementations, which continue to need explicit bounds where the programmer requires them. This keeps the inference confined to a well-defined place.

Trait objects inside a struct field use the default lifetime rule. The rule that determines the default depends on the bounds written on the containing struct. The proposal preserves that rule by using only explicit bounds when computing the default, so that the meaning of existing trait object types does not change. Inferred bounds do not affect the default.

The change is backwards compatible in the sense that every struct accepted before remains accepted, with the same meaning. Structs that were rejected because of a missing bound may now be accepted, and that is the intended effect.

## Drawbacks

Inference makes some definitions harder to read, since the bound that governs a field no longer appears in the source. A reader must know the rule to understand why a struct is valid. The distinction between inferred and explicit bounds, and the exception for trait objects, adds conceptual weight. There is also a risk that a change to a field type silently changes the requirements of the struct, which may surprise a programmer who did not expect the bound to be needed.

## Rationale and alternatives

The main alternative is to leave the rule as it is, which is simple to state but repetitive in practice. Another alternative is to infer the bounds but to require the programmer to write them in the documentation. This was considered, but it does not reduce the burden in code and it does not give any benefit beyond the documentation.

A third alternative is to infer bounds for functions and methods as well. This is a larger change, and it is not needed to solve the problem of struct definitions, so it is left for separate consideration. The proposal focuses on structs because the information is fully determined by the fields and the design of the inference is straightforward.

## Prior art

Compilers for other languages with lifetimes or region-like systems often infer the constraints needed for aggregate types from their contents. The general experience is that inference of this kind reduces boilerplate and that the main source of confusion is the lack of visibility. The proposal responds to that by keeping explicit annotations available and by keeping the trait object rule unchanged.

## Unresolved questions

- How the inferred bounds should be presented in documentation tools, so that readers can see the requirements that the compiler has inferred.
- Whether the inference should extend to enums, where the fields belong to variants, and how it should interact with variants that have different requirements.
- The exact diagnostic to give when an inferred bound fails, so that the programmer can understand which field caused the failure.

## Future possibilities

A future proposal could extend inference to function signatures or to implementations, once the rules for structs have been tested. Tooling could show inferred bounds on hover or in generated documentation, which would address the visibility concern. The rule for trait object defaults could also be reconsidered in a later edition, if the explicit annotations that control it are found to be a burden in common code.

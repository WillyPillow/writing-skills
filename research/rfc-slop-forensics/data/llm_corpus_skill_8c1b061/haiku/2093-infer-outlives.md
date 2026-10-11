# RFC 2093: `infer_outlives`

- Status: [TODO: status and tracking issue link]

## Summary

This RFC removes the need for explicit `T: 'x` annotations on structs. The compiler infers them from the fields of the struct. If a struct contains a reference to `T` with lifetime `'x`, directly or indirectly, the compiler infers the requirement `T: 'x`. Explicit annotations remain available. They still control trait object lifetime defaults, and they are kept for backward compatibility.

## Motivation

A struct that holds a reference to a generic parameter must state that the parameter outlives the reference. Without that statement, the compiler rejects the struct. The annotation is required even when it is the only thing the programmer could have written, because the fields already determine it.

The obstacle is that the annotation repeats information the fields already contain. A programmer who adds a reference field must also update the struct's generic bounds, and a reader must check that the two agree. [TODO: give an example from the material of a struct that needs the annotation today, and the error the compiler reports without it.]

## Design

The compiler examines the fields of each struct. Where a field contains a reference to `T` with lifetime `'x`, directly or through another type, the compiler adds `T: 'x` as a requirement of the struct. The programmer no longer writes the bound in the common case.

The force behind this rule is the repetition described above. The rule uses the fields because they are the only place where the relationship between `T` and `'x` is actually expressed. A rule based on something else, such as the position of the struct in a module, would not reflect the data the struct holds.

Explicit annotations are not removed. The RFC keeps them for two reasons. They still control the default lifetime of trait objects, which the inferred bound does not change. They also keep existing code compiling, which is the backward-compatibility reason stated in the RFC. [TODO: state how the authors weigh keeping the annotation syntax against a future removal, and whether any deprecation is planned.]

## Alternatives considered

[TODO: list the alternatives the authors considered. The material does not record them. Do not present any alternative as considered until the authors confirm it and give the reason it lost. Candidates to check include inferring bounds for function signatures and requiring the annotation for public structs only.]

## Cost accepted

Readers can no longer see the bound on the struct definition. To know that `T: 'x` holds, a reader must look at the fields. Error messages must also explain an inferred requirement that the programmer never wrote. [TODO: state how the compiler reports a violated inferred bound, and whether the authors have checked the wording of such errors.]

## Reversibility

Inferred bounds are part of the type's behavior, and users of a public struct can depend on them. Changing the inference rule later would change which programs compile. Because explicit annotations are kept, a user who wants the bound written down can still write it, which limits the cost of any later change. [TODO: confirm that an inferred bound on a public type can be made explicit without changing the type's meaning.]

## Rollout

[TODO: describe how the change reaches users, and whether it is accepted by default or gated behind a feature flag. State how existing code that writes the annotations is affected.]

## Open questions

- [TODO: decide whether the inferred bounds should be shown in documentation.]
- [TODO: state whether the inference covers references nested inside other generic types, and what the authors checked to support that.]

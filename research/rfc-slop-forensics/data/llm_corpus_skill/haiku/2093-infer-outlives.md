# Rust RFC 2093: infer_outlives

Document type: Rust language/tooling RFC
Status: [TODO: RFC status and tracking details]

## Context and scope

A struct that holds a reference to a generic type parameter needs a bound that says the type parameter outlives the reference's lifetime. The current rule requires that bound to be written explicitly, as a `T: 'x` annotation on the struct.

This RFC removes the need for those annotations. The compiler infers them from the struct's fields.

[TODO: An example of the current rule, from the author, showing a struct that must carry the annotation.]

## Motivation

[TODO: A concrete case in which the explicit annotation is a burden for the people who write or read the code. The material states the goal of removing annotations but not a case that needs it.]

## Goals

- Infer `T: 'x` requirements on structs from their fields. [TODO: A checkable criterion, such as a set of structs that must compile without annotations and with the same meaning as before.]
- Keep explicit annotations available. The RFC says they "remain as an option" for two purposes: controlling trait object lifetime defaults, and backward compatibility.

## Design

The inference rule is this. If a struct contains a reference, directly or indirectly, to `T` with lifetime `'x`, the compiler infers the requirement `T: 'x`.

[TODO: One example of a direct case and one of an indirect case, with the inferred requirement written out for each.]

Explicit annotations stay as an option for the two purposes named above. [TODO: Whether the inference changes the default lifetimes of trait objects, or leaves them to the explicit annotations, and how the author knows.]

## Compatibility

The RFC says explicit annotations remain available "for backwards compatibility." This is a compatibility claim: existing code is not affected. The claim needs support from the author's material.

[TODO: The evidence that existing code keeps compiling and keeps its meaning. The author should say which code was checked, and how. The material does not say.]

## Alternatives considered

[TODO: Alternatives the author evaluated. The material gives none. Do not present any as considered until the author confirms it.]

## Cost

[TODO: What is lost when the bound is inferred rather than written. A reader of a struct declaration can no longer see the bound there. The author should say whether this matters and how the cost is weighed.]

## Reversibility

Once released, inferred bounds become part of how user code type checks. [TODO: Whether the author regards the inference rule as expensive to change after release.]

## Rollout

[TODO: How the change ships, whether it is gated, and what a user would do if the inferred bound caused a problem.]

## Open questions

- [TODO: How the inference interacts with trait object lifetime defaults, which the RFC says explicit annotations still control.]

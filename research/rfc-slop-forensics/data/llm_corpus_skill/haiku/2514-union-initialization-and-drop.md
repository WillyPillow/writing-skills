# Rust RFC 2514: union_initialization_and_drop

Document type: Rust language/tooling RFC
Status: [TODO: RFC status and tracking details]

## Context and scope

A union holds one of its fields at a time. Rust does not allow a union to have a field whose type requires drop glue, which is the code run automatically when a variable goes out of scope to drop the variable and, recursively, all its fields. A union may still implement `Drop` itself.

This RFC specifies three things: when a program may move out of a union field, when the union's `drop` is called, and how `DerefMut` is restricted when unions are involved.

## Motivation

[TODO: A concrete program that needs a union with its own `Drop` implementation, or that needs to move out of a union field, and what it cannot do today. The material states the rules but not the need for them.]

## Goals

- A specified rule for when a program may move out of a union field. [TODO: The exact condition.]
- A specified rule for when the union's `drop` is called. [TODO: The exact condition.]
- No undesired implicit calls of `drop`. The RFC restricts `DerefMut` for this purpose.

## Non-goals

[TODO: Anything a reader might expect from union support that this RFC deliberately leaves out. The author has not stated any.]

## Design

The RFC makes three decisions. Each is listed here with what is known and what is missing.

1. **Moving out of a union field.** [TODO: The condition under which a move is allowed. The material says the rule is specified but does not give it.]
2. **Calling the union's `drop`.** [TODO: The condition under which the union's own `drop` runs.]
3. **Restricting `DerefMut`.** The RFC restricts the use of `DerefMut` when unions are involved, "to avoid undesired implicit calls of drop." [TODO: The implicit drop call this restriction prevents, with a short example, and the exact form of the restriction.]

The third decision has the least support in the material. A reviewer who disputes it needs to know which implicit drop call is meant, so the author should name it.

## Alternatives considered

[TODO: Alternatives the author evaluated, in their strongest form. The material gives none. Do not record any as considered without the author's account.]

## Cost

[TODO: What the `DerefMut` restriction prevents users from doing with unions, and whether the author accepts that cost.]

## Reversibility

The rules for moving out of union fields and for calling the union's `drop` change what programs may do with unions. Programs that depend on them are hard to break later. [TODO: The author's view on how difficult it would be to relax or tighten these rules after stabilization.]

## Rollout

[TODO: The feature gate, if any, and the path to stabilization.]

## Open questions

- [TODO: Questions the author wants reviewers to address.]

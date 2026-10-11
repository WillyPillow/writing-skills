# RFC 2514: `union_initialization_and_drop`

- Status: [TODO: status and tracking issue link]

## Summary

Unions cannot have fields whose types require drop glue. Drop glue is the code that runs automatically when a variable goes out of scope, which recursively drops the variable and all of its fields. A union may still implement `Drop` itself. This RFC specifies when a value may be moved out of a union field, and when the union's `drop` is called. It also restricts the use of `DerefMut` when unions are involved, so that drop is not called implicitly.

## Motivation

A union stores one of several fields at a time, and the compiler does not know which field is active. Drop glue relies on knowing what a value contains, so the compiler cannot run it on a union field safely in general. This is why unions reject fields with drop glue.

The union itself is different. A type can implement `Drop` without giving the compiler any knowledge of the active field, because the author of the union writes the code that runs. That leaves a gap: unions that need cleanup have no defined rule for when it runs, and moving a value out of a field has no defined rule either. [TODO: give a concrete use case from the material that needs a union with a cleanup step, or a field value moved out.]

## Design

The RFC defines two rules.

The first rule says when a value may be moved out of a union field. [TODO: state the exact condition. The material does not record it, so the rule is not stated here.]

The second rule says when the union's `drop` is called. [TODO: state whether `drop` runs at the end of the union's scope, and what the implementation must check first.]

The third rule restricts `DerefMut` for unions. The reason is that a mutable dereference can cause an implicit call to drop, and the RFC aims to avoid such calls. Dereferencing a union through `DerefMut` could therefore run cleanup code the programmer did not write at that point. [TODO: state which operations the restriction covers, and whether shared `Deref` is affected.]

## The central tension

The hardest part of this design is the tension between two goals. Unions are useful because they let a program reuse storage and move values out of fields directly. Drop is useful because it guarantees cleanup. Permitting moves and drops without restriction would make cleanup run at points the programmer cannot see, and restricting them too much would make unions with cleanup unusable. The three rules are the authors' attempt to strike a balance. [TODO: the authors should state which of the two goals they weighted more heavily, and show where each rule gives up some of the other.]

## Alternatives considered

[TODO: list the alternatives the authors considered, for example forbidding `impl Drop` on unions altogether or forbidding moves out of fields. The material does not record them, so they are not presented here as considered or rejected. Each one needs the reason it lost.]

## Cost accepted

Programs that want the convenience of `DerefMut` on a union must use another form of access. [TODO: state what the restriction makes harder in practice, and give an example of code that now needs to change.]

## Reversibility

Relaxing a restriction later is less disruptive than tightening one. The rules here are the stricter option for drop and mutation, so relaxing them later is the expected path if experience shows they are too strict. [TODO: confirm this is the authors' view, and state which part is expected to be stabilized first.]

## Open questions

- [TODO: decide whether the rules apply to unions nested inside other types.]
- [TODO: state how the rules interact with the drop behavior of fields that do not require drop glue.]

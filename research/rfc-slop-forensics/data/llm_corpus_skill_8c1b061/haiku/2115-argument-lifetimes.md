# Rust RFC 2115: argument_lifetimes

## Summary

This RFC removes the need to declare lifetime parameters separately in `fn` definitions and `impl` headers. A function signature binds every lifetime it mentions that is not already bound. The RFC also adds a lint against leaving lifetime parameters off structs such as `Ref` or `Iter`, and it asks users to write explicit lifetimes in those cases. The lint is paired with other changes that make explicit lifetimes less cumbersome. [TODO: state the other changes by name.]

## Motivation

A function that takes a reference must currently declare the lifetime of that reference before it can use it. Each declaration adds a name the reader must track and a line the writer must type. [TODO: give one function from the motivating code, in its current form, and state how many lifetime declarations it needs.]

The obstacle is that the declaration is often redundant. In most signatures the lifetime appears only in the parameter and return types, and nothing else in the function depends on its name. The declaration repeats information the signature already carries. [TODO: count how many signatures in a named corpus are affected, with the corpus and the method, before stating a proportion.]

Structs present the opposite problem. A struct with a lifetime parameter can be used without writing the parameter, which hides the fact that a borrow is involved. A reader of `Iter` cannot see from the type that it borrows from another value. [TODO: give an example of a bug or confusion this causes, if one is known.]

## Guide-Level Explanation

Under the proposed rule, a signature mentions a lifetime and that lifetime is bound by the signature itself. The writer does not declare it. The compiler infers that the lifetime belongs to the function.

[TODO: give the before and after code for the two forms named in the summary. The exact examples are not in the material, and the RFC should show them rather than describe them.]

For `impl` headers, the proposal asks that lifetimes bound there have names longer than one character. The reason is to keep them visually separate from lifetimes bound inside functions. [TODO: give an example that shows the confusion the rule prevents.]

To make the borrow visible in a struct, the writer writes `'_` to say that the lifetime is elided on purpose. Leaving the parameter off entirely becomes deprecated. [TODO: give the exact deprecation wording and the edition or release in which it takes effect. The material is incomplete here.]

## Reference-Level Explanation

[TODO: specify the binding rule precisely. State how the compiler decides which lifetimes a signature binds, and what happens when a lifetime appears in an argument and in the return type.]

[TODO: specify the lint. State its name, the default level, and the exact set of types it applies to.]

[TODO: specify how the `'_` form is parsed and checked, and whether it is allowed in every position where an explicit lifetime is allowed.]

## Drawbacks

The change makes some signatures harder to read in isolation, since the reader must work out the lifetime's scope from the signature alone. [TODO: state whether the author has seen this in practice, and in which code.]

The deprecation affects every struct that is used without a lifetime parameter. [TODO: estimate how many such uses exist in the ecosystem, with the source of the estimate. Do not state a count without it.]

## Rationale and Alternatives

The central choice is to let the signature carry the binding, so the writer does not repeat it. The reason is that the redundant declaration is the main cost the RFC targets. [TODO: state whether the author considered keeping the declaration and only relaxing the rules for impl headers, and why that option lost.]

The lint on structs follows from the same logic. A borrow should be visible at the point of use. [TODO: state the deciding reason for the lint over a documentation-only change.]

## Unresolved Questions

[TODO: list the open questions. Candidates include the exact lint name, whether the one-character rule needs an exception, and the ecosystem impact of the deprecation.]

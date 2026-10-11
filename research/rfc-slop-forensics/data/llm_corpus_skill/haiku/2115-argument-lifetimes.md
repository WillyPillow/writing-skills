# Rust RFC 2115: argument_lifetimes

Status: [TODO: RFC status, tracking issue and date]

## Summary

This RFC removes the need to bind lifetime parameters separately in `fn` definitions and `impl` headers. Under the current design, a programmer declares each lifetime before using it. Under this RFC, a signature binds any lifetime it mentions that is not already bound. [TODO: confirm the current behavior against the before and after code. The abstract says "instead of writing ... you can write ...", but the code samples are missing from the material.]

The abstract's examples are cut off at that point. [TODO: the before and after code. A reader cannot see the change without it, so this is the first gap to fill.]

## Motivation

[TODO: the goal or obstacle. The abstract states the change but not the friction it removes. Describe the difficulty programmers hit, with an example from the author's material, and say how often it occurs if the author has data.]

## The changes

The abstract lists three changes and mentions two further points.

1. A signature binds any lifetime it mentions that is not already bound.
2. A style lint checks that lifetimes bound in `impl` headers have names longer than one character. The lint is meant to reduce confusion with lifetimes bound within functions.
3. A programmer may write `'_` to elide a lifetime explicitly.

The abstract also says that leaving off a lifetime entirely is deprecated, but the sentence is cut off before saying which positions it covers. [TODO: the rest of this sentence and the full scope of the deprecation.]

## Lints

The abstract describes two lints. The first concerns the naming of lifetimes in `impl` headers. The second is a lint against leaving off lifetime parameters in structs such as `Ref` and `Iter`. This lint nudges programmers toward explicit lifetimes. The abstract says the other improvements make explicit lifetimes ergonomic. [TODO: name those improvements and link the RFCs or issues that propose them. The abstract refers to them without naming them, so the claim that they make explicit lifetimes ergonomic is not yet supported.]

The abstract also says there are "some additional, less important lints." [TODO: each of these lints, named and described.]

## Design decisions

### Naming in impl headers

The force behind the naming lint is the confusion between lifetimes of different scopes, which the abstract calls potential confusion. [TODO: examples or reports of that confusion. "Potential" does not say how often it happens, and the lint's value depends on that frequency.]

The lint flags single-character lifetime names in `impl` headers. [TODO: how many existing `impl` headers use such names, measured on a named body of code, with the method of the count stated.]

[TODO: the options considered for the naming rule, including keeping the current rule, and the reason each one lost.]

Cost: programs with single-character names in `impl` headers receive a lint they did not receive before. [TODO: whether this lint is a warning or an error, and whether the author judges the cost acceptable.]

### Structs without explicit lifetimes

The force is that a struct such as `Ref` or `Iter` may be used with its lifetime left implicit, which hides the borrow from the reader. [TODO: a case from the material where the hidden lifetime caused a problem, if one exists. If none does, say so and narrow the motivation to the readability argument the abstract makes.]

The lint does not forbid the implicit form. It nudges programmers toward the explicit one, and the cost is a lint on code that compiles today. [TODO: the consequence for code that the author wants to keep as written.]

## The central tension

The abstract's aim is to make lifetime binding simpler while still steering programmers toward explicit lifetimes where the reader needs them. These two aims pull against each other. [TODO: which aim the author judges more important, and the evidence for that judgment.]

## Drawbacks

[TODO: the drawbacks of the change, each in its strongest form. The material does not contain a drawbacks section.]

## Alternatives

[TODO: the alternatives considered, including keeping the current design, each with the reason it lost. The material does not say whether any alternative was considered.]

## Unresolved questions

[TODO: the open points the author has not settled, including the timeline of the deprecation, the list of additional lints, and the scope of the elision change.]

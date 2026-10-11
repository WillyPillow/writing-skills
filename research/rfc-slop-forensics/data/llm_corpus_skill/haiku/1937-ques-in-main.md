# Allow `?` in `main`, `#[test]` functions and doctests

Status: proposed. [TODO: author to confirm the status field and the RFC number format used by the venue.]

## Summary

This RFC proposes allowing the `?` operator in three places: the `main` function, functions marked `#[test]`, and doctests. To make this possible, the return type of these functions is generalized from `()` to a new trait, provisionally called `Termination`. The standard library implements the trait for a set of types, and applications may implement it for their own types. The compiler adds no special behavior to function signatures.

## Motivation

A function that uses `?` must return a type that the `?` operator can convert into. Today `main`, test functions and doctests return `()`. A function that wants to propagate an error therefore has to match on the error and handle it inline, even when the natural response is to return it. [TODO: give an example of a current `main` that handles an error inline. The author should choose a representative case from the users who need this.]

The force is the cost of that workaround. Programs that do one thing and then exit can be written more directly if `?` works at the top level. [TODO: state how many programs, crates or test suites the author has seen that use the workaround, if the author has such a count.]

The obstacle is in the return type. Changing the return type of `main` is the only way to allow `?` there, because the operator needs a return type to convert into. [TODO: author to confirm that no other mechanism was considered for this obstacle, or name the one that was.]

## Guide-level explanation

A function such as `main` may now return a `Result` whose error type is chosen by the program. [TODO: insert the short example of `main` returning `Result<(), ErrorT>` with `?` in its body. The author should write the example and check that it compiles against the final design.]

The program must state its return type. The compiler does not insert a return type for it. [TODO: confirm this. The abstract says that the programmer must write the return type, and the example should match.]

Test functions and doctests follow the same rule. A doctest that wants to use `?` needs a hidden function head around the example, at least initially. [TODO: show the hidden head and the way the rendered documentation displays the example, so that readers see what the hidden part looks like.]

## Reference-level design

The trait `Termination` is the central piece. [TODO: state the trait's method or methods, their signatures, and what the runtime does with the value returned from each function.] The standard library implements `Termination` for a set of types. The abstract says that this set is only partly decided. [TODO: author to list the types for which the impl is settled, and to mark the rest as open. Do not list types that are not decided.]

Applications may implement `Termination` for their own types. [TODO: state any restriction the author intends, such as orphan rules or the requirement that the implementing type be a particular kind of value.]

The compiler does not add any special behavior to function signatures. The programmer must write `-> Result<(), ErrorT>`, or the equivalent type, explicitly. This is a deliberate statement about where the change lives, and the design depends on it. [TODO: author to say what would change if the compiler did add behavior, and why that was not proposed.]

## Deployment

The abstract refers to a deployment plan, in which the default doctest template is adjusted so that the hidden function head is no longer needed. The material supplied does not contain the plan. [TODO: author to supply the deployment plan. Until it is supplied, the claim that the adjustment will happen is not supported and must not be presented as settled.]

Until that plan is in effect, doctests that use `?` need the hidden head. [TODO: state how many doctests in the ecosystem would be affected during this period, if the author has the figure.]

## Why the design takes this shape

The central tension is between making `?` available where it is useful and keeping the language's signatures unchanged. The abstract resolves it in favor of keeping the signatures unchanged. Signatures are visible to every reader of a program, and a compiler rule that rewrote them would make the actual signature harder to see. The text supports this reading, but the author should state the reasoning in their own words. [TODO: author to confirm.]

The choice of a trait over a fixed set of allowed return types is another point that needs a reason. The abstract says that the trait lets applications provide their own implementations. [TODO: author to state the cost of the trait approach and the alternatives that were considered, such as a closed enum of return types.]

## Alternatives

The drafter has not verified that any alternative was considered. The following are suggestions for the author to evaluate.

One alternative is to add a closed set of allowed return types, with no trait. This would be simpler to specify, but applications could not extend it. [TODO: author to state whether this was considered.]

A second alternative is to have the compiler rewrite the signature of `main` when `?` appears in its body. The abstract rules this out, since it says that no magic is added to function signatures. [TODO: author to explain why the rule was adopted, in their own words.]

## Drawbacks

The trait is an addition to the public surface of the standard library, and it cannot easily be changed once stabilized. [TODO: author to state the cost of getting the trait wrong.] Doctests that need the hidden head add a line that readers must recognize. [TODO: state whether this is a cost the author accepts for the transition period.]

## Migration and compatibility

Existing `main` functions that return `()` continue to compile. [TODO: this is a compatibility claim. Support it with the rules for how the existing return type is treated by the trait, or narrow it to what is checked.]

## Open questions

The set of standard library types that implement `Termination` is open. The deployment plan for doctests is open, because the material supplied does not contain it. Whether a test function may return a value that the test runner treats differently from `()` is open. [TODO: author to state the intended behavior for test runners.]

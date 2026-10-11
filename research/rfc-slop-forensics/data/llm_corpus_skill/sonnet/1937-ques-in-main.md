# Allow `?` in `main`, `#[test]` functions and doctests

## Summary

This RFC allows the `?` operator in `main`, in `#[test]` functions and in doctests. To make that possible, the return type of these functions generalizes from `()` to a new trait, provisionally called `Termination`. The standard library implements `Termination` for a set of types, and applications can implement it for their own.

The compiler gets no special rule for function signatures. A programmer who wants `?` in `main` or in a test writes `-> Result<(), ErrorT>` (or another suitable type) explicitly. A doctest that wants `?` initially needs a hidden function head. The deployment plan below changes the default doctest template so that this is unnecessary in most cases.

[TODO: the supplied abstract is cut off and refers to a list of implementing types that is "partially TBD" and to a deployment plan. The author must supply both. Details below are marked where they are inferred.]

## Context

The `?` operator returns early from the enclosing function when it meets an error. It works only in functions whose return type can carry that error. `main` returns `()`, so `?` does not compile there. A program that calls fallible functions from `main` has to match or unwrap each result by hand.

The same restriction applies to `#[test]` functions and to doctests, since a doctest body is placed inside a function that returns `()`. [TODO: confirm the doctest wrapping mechanism and describe the current "hidden function head" that users write today.]

[TODO: add one concrete example, such as a short program that reads a file in `main`. Show the version that compiles today next to the version this RFC enables. A reviewer can then compare the two directly.]

## Goals and non-goals

Goals:

1. `?` compiles in `main`, `#[test]` functions and doctests when the function declares a suitable return type.
2. An application can choose the type that `main` returns, and can add support for its own types.
3. Doctests that use `?` need no hidden function head after the deployment plan completes. [TODO: say how a reviewer would check this goal.]

Non-goals:

1. The compiler does not rewrite signatures. A function declared to return `()` stays that way, and `?` in it stays an error. The abstract says "there is no magic added to function signatures in rustc".
2. This RFC does not define exit-code conventions beyond those that follow from the trait. [TODO: confirm. A reader may expect a rule for how an error becomes a process exit status, and the author must say whether this RFC supplies one.]

## Design

### The `Termination` trait

The trait describes what a `main`, test or doctest function may return and how the runtime turns that value into the outcome of the program. The name is provisional.

[TODO: give the trait definition, the method or methods it has, and what each returns. The abstract does not say. A sketch for the author to replace:

```rust
// Suggestion only.
trait Termination {
    fn report(self) -> i32;
}
```
]

The runtime calls the trait on whatever `main` returns. For `()`, the behavior stays what it is today, so existing programs are unaffected. [TODO: this compatibility claim is inferred from the generalization of `()`. The author should confirm that the implementation for `()` reproduces current behavior exactly.]

### Which types implement it

The standard library implements `Termination` for a set of types. The abstract says this set is "partially TBD" and refers to a list. [TODO: insert the list. At minimum the author should state whether `()` and a `Result` with a suitable error type are included.]

Applications can add implementations for their own types. This choice gives programs control over how a failure is reported, at the cost of making the trait part of the public contract. [TODO: confirm the rationale, and say whether the orphan rules limit which types a program can cover.]

### Why a trait

The force is that `?` needs a return type that can hold an error, and `main` must still be able to say how the process ends. A trait does both without a signature rule in the compiler.

Options:

- *A compiler rule that accepts `Result` in `main` only.* This would be smaller, and it would hard-code one type. [TODO: suggestion for the author to evaluate, not recorded history.]
- *A compiler rewrite that wraps the body of `main` implicitly.* The abstract excludes this ("no magic"). [TODO: the author should give the reason, such as that signatures should say what they mean.]
- *A trait, as proposed.* It keeps the signature honest and lets libraries extend the set.

[TODO: state the deciding reason in the author's words.]

### Tests and doctests

A `#[test]` function that returns a type implementing `Termination` passes when the value signals success and fails when it signals failure. [TODO: define what the test harness does with a failure value, for example whether it prints the error, and which trait method it uses.]

For doctests, the initial state requires a hidden head such as a wrapper function declaration. After the deployment plan, the default template wraps the example in a function with a suitable return type, so examples that use `?` work without the wrapper. [TODO: describe the template change and what happens to existing doctests whose last expression is not `Ok(())`.]

## Deployment plan

[TODO: the abstract refers to this plan but the supplied material has no content for it. A suggested outline for the author to correct:

1. Add the trait and the standard implementations behind a feature gate.
2. Support `main` and `#[test]` first.
3. Change the default doctest template in a later step, after feedback.

Give the criteria for each step.]

## Drawbacks

1. The runtime entry point now involves a trait, so a reader who looks at `main` must know the trait exists to understand the exit status. [TODO]
2. Doctests have two forms during the transition: the hidden head and the new default. [TODO]
3. The trait is public, so the author takes on its long-term compatibility. [TODO: say which parts are costly to change.]

## Failure behavior

[TODO: state what a user sees when `main` returns an error: the printed text, the exit status, and whether destructors run. Do the same for a failing test and a failing doctest.]

## Unresolved questions

1. What is the final name of the trait? [TODO]
2. Which standard types implement it? [TODO: the list is incomplete.]
3. How do embedded targets without a process exit behave? [TODO: the author should confirm whether this applies.]
4. Should the error be printed with the debug format or the display format? [TODO]

## Evidence

The supplied material has no prototype, measurement or incident. The case for the change currently rests on the example in the Context section, which the author still has to supply. [TODO]

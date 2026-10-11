# Rust RFC 1937: ques_in_main

## Summary

Allow the `?` operator in `main`, in `#[test]` functions and in doctests. To make this possible, generalize the return type of these functions from `()` to a new trait, provisionally called `Termination`. The standard library implements the trait for a set of types, partly to be decided (see the list below). Applications can implement it for their own types.

The compiler gets no special handling of function signatures. To use `?` in `main` or in a test, the author writes `-> Result<(), ErrorT>` or whatever type they want. Initially a doctest that wants `?` also needs a hidden function head. Eventually (see the deployment plan below) the default doctest template changes so that this is rarely needed.

## Motivation

The `?` operator returns early from the enclosing function when it meets an error. It works in a function whose return type can hold that error. `main` returns `()`, so it cannot hold one, and `?` does not compile inside it.

A short program, a script, or an example in documentation often does several fallible operations in a row: open a file, parse a value, print a result. Without `?` in `main`, the author has two options. One is to move the body into a second function that returns `Result`, call it from `main`, and handle the error there. The other is to call `unwrap()` or `expect()` on each step. The first adds boilerplate that every program repeats. The second turns every error into a panic with a message that was not written for the user.

Examples suffer more than programs. A doctest is compiled as the body of a generated `main`. An example that shows a fallible call has to either hide a wrapper function from the reader or show `unwrap()` on every line, and a reader copying the example into real code takes the `unwrap()` with them. [TODO: ask the author for a concrete doctest from the standard library that shows this, so the claim has an instance.]

Tests have the same shape. A test that exercises a fallible function wants to propagate the error, and a failed test should report the error rather than a panic message from `unwrap`.

The goal, then, is that a reader who writes `?` in the body of `main`, a test or a doctest gets the behavior they expect, without a language rule that treats these functions as special.

## Detailed design

### The trait

A new trait, provisionally `Termination`, describes what a program does when `main` returns. It has one method that produces the process exit code from `self`. [TODO: confirm the method name, its signature, and whether it can print.]

The compiler's entry point calls the user's `main`, takes the returned value, and calls the trait method on it. This replaces the current rule that `main` must return `()`. A `main` that returns `()` keeps working, because the standard library implements the trait for `()`.

### Implementations in the standard library

The standard library provides implementations for:

- `()`, which yields a successful exit code.
- `Result<T, E>` where `T` is itself `Termination` and `E` can be printed, which yields a failure exit code on `Err` after printing the error. [TODO: confirm the bounds on `E`; the abstract says only that the set is partly to be decided.]
- [TODO: the abstract says "a set of types partially TBD (see list below)" but no list is supplied. Fill in the remaining types, and say for each one what exit code it produces.]

The unresolved parts of the list are repeated in the Unresolved questions section.

### What the compiler does not do

The compiler adds no rule that rewrites a function body or inserts a wrapper. A function that uses `?` has to declare a return type that can carry the error. Because the signature is visible, a reader of `main` can see where the error goes.

This is the reason for the "no magic" constraint. A rule such as "`main` implicitly returns `Result` if the body contains `?`" would make the same code mean different things depending on a body's content, and would break the reader's ability to see a function's type from its signature.

### Tests

A `#[test]` function that returns a type implementing `Termination` passes if the exit code from the trait is a success, and fails otherwise. A test that returns `Err` fails and the error is printed.

[TODO: ask the author how the test harness interprets the value, since the harness runs in-process and `Termination` was described in terms of exit codes.]

### Doctests

Doctests are different. The generated wrapper around a doctest body declares `fn main()`. A doctest author can write the wrapper themselves to get `?`, using a hidden line:

```rust
/// # fn main() -> Result<(), std::num::ParseIntError> {
/// let n: i32 = "5".parse()?;
/// # Ok(())
/// # }
```

The hidden lines start with `#` and do not appear in the rendered documentation. This works without any change to rustdoc. It is a workaround, and the deployment plan removes the need for it.

### Deployment plan

1. Add the trait and the implementations. Make `main` and test functions accept any type that implements the trait.
2. Document the hidden-head pattern for doctests.
3. Change the default doctest template to wrap the body in a function that returns a `Result` with a boxed error, so that `?` works without a hidden head. [TODO: ask the author for the exact template and for the condition under which rustdoc switches to it.]

Step 3 changes how existing doctests compile, and the RFC does not say how doctests that already define `main` are treated. [TODO: ask the author.]

## Drawbacks

The trait becomes part of the language's surface. Every future change to what a program may return from `main` has to be compatible with it.

A `Result<(), E>` returned from `main` prints the error and exits. The format of that output is now behavior that users depend on. [TODO: ask the author whether the output format is specified here or left to the implementation.]

The doctest workaround adds hidden lines, and a reader who copies the rendered documentation does not see them. The example then fails to compile in the reader's own project. This persists until step 3.

## Alternatives

**Keep `main` returning `()`.** Authors continue to wrap or unwrap. The drawback is the boilerplate described in the motivation section.

**Special-case `main` in the compiler.** The compiler could treat a `main` that uses `?` as if it returned a `Result`. The RFC rejects this on the grounds of the signature rule above. [TODO: ask the author whether this was discussed under that reasoning or another.]

**Use a closed set of return types instead of a trait.** `main` could be allowed to return `()` or `Result<(), E>` and nothing else. That is simpler to explain. It prevents applications from defining their own exit behavior, such as mapping specific errors to specific codes. [TODO: ask the author.]

## Unresolved questions

- The final name of the trait.
- The full list of standard library implementations and the exit code of each.
- Whether the trait method can be called by user code, or is reserved for the entry point.
- How the test harness reports a non-unit return value.
- The timing of the doctest template change in the deployment plan.

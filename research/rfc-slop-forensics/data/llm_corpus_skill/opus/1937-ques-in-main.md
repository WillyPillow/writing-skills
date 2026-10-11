# RFC 1937: `?` in `main`

## Summary

Allow the `?` operator in `main`, in `#[test]` functions and in doctests. The return type of these functions is generalized from `()` to any type that implements a new trait, provisionally named `Termination`. The standard library implements the trait for a small set of types, and applications can implement it for their own.

## Motivation

The `?` operator returns early from a function whose return type can hold the error. `main` returns `()`, which cannot hold one, so `?` does not compile there:

```rust
fn main() {
    let text = std::fs::read_to_string("config.toml")?; // error
    println!("{}", text);
}
```

The same holds in `#[test]` functions, which also return `()`, and in doctests, whose code is wrapped in a generated `fn main()`.

Users work around this in one of two ways. They replace `?` with `.unwrap()`, which panics with a message aimed at the developer. Or they move the body into a helper that returns `Result` and match on it in `main`. The first teaches a habit that is wrong in library code. The second is boilerplate that every program repeats. [TODO: if there is evidence of how often these patterns appear, for example in documentation examples or user forum questions, cite it here.]

The cost lands hardest on documentation. An example that shows how to use a fallible API either uses `unwrap`, which readers then copy, or hides a wrapper function, which readers cannot see. Doctests are where most users first see error handling, so the examples teach the wrong lesson at the point of first contact.

The goal is that the shortest correct program is also the one that handles errors with `?`.

## Guide-level explanation

`main` can now return a `Result`:

```rust
use std::error::Error;

fn main() -> Result<(), Box<dyn Error>> {
    let text = std::fs::read_to_string("config.toml")?;
    println!("{}", text);
    Ok(())
}
```

If `main` returns `Ok(())`, the program exits with a success status. If it returns `Err(e)`, the program prints `e` to standard error and exits with a failure status.

A `#[test]` function can do the same. A test that returns `Err` fails, and the error is printed in the test report.

Nothing about the signature is inferred. A function that wants to use `?` must declare a return type such as `Result<(), E>`. A `main` that returns `()` behaves as before.

## Reference-level explanation

### The `Termination` trait

The return type of `main` and of test functions must implement:

```rust
pub trait Termination {
    fn report(self) -> i32;
}
```

`report` performs any output the value calls for and returns the process exit status. The runtime calls it on the value `main` returns, then exits with that status. The test harness calls it on the value a test returns and treats a nonzero status as a failure.

The decision to use a trait rather than a fixed list of permitted return types is driven by applications with their own conventions. A command-line tool may need distinct exit statuses for distinct errors. Through the trait, such a tool defines its own return type and maps each error to a status. A fixed list in the compiler would require a language change for each new convention.

### Implementations in the standard library

The set of types is partially open. The proposed starting set is:

1. `()`, which reports success. This keeps every existing `main` valid.
2. `Result<T, E>` where `T: Termination` and `E: Debug`. `Ok(t)` reports whatever `t` reports. `Err(e)` prints `e` with `Debug` formatting to standard error and reports failure.
3. `!`, for a `main` that never returns.

[TODO: decide whether `E` should be bound by `Debug` or by `Display`. `Debug` is implemented by more error types, including `Box<dyn Error>`; `Display` usually produces a message better suited to an end user. This choice determines what users see when a program fails, so the author should state which wins and why.]

[TODO: decide whether an `ExitCode` type, or an implementation for integer types, belongs in the initial set. The abstract leaves this list open.]

[TODO: specify the exit status for failure. The value 1 is a common convention on Unix-like systems; confirm the value and whether it differs by platform.]

### `#[test]` functions

The test harness accepts any test function whose return type implements `Termination`. `#[should_panic]` remains defined in terms of panics. [TODO: decide whether a test marked `#[should_panic]` that returns `Err` without panicking passes or fails.]

### Doctests

A doctest's code is wrapped by rustdoc in a generated `fn main()`. That function returns `()`, so `?` does not work in it. Initially, a doctest that wants `?` must write its own hidden function head:

```rust
/// # fn main() -> Result<(), Box<dyn std::error::Error>> {
/// let n: i32 = "42".parse()?;
/// # Ok(())
/// # }
```

This is visible boilerplate for documentation authors, though hidden from readers.

## Deployment plan

The rollout has three steps, ordered so that each one can ship and be evaluated before the next.

1. Add `Termination` and its standard implementations, unstable, and allow `main` and test functions to return it. Users can try the feature on nightly.
2. Stabilize the return types for `main` and tests, with the trait itself still unstable, so that applications use the standard implementations before custom implementations are allowed.
3. Change rustdoc's default wrapper so that the generated `main` returns a `Result`, which makes the hidden function head unnecessary in most doctests. [TODO: specify the condition under which rustdoc uses the new wrapper, for example when the doctest contains `?`, and how it chooses the error type.]

[TODO: confirm whether stabilizing the trait for user implementations is part of this RFC or left to a later one.]

## Drawbacks

Printing the error with `Debug` formatting produces output aimed at developers, such as quoted strings and struct syntax. End users of command-line tools will see that output unless the application defines its own return type. This is the cost of choosing a bound that most error types already satisfy.

The feature makes `main` look like ordinary error handling, but the behavior on error is fixed by std. An application that wants different output must define its own type, which takes more code than writing a helper function and matching on its result.

The doctest change in step 3 changes how existing doctests are compiled. [TODO: check whether any existing doctest would compile differently under the new wrapper, for example one that already defines `main`.]

## Rationale and alternatives

The deciding constraint is that no existing program may change meaning. Generalizing the return type through a trait implemented for `()` keeps every current `main` valid without special cases in the compiler.

[TODO: the following are suggestions for the author to evaluate, not options known to have been considered.]

1. Let the compiler infer a `Result` return type for `main` whenever its body contains `?`. This removes the signature change, but adds inference that no other function has, which the abstract rules out ("no magic added to function signatures").
2. Provide a macro that wraps `main` in a helper. This needs no language change, but every program must import it, and doctests would still need it.
3. Keep the status quo and document the helper-function pattern.

## Unresolved questions

1. The name of the trait.
2. `Debug` versus `Display` for printing errors.
3. The full initial set of implementations.
4. The exit status values on each platform.

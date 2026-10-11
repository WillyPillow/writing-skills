# Rust RFC 1937: `ques_in_main`

- Feature Name: `ques_in_main`
- Start Date: 2024-01-22
- Status: Proposed

## Summary

This RFC allows the `?` operator to be used inside `main`, inside functions annotated with `#[test]`, and inside documentation tests. To make this work, the return type of these entry points is generalized from `()` to a new trait, provisionally named `Termination`. The standard library implements `Termination` for a set of types, and applications may implement it for their own types. The compiler does not add any special rules to function signatures. A program that wants to use `?` in `main` must declare a return type such as `Result<(), E>` itself. The RFC also describes how the runtime turns a returned value into an exit status.

## Motivation

Many small Rust programs begin with a `main` function that calls fallible operations. Without `?`, the author must either unwrap every result, which panics on error and produces a poor message, or write a `match` expression for each call. Both options are clumsy. Other functions in the same program can use `?` to propagate errors to their callers, but `main` has no caller to receive them. The gap is especially visible in tests and examples. Documentation examples are often the first code a new user reads, and a doctest that cannot use `?` teaches an unidiomatic style.

The change also addresses a consistency concern. Rust already allows functions to return `Result` in most positions. Allowing the same return type at the entry point removes an arbitrary exception from the language.

## Guide-level explanation

A program may declare its `main` function to return a `Result`:

```rust
use std::error::Error;
use std::fs;

fn main() -> Result<(), Box<dyn Error>> {
    let text = fs::read_to_string("config.toml")?;
    println!("loaded {} bytes", text.len());
    Ok(())
}
```

If `main` returns an `Err` value, the program prints a description of the error to standard error and exits with a nonzero status. If it returns `Ok(())`, the program exits with status zero. The same rule applies to `#[test]` functions, which report a failure when they return an error, and to doctests, which fail when the block returns an error.

The behavior is governed by the `Termination` trait. Its single method converts the value into an exit code. The standard library provides implementations for `()`, for `Result<T, E>` where `T: Termination` and `E: Debug`, and for a small set of other types that are listed in the reference section. Application authors may implement `Termination` for their own types if they want a custom exit code.

Doctests need a small hidden wrapper in the current design. A doctest that uses `?` must include a hidden function head that returns `Result`. The RFC proposes that the default doctest template adopt this wrapper automatically once the change is stable, so that most examples require no extra annotation.

## Reference-level explanation

The `Termination` trait is defined in the standard library with one required method, `report`, which returns an exit code. The trait is implemented for `()`, which yields success, and for `!`, which is never reached. For `Result<T, E>`, the implementation calls `report` on the `Ok` value when the result is successful, and when the result is an error, it writes the `Debug` representation of the error to standard error and returns a failure code.

The compiler is changed in two places. First, the check on the return type of `main` is relaxed so that any type implementing `Termination` is accepted. Second, the code that generates the process entry point calls `report` on the returned value and passes the resulting code to the operating system. No change is made to function signatures in general, and the compiler does not insert implicit conversions.

For `#[test]`, the test harness inspects the return value. An `Err` marks the test as failed and prints the error. For doctests, the generated template is adjusted so that the body is placed inside a function whose return type matches the user's annotation, if one is present.

The list of standard library implementations is intentionally conservative. Types whose exit behavior is not obvious, such as those that carry platform-specific meaning, are deferred until there is experience with the basic design.

## Drawbacks

The change introduces a new trait that users must understand when they write custom entry points. Some programs will print error messages in a format the author did not intend, because the default output uses `Debug` formatting. The change also adds a small amount of complexity to the compiler and to the test harness.

## Rationale and alternatives

One alternative is to have the compiler rewrite `main` automatically whenever it contains `?`. This was rejected because it hides the return type from the reader and creates surprising interactions with code that already declares a return type. Making the return type explicit keeps the signature honest.

A second alternative is to continue to require users to write an explicit `match` or a helper function. This keeps the language small, but it leaves an obvious and frequent pattern without a good answer.

A third alternative is to restrict the change to `main` and leave tests and doctests unchanged. This was considered simpler, but the test and documentation cases are as common as the entry point case, and a partial change would leave an inconsistent model.

## Prior art

Several languages let the entry point of a program return a value that determines the exit status. The `Termination` design follows this general pattern while keeping the set of accepted types open through a trait rather than a fixed list.

## Unresolved questions

- Which standard library types should implement `Termination` at the time of stabilization?
- Should the `Debug` output of a returned error be replaced with `Display` output, which is often friendlier to end users?
- How should the hidden doctest wrapper be presented in rendered documentation so that readers are not confused by it?

## Deployment plan

The trait and its basic implementations are stabilized first, followed by the change to `main` and `#[test]`. The doctest template change is deployed as a separate step after the rest has been in use for a period, so that documentation tooling can adjust without a sudden break. Each step is accompanied by a diagnostic that explains how to declare a suitable return type when `?` is used in a context that does not support it.

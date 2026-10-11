- Feature Name: `termination_trait` / `ques_in_main`
- Start Date: 2017-02-22
- RFC PR: rust-lang/rfcs#1937
- Rust Issue: (none yet)

# Summary

Allow the `?` operator to be used in `main`, in `#[test]` functions, and in doctests. To make this possible, the return type of these functions is generalized from `()` to any type implementing a new trait, provisionally named `Termination`. The standard library implements `Termination` for a small set of types, including `()` and `Result<(), E>` where `E: Debug`. Applications may implement it for their own types.

No new syntax and no special signature rewriting is involved. A program that wants to use `?` in `main` writes `fn main() -> Result<(), MyError>` explicitly. Doctests initially need an explicit hidden function header to do the same; a later step will change the default doctest wrapper so that most doctests get this for free.

# Motivation

The `?` operator has made error propagation in Rust concise, but it only works inside functions whose return type supports it. `main` returns `()`, so the moment a beginner copies a line like

```rust
let file = File::open("config.toml")?;
```

into `main`, they get an error about `?` being used in a function that returns `()`. The usual workaround is to move the body into a `run()` function returning `Result` and write a small `main` that matches on it and prints an error:

```rust
fn run() -> Result<(), Box<dyn Error>> {
    let file = File::open("config.toml")?;
    // ...
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("error: {}", e);
        std::process::exit(1);
    }
}
```

This pattern is so common that it appears in nearly every command-line tool and in many crates' example directories. It is boilerplate, and it hurts the most in the places where we most want Rust to look approachable: tutorials, examples, and documentation.

Doctests make the situation worse. Rustdoc wraps each example in an implicit `fn main() { ... }`, so examples that would naturally use `?` instead call `.unwrap()`. Readers then copy that code, and `unwrap` spreads into production code as the idiomatic way to handle errors. Documentation should model good practice, and today the tooling prevents it.

Tests have the same problem. A `#[test]` function that sets up a temporary directory, writes some files, and parses them ends up with a column of `.unwrap()` calls. Being able to write `?` and have a failure reported as a test failure is both shorter and gives better messages.

# Guide-level explanation

`main` may now return a `Result`:

```rust
use std::error::Error;
use std::fs::File;

fn main() -> Result<(), Box<dyn Error>> {
    let f = File::open("config.toml")?;
    let config = parse(f)?;
    run(config)?;
    Ok(())
}
```

If `main` returns `Ok(())`, the program exits with a success status. If it returns `Err(e)`, the error is printed to standard error using its `Debug` representation and the process exits with a failure status (on most platforms, `1`).

The same applies to tests:

```rust
#[test]
fn parses_sample() -> Result<(), ParseError> {
    let cfg = parse_str(SAMPLE)?;
    assert_eq!(cfg.name, "sample");
    Ok(())
}
```

A test that returns `Err` fails, and the error is included in the test output.

In doctests, for now, you write the wrapper yourself and hide it:

```rust
/// ```
/// # fn main() -> Result<(), std::num::ParseIntError> {
/// let n: i32 = "42".parse()?;
/// assert_eq!(n, 42);
/// # Ok(())
/// # }
/// ```
```

Nothing changes for existing programs. `fn main()` with no return type continues to work exactly as before.

# Reference-level explanation

## The `Termination` trait

A new trait is added to `std::process`:

```rust
pub trait Termination {
    /// Called by the runtime after `main` returns. Converts the value
    /// into an exit status, reporting any information it needs to.
    fn report(self) -> i32;
}
```

The return value is the process exit status. The precise signature is subject to change before stabilization (see Unresolved questions); in particular, an opaque `ExitCode` type may replace the raw `i32`.

## Required impls

libstd provides:

- `impl Termination for ()` — returns the platform success code.
- `impl Termination for !` — never called, since `main` never returns.
- `impl<T: Termination, E: Debug> Termination for Result<T, E>` — on `Ok(t)`, delegates to `t.report()`; on `Err(e)`, prints `Error: {e:?}` to standard error and returns the platform failure code.

Further impls, such as one for `bool` or for an `ExitCode` newtype, are left open and can be added later without breaking changes.

## Changes to `main`

The entry point `main` is required to have the signature `fn main() -> T` for some `T: Termination`. The compiler-generated start shim calls `main()`, then calls `Termination::report` on the result and uses the returned value as the exit status. Because `()` implements `Termination`, every existing program continues to typecheck.

There is deliberately no rewriting of the user's signature: rustc does not infer a return type for `main` or insert `Ok(())`. What you write is what you get.

## Changes to `#[test]`

A `#[test]` function may return any `T: Termination`. The test harness calls `report` and treats a nonzero result as a failure. `#[should_panic]` tests continue to require `()`, since mixing the two failure modes is confusing.

## Doctests and the deployment plan

Rustdoc currently wraps a doctest's body in `fn main() { ... }` if the body does not already define `main`. The plan proceeds in stages:

1. Stabilize `Termination` support in `main` and `#[test]`. Doctests that want `?` write an explicit hidden `main` returning `Result`.
2. Change rustdoc's default wrapper to `fn main() -> Result<(), impl Debug> { <body> ; Ok(()) }` when the body uses `?` and would not otherwise typecheck. Doing this robustly requires care, so it is a separate step.
3. Update the standard library's documentation to use `?` in place of `unwrap` where appropriate.

# Drawbacks

- Printing errors with `Debug` is not always what users want; for user-facing tools, `Display` is usually better. Programs that care will continue to write their own error handling in `main`, which is fine, but the default output may look rough.
- The exit code mapping is platform-dependent and the trait exposes a raw integer, which does not map cleanly onto every target (for instance, platforms without process exit codes).
- Adding a trait bound to `main` makes the entry point slightly less "obvious" when reading compiler error messages about it.

# Rationale and alternatives

**Special-case `?` in `main`.** We could make `?` in `main` call `exit(1)` on error without changing the return type. This is magic, does not generalize to tests, and makes `?` behave differently depending on the enclosing function.

**Allow only `Result<(), E: Error>`.** Restricting `main` to a fixed set of return types would avoid a new trait, but would prevent applications from defining their own exit-status conventions, and would be hard to extend later.

**Use `Display` instead of `Debug`.** `Box<dyn Error>` implements both, but many error types only implement `Debug`. Requiring `Display` would exclude common cases such as `std::io::Error` wrapped in user enums that only derive `Debug`.

# Unresolved questions

- The name `Termination` and the exact signature of `report`.
- Whether to introduce an `ExitCode` type in place of `i32`.
- The precise heuristic rustdoc uses to decide whether to apply the `Result`-returning wrapper.
- The full list of standard impls beyond `()`, `!`, and `Result`.

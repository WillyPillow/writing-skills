# RFC: `?` in `main`, tests, and doctests

- Feature Name: `ques_in_main`
- Start Date: 2017-02-22
- RFC PR: rust-lang/rfcs#1937
- Rust Issue: rust-lang/rust#43301

## Summary

Allow the `?` operator to be used in `main`, and in `#[test]` functions and doctests. To make this possible, the return type of these functions is generalized from `()` to a new trait, provisionally called `Termination`. libstd implements this trait for a set of types partially TBD (see the list below); applications can provide impls themselves if they want.

There is no magic added to function signatures in rustc. If you want to use `?` in either `main` or a `#[test]` function you have to write `-> Result<(), ErrorT>` (or whatever) yourself. Initially, it will also be necessary to write a hidden function head for any doctest that wants to use `?`, but eventually the default doctest template will be adjusted to make this unnecessary in most cases.

## Motivation

Right now, `?` can only be used in functions that return `Result` or `Option` (or, with some friction, a handful of other types). This is a problem for the most common entry points of a Rust program. The function `main` must return `()`, and so must every `#[test]` function. Consequently, example code, which is overwhelmingly written to look like `main` or like a test body, cannot use `?` without wrapping the interesting part in a helper function.

This hurts in three places.

First, the book, the standard library documentation, and third-party crate documentation all contain examples that perform fallible operations. Because the doctest harness wraps examples in `fn main() { ... }`, authors must either call `.unwrap()` everywhere, which teaches the wrong habit, or add a hidden `fn try_main() -> Result<(), Box<Error>>` and a hidden `fn main() { try_main().unwrap() }`. The latter is noisy and obscures the code under demonstration.

Second, small command-line programs are written the same way. A program that opens a file and parses it has to either match on every error, unwrap, or introduce a `run` function. The conventional `fn main() { if let Err(e) = run() { eprintln!("{}", e); std::process::exit(1); } }` is repeated across the ecosystem, which is a hint that the language is missing a facility.

Third, tests that exercise fallible APIs suffer from the same problem. A test that sets up a temporary directory, writes a file, and reads it back must unwrap at every step. A failing unwrap yields a panic message that points at the unwrap, not at the real cause. Returning `Err(e)` from a test gives a better report and lets the author use `?`.

All three situations are served by one change: let the entry point return something other than `()`.

## Detailed design

### The `Termination` trait

A new trait is added to libstd:

```rust
pub trait Termination {
    /// Called by the runtime when the entry point returns.
    /// The result is used as the process exit code.
    fn report(self) -> i32;
}
```

The runtime shim that calls the user's `main` is changed from calling a function returning `()` to calling a function returning `T: Termination`, then passing the value of `report()` to the platform's process exit routine.

The signature of `lang_start` is generalized accordingly. The compiler continues to require that `main` be a non-generic function taking no arguments, but it now accepts any return type that implements `Termination`. The check happens in the type checker as an ordinary trait obligation, so no new special cases are needed in rustc other than the existing check that `main` has a valid shape.

### Implementations

The standard library provides the following impls:

```rust
impl Termination for () {
    fn report(self) -> i32 { 0 }
}

impl Termination for ! {
    fn report(self) -> i32 { self }
}

impl<T: Termination, E: Debug> Termination for Result<T, E> {
    fn report(self) -> i32 {
        match self {
            Ok(val) => val.report(),
            Err(err) => {
                eprintln!("Error: {:?}", err);
                1
            }
        }
    }
}
```

The bound `E: Debug` is chosen over `E: Display` because `Debug` is implemented for essentially all error types, and `Box<Error>` has a useful `Debug` impl. Using `Debug` also avoids the need for a blanket bound that excludes types implementing only `Debug`. A later RFC could specialize this for `Display`.

Impls for `bool` and for the integer types are left for the unresolved-questions section. The authors of this RFC do not wish to commit to a specific convention for mapping them to exit codes without further discussion.

User crates can provide their own impls, which allows, for example, a framework to define an application result type with richer exit behavior.

### Tests

The test harness is updated so that a `#[test]` function may return any type implementing `Termination`. A test passes if the value's `report()` is zero and fails otherwise. For a `Result`, the `Err` is printed as part of the failure output, as with a panic message. `#[should_panic]` continues to work as before; combining it with a non-unit return type is allowed but the return value is discarded when the panic occurs.

### Doctests

Rustdoc wraps each example in a `fn main() { ... }` unless the example already contains one. For examples that want to use `?`, the author can write a hidden `main` header:

```rust
/// ```
/// # fn main() -> Result<(), std::io::Error> {
/// let data = std::fs::read_to_string("Cargo.toml")?;
/// # Ok(())
/// # }
/// ```
```

This works immediately, with no changes to rustdoc, because a user-written `main` is already honored. Once the feature is stable, the default template can be adjusted so that, if the example's last expression appears to be `Ok(())`, or if the example uses `?` at the top level, the wrapping function is given the return type `Result<(), Box<dyn std::error::Error>>`. The details of this heuristic are deferred to a follow-up change, and the decision is intentionally independent from the trait.

### Deployment plan

1. Land the `Termination` trait as unstable, along with the runtime shim changes and the test harness updates.
2. Stabilize the trait, the impls for `()` and `Result`, and the permission for `main` and tests to return `T: Termination`.
3. Update the book and standard library docs to use `?` in examples with the explicit hidden header.
4. After one release cycle, change the default doctest template as described above.

## How We Teach This

The Book's chapter on error handling would gain a short section showing `fn main() -> Result<(), Box<dyn Error>>`. This is the most natural place to introduce the idea that the entry point has a return type like any other function.

Existing Rust programmers will recognize the idea from other languages that allow `main` to return an integer, and from `Result`-returning entry points in languages such as Swift and Kotlin. We should be careful to explain that returning `Err` produces a non-zero exit code and prints the error with `Debug` formatting to standard error, not `Display`.

## Drawbacks

Using `Debug` to print the error means that messages from `Box<Error>` look like `Error: Os { code: 2, kind: NotFound, message: "No such file or directory" }`, which is less friendly than the `Display` output most users want to see. This is a real regression in polish compared to a hand-written handler, and some will keep writing that handler.

The trait also becomes part of the standard library's stable API surface and, because the runtime calls it, its exact shape is hard to change later.

Finally, making `main` generic over its return type adds a small amount of complexity to the compiler's entry-point check and to anything that assumes `main` returns `()`, such as tooling that synthesizes a call to it.

## Alternatives

**Special-case `Result<(), E>` in rustc.** This would avoid a public trait but would be inflexible and could not be extended by user crates.

**Magic rewriting of `main`.** Another design silently wraps `main` bodies containing `?` and infers the return type. This was rejected because it makes function signatures lie, and because inference of the error type is not generally possible.

**A `try`-block based approach.** Wrapping the body in a `try` block would give a local `?` scope, but it does not solve the exit code problem or the doctest and test cases, and `try` blocks are a separate, larger feature.

## Unresolved questions

- Should `Termination` have impls for `bool`, `u8`, `i32`, and `ExitCode`-like wrappers? What should they report?
- Should the error be printed with `Display` when available, using specialization?
- Is `report` the right method name, and should it take `self` or `&self`?
- Should the trait be named `Termination`, `Main`, or `Exit`?

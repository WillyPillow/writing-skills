# RFC 1937: `?` in `main`

## Summary

Allow the `?` operator in `main`, in `#[test]` functions and in doctests. To do this, generalize the return type of these functions from `()` to any type that implements a new trait, provisionally called `Termination`. The standard library implements `Termination` for a set of types listed below, and applications can implement it for their own types.

rustc adds nothing to function signatures. A program that wants `?` in `main` or in a test writes the return type itself, for example `-> Result<(), MyError>`. Doctests at first need a hidden function header to use `?`. A later step of the deployment plan changes the default doctest template so that most doctests do not need one.

## Motivation

The `?` operator returns early from a function whose return type can represent the error. `main` returns `()`, which cannot, so `?` does not compile in `main`. The same holds for `#[test]` functions, and for doctests, which rustdoc wraps in an `fn main()`.

Programs work around this in two ways. They call `.unwrap()` or `.expect()` on every fallible call in `main`, which panics with a backtrace-style message on error. Or they move the body of `main` into a helper that returns `Result`, and write a `main` that calls the helper, prints the error and calls `std::process::exit`:

```rust
fn run() -> Result<(), Box<dyn Error>> {
    let config = read_config()?;
    serve(config)?;
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("error: {}", e);
        std::process::exit(1);
    }
}
```

The helper is boilerplate that every command-line program writes slightly differently. Doctests are worse off. Examples in documentation are where readers learn idiomatic error handling, and the examples there use `.unwrap()` because `?` does not compile. Readers then copy `.unwrap()` into their own code. [TODO: cite examples from the standard library or popular crates where documentation uses `unwrap` only because of this restriction, if the author has them.]

## Guide-level explanation

`main` may now return a `Result`:

```rust
fn main() -> Result<(), io::Error> {
    let mut file = File::open("config.toml")?;
    let mut text = String::new();
    file.read_to_string(&mut text)?;
    Ok(())
}
```

If `main` returns `Ok(())`, the program exits with a success status. If it returns `Err(e)`, the runtime prints `e` to standard error and exits with a failure status. The exact output format is described below.

A `#[test]` function may return a `Result` in the same way. A test that returns `Err` fails, and the test harness reports the error.

```rust
#[test]
fn parses_config() -> Result<(), ParseError> {
    let cfg = Config::parse("port = 80")?;
    assert_eq!(cfg.port, 80);
    Ok(())
}
```

In a doctest, the author writes a hidden `main` with a `Result` return type:

```rust
/// ```
/// # fn main() -> Result<(), std::num::ParseIntError> {
/// let n: i32 = "42".parse()?;
/// # Ok(())
/// # }
/// ```
```

Functions that return `()` keep working unchanged.

## Reference-level explanation

### The `Termination` trait

```rust
pub trait Termination {
    fn report(self) -> i32;
}
```

The runtime calls `report` on the value returned from `main`, and passes the result to the platform's process exit. `report` may print to standard error before returning. [TODO: decide whether the return type is `i32` or a dedicated `ExitCode` type. An `i32` is simple but lets programs return values that some platforms truncate or reinterpret.]

The trait lives in `std::process`. It is unstable at first, so applications can use the impls from `std` on stable Rust before they can write their own. [TODO: confirm whether user impls are allowed on stable from the start, as the summary suggests, or gated.]

### Implementations in `std`

The set of types is partly undecided. The proposed initial set is:

1. `()`, which reports success. This keeps every existing `main` valid.
2. `Result<T, E>` where `T: Termination` and `E: Debug`. `Ok(t)` reports whatever `t` reports. `Err(e)` prints `e` and reports failure.
3. `!`, the never type, for a `main` that never returns. [TODO: confirm, since `!` is not yet a stable type.]

[TODO: decide whether `bool`, `i32`, `ExitCode` or `Option<T>` are in the initial set.]

The bound on `E` is the most consequential choice in this list. `Debug` is implemented by nearly every error type, including `Box<dyn Error>` and `io::Error`, so most programs can use `?` without writing an impl. But `Debug` output is meant for programmers, and for some types it is less readable than `Display` output. Requiring `Display` would give better messages but would exclude error types that only derive `Debug`. [TODO: record which bound the author chose and why. Note that this choice is hard to reverse: tightening the bound later breaks programs that relied on it.]

The failure status is the platform's conventional failure code: `EXIT_FAILURE` from C, which is 1 on common platforms. [TODO: confirm.]

### `main`

The compiler checks that the return type of `main` implements `Termination`, instead of checking that it is `()`. The generated entry point calls `main`, then calls `report` on its value, then exits with the code. No other change to `main` is made.

### Tests

The test harness checks that each `#[test]` function's return type implements `Termination`. A test passes when `report` returns the success code and fails otherwise. `#[should_panic]` tests keep their existing behavior, and a `#[should_panic]` test that returns `Err` without panicking fails. [TODO: confirm the interaction with `#[should_panic]`.]

### Doctests

rustdoc wraps a doctest that has no `fn main` in `fn main() { ... }`. Until the template changes, doctests that use `?` must supply their own hidden `main`, as in the guide example.

## Deployment plan

1. Add `Termination` as an unstable trait, with impls for `()` and `Result`. Accept `main` and `#[test]` functions whose return type implements it, behind a feature gate.
2. Stabilize the return-type change for `main` and `#[test]` once the error output format is settled.
3. Change the default doctest template so that a doctest without its own `main` is wrapped in a function returning `Result<(), E>` for a suitable `E`, with `Ok(())` appended. Doctests that already compile keep compiling. [TODO: decide the error type for the template. `Box<dyn Error>` is a candidate, but type inference for `?` may need it named explicitly, and this needs testing on existing doctests.]
4. Stabilize `Termination` for user impls.

[TODO: give target releases for each step, if known.]

## Drawbacks

The output format for an error returned from `main` becomes part of the user-facing behavior of every program that uses this feature. Programs that want a specific format, such as a single line with a program name prefix, still need their own handling. The feature removes boilerplate for programs that accept the default format and does nothing for the rest.

Allowing `main` to return several types adds a rule that new users have to learn, and compiler errors for a `main` with an unsupported return type need to name `Termination` in a way that makes sense to someone who has not seen it.

## Alternatives

[TODO: record which alternatives were considered and why each was rejected. None of the following is presented as having been evaluated.]

[TODO: Was having rustc rewrite `main`'s signature automatically when the body uses `?` considered? The summary rules this out ("no magic"), but the reason should be stated.]

[TODO: Was a fixed `Result<(), Box<dyn Error>>` return type, without a trait, considered?]

[TODO: Was a library macro that generates the `run`/`main` pair considered as a smaller step?]

## Unresolved questions

The trait name, the return type of `report`, the `Debug` versus `Display` bound and the doctest template's error type are all open.

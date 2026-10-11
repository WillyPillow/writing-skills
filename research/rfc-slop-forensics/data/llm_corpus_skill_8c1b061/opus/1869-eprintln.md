# RFC 1869: eprintln

- Feature name: `eprintln`
- Start date: [TODO: date]
- RFC PR: [TODO: link]
- Rust issue: [TODO: link]

## Summary

Add two macros to the standard library, `eprint!` and `eprintln!`. They behave exactly like `print!` and `println!`, except that they write to standard error instead of standard output. Like the other standard macros, they are available in every module without an import. An [implementation][] already exists.

[implementation]: [TODO: link to the implementation]

## Motivation

Command-line programs separate their output into two streams. Standard output carries the program's result, the data that a pipeline passes to the next command. Standard error carries diagnostics: progress, warnings and error messages. A user who runs

```text
$ mytool input.txt > result.txt
```

expects `result.txt` to hold only the result, and expects any error to appear on the terminal. A program that prints its errors with `println!` breaks both expectations. The error goes into the file, and the user sees nothing.

Rust makes the wrong choice the easy one. Printing to standard output takes one line:

```rust
println!("processed {} records", n);
```

Printing the same message to standard error takes an import and a call whose result must be handled:

```rust
use std::io::Write;

writeln!(std::io::stderr(), "error: cannot open {}", path).unwrap();
```

The import is needed because `writeln!` calls the `write_fmt` method of the `Write` trait, and trait methods are only callable when the trait is in scope. The `unwrap` is needed because `writeln!` returns an `io::Result`, and ignoring it triggers the `unused_must_use` warning. A newcomer who wants to print an error message has to learn about traits, imports and error handling to do it, while `println!` needs none of these.

[TODO: add evidence of how often Rust programs print errors to standard output, for example issues filed against crates, or examples from tutorials and documentation.]

The two-stream convention is not specific to Rust, and the standard library already provides the stream. What it lacks is the one-line form for the second stream that it provides for the first.

## Guide-level explanation

`eprintln!` takes the same arguments as `println!` and writes the formatted text, followed by a newline, to standard error:

```rust
fn main() {
    let path = std::env::args().nth(1).unwrap_or_default();
    match std::fs::read_to_string(&path) {
        Ok(text) => println!("{}", text.len()),
        Err(e) => eprintln!("error: cannot read {}: {}", path, e),
    }
}
```

`eprint!` is the same without the newline.

Use `println!` and `print!` for the program's output, and `eprintln!` and `eprint!` for messages to the person running it. When a program's output is redirected or piped, its messages still reach the terminal.

## Reference-level explanation

The macros are defined in `std` and exported with `#[macro_export]`, so they join the set of macros that are in scope in every crate that links `std`. They are not available in `no_std` crates, since `core` has no standard error stream.

The expansion mirrors that of `print!` and `println!`. Those macros call a private function in `std::io` that writes to standard output and panics if the write fails. The new macros call a parallel function that writes to standard error:

```rust
macro_rules! eprint {
    ($($arg:tt)*) => ($crate::io::_eprint(format_args!($($arg)*)));
}

macro_rules! eprintln {
    () => (eprint!("\n"));
    ($fmt:expr) => (eprint!(concat!($fmt, "\n")));
    ($fmt:expr, $($arg:tt)*) => (eprint!(concat!($fmt, "\n"), $($arg)*));
}
```

The behavior matches the existing macros in each respect that matters to callers:

1. Formatting uses `format_args!`, so the format string syntax and checks are the same.
2. If writing to standard error fails, the macro panics, as `println!` does for standard output. [TODO: confirm that panicking is the intended behavior. A program that cannot write to standard error has few other ways to report a problem, and the panic message itself goes to standard error, so the failure may be silent.]
3. Standard error is unbuffered in Rust's standard library, so each call is written immediately. `eprintln!` does not need to flush. [TODO: confirm this matches the implementation.]
4. When the test harness captures output, `print!` and `println!` output is captured per test. The new macros should be captured in the same way, so that a failing test shows its diagnostics with the rest of its output. [TODO: confirm whether the implementation captures standard error in tests, and decide whether this RFC requires it.]

## Drawbacks

The change adds two names to the set of macros in scope everywhere. A crate that defines its own macro named `eprint` or `eprintln` could be affected. [TODO: check whether a crate-local macro with the same name shadows the standard one without error, and how many crates on crates.io define such macros.]

The macros panic on a failed write. Programs that must not panic still need `writeln!` with explicit error handling. The new macros make the panicking form easier to reach, which is the same trade-off `println!` already makes.

The standard library gains two more macros to document and maintain. The implementation is a small copy of the existing `print!` path, so the cost is the extra surface, not the code.

## Rationale and alternatives

The names follow the existing pair. Adding an `e` for "error" to `print` and `println` keeps the pair next to the existing macros in the documentation and makes the relation visible. [TODO: confirm whether other names were considered and why `eprint`/`eprintln` was chosen.]

The macros are added to the standard library rather than left to a crate. A crate cannot make its macros available without an import or `#[macro_use]`, so it would not remove the gap between the two streams that this RFC describes. [TODO: confirm that this was the reason, and whether existing crates that provide such macros were considered.]

[TODO: Was an alternative of making `println!` take a stream argument, for example `println!(stderr, ...)`, considered? If so, record why separate macros were preferred.]

[TODO: Was adding a convenience function, such as a `stderr_print` method on `Stderr`, considered instead of macros? Record why it lost, if it was.]

## Prior art

Many languages provide a short form for writing to standard error. [TODO: list the examples the author wants to compare against, such as C's `fprintf(stderr, ...)` and Python's `print(..., file=sys.stderr)`, and say what each shows about the convention.]

## Unresolved questions

- Whether output from the new macros is captured by the test harness.
- Whether the macros should panic on write failure or ignore it.

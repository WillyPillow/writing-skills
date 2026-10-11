# RFC 1869: `eprintln`

- Feature Name: `eprintln`
- Start Date: [TODO: date]
- RFC PR: [TODO: link]
- Rust Issue: [TODO: link]

## Summary

Add two macros to the global prelude, `eprint!` and `eprintln!`. They behave exactly like `print!` and `println!`, except that they write to standard error instead of standard output. An implementation already exists. [TODO: link to the implementation.]

## Motivation

A command-line program has two output streams. Standard output carries the program's result, and standard error carries diagnostics: errors, warnings, progress messages. The split lets a user redirect the result to a file or a pipe and still see the diagnostics on the terminal. For example, in `tool input.txt > out.txt`, an error message written to standard output ends up in `out.txt`, where the user does not see it and where it corrupts the result.

Rust makes the wrong stream easier to use. Writing a line to standard output takes one macro:

```rust
println!("processed {} files", n);
```

Writing the same line to standard error takes an import and a decision about the result of the write:

```rust
use std::io::Write;

writeln!(std::io::stderr(), "error: cannot open {}", path).unwrap();
```

The `use std::io::Write;` line is needed because `writeln!` calls the `write_fmt` method of that trait. Without the import, the error message the compiler gives concerns the trait method, not the stream. The `.unwrap()` is needed because `writeln!` returns a `Result`, and ignoring it triggers the `unused_must_use` warning.

The correct form costs more than the incorrect one, which invites programs to print errors with `println!`, to standard output. [TODO: author to give examples, such as crates or documentation that print errors with `println!`, or issues where users asked how to print to standard error.]

The `print!` family has a second advantage beyond length: its behavior on failure is already decided. `println!` panics if the write fails. A programmer who writes `writeln!(stderr(), ...)` has to choose between `.unwrap()`, `.expect(...)`, `let _ =`, and `?` at every call site, so the choice can differ from one call site to the next. `eprintln!` makes the same choice that `println!` makes.

## Guide-level explanation

Use `eprintln!` to write a line to standard error, the stream for messages to the user that are not part of the program's output:

```rust
fn main() {
    let path = "input.txt";
    match std::fs::read_to_string(path) {
        Ok(text) => println!("{}", text.len()),
        Err(e) => eprintln!("error: cannot read {}: {}", path, e),
    }
}
```

`eprint!` writes without a trailing newline, as `print!` does. Both macros take the same format strings and arguments as `print!` and `println!`.

When to use which: `println!` for the program's result, which the user may redirect or pipe into another program; `eprintln!` for anything the user should see even when the result is redirected.

## Reference-level explanation

`eprint!` and `eprintln!` are defined in `std` and are available in every module through the prelude, as `print!` and `println!` are.

Each call:

1. Locks the standard error handle for the duration of the call, so that the output of one call is not interleaved with output from another thread.
2. Formats its arguments and writes the result to standard error. `eprintln!` then writes a newline.
3. Panics if the write fails, with a message that names standard error.

These are the same steps `print!` and `println!` follow for standard output, with the stream replaced. [TODO: check the exact panic message of `print!` and choose the matching message.]

Two differences between the streams carry over to the macros, because they are properties of the streams, not of the macros:

- Standard output in Rust is line-buffered. Standard error is not buffered, so each `eprint!` call reaches the operating system when it returns. A program that writes to both streams can therefore see its standard error output appear before standard output written earlier, if that output is still in the buffer. [TODO: confirm the buffering of both streams in the current standard library.]
- If the process's standard error is closed, or not connected to anything, the write fails and the macro panics. The same holds for `println!` and standard output.

The macros are available in `std` only. Crates using `#![no_std]` have no standard error stream and do not get them, just as they do not get `println!`.

## Drawbacks

The macros add two names to the prelude. A crate that already defines its own macro named `eprintln!` or `eprint!` is affected. [TODO: author to list crates that define such macros, if any. Also check whether a locally defined `macro_rules!` macro with the same name shadows the prelude macro, or whether the name becomes ambiguous. If ambiguity is possible, this is a breaking change for those crates, and the RFC must list them or explain why they are not affected.]

Panicking on a failed write may be the wrong behavior for diagnostics. A program that writes an error message while handling another error may prefer to lose the message rather than panic. The macros copy the behavior of `println!` for consistency. Programs that need different behavior keep using `writeln!` and handle the `Result`. [TODO: author to confirm that panicking is the intended behavior, rather than silently ignoring the failure.]

The test harness captures the output of `print!` and `println!` in passing tests and shows it only for failing tests. Whether it also captures `eprint!` and `eprintln!` is open. If it does not, tests that use the new macros print to the terminal even when they pass, which differs from what users of `println!` in tests are used to. [TODO: author to decide whether this RFC requires capture, and check whether the existing implementation does it.]

## Rationale and alternatives

The macro names follow the existing `print!` and `println!`, with a prefix `e` for "error". A reader who knows `println!` can guess what `eprintln!` does from the name. [TODO: author to state whether other names were considered.]

The status quo is `writeln!(io::stderr(), ...)`. The motivation section gives its costs: an import, a decision about the result at each call site, and a choice the language makes harder than the wrong one.

The following alternatives are suggestions for the author to evaluate, not alternatives this RFC records as considered:

- Put the macros in `std` without adding them to the prelude, so that users import them explicitly. This avoids any conflict with crates that define their own macros of the same name. It also brings back an import, which the motivation counts as part of the cost of the status quo.
- Add a macro that takes the stream as an argument, such as `println!(to: stderr, ...)`. This keeps one macro family. It also needs a new syntax inside the macro arguments, and the common case becomes longer than `eprintln!`.
- Leave the macros to a crate. This avoids growing the standard library, but the users who most need the macros are the ones least likely to look for a crate that provides them.

## Prior art

[TODO: author to supply prior art, for example how other languages' standard libraries make writing to standard error as short as writing to standard output, with a sentence on how each relates to this proposal.]

## Unresolved questions

- Whether the test harness captures the output of the new macros.
- Whether a failed write panics or is ignored.
- Whether adding the names to the prelude breaks crates that define macros with the same names.

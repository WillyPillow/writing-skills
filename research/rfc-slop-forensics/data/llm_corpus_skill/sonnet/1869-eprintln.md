# Rust RFC 1869: eprintln

## Summary

This RFC adds two macros to the global prelude: `eprint!` and `eprintln!`. They behave exactly like `print!` and `println!`, except that they write to standard error instead of standard output. An implementation already exists. [TODO: link to the implementation.]

## Motivation

A command-line program has two output streams. Standard output carries the result that another program or a file will read. Standard error carries diagnostics, such as progress messages, warnings and failure reports. Keeping the two apart lets a user redirect the result to a file and still see the diagnostics on the terminal.

Rust's `println!` writes to standard output. A program that wants to write to standard error has to use the `std::io` API directly. The shortest form is this.

```rust
use std::io::Write;

writeln!(std::io::stderr(), "error: {}", msg).unwrap();
```

The line has four costs that `println!("error: {}", msg)` does not have.

1. It needs an import of the `Write` trait, which the macro does not need.
2. It needs a path to `stderr`, or a second import.
3. It returns a `Result`, and the compiler warns when the result is unused, so the author must handle or unwrap it.
4. It is longer, in a place where programs print often.

[TODO: the author should confirm the details above for the Rust version at the time of the RFC, in particular whether `writeln!` on `Stderr` needs `&mut` or an explicit lock, and the `unused_must_use` behaviour.]

The cost matters most for new users. The first program a learner writes prints with `println!`. The first program that reports an error to the right stream needs the more complicated form, which draws on traits and `Result` before the learner has met them. [TODO: the author should supply evidence for this claim, such as questions from forums or issues, or drop the claim. No data was supplied.]

The abstract's remedy is to give standard error the same pair of macros that standard output has.

## Guide-level explanation

`eprintln!` takes the same arguments as `println!`: a format string and values. It writes the formatted text followed by a newline to standard error. `eprint!` does the same without the newline.

```rust
fn main() {
    println!("result: 42");
    eprintln!("warning: input was empty");
}
```

When the program runs with its output redirected to a file, the file contains `result: 42` and the terminal shows the warning. The macros are in the global prelude, so a program calls them without an import, as it does with `println!`.

The names follow a convention: the letter `e` stands for error. A reader who knows `print!` can guess the rest. [TODO: the author should say whether the name was chosen over alternatives, and cite where the convention comes from. This draft cannot supply that history.]

## Reference-level explanation

`eprint!` and `eprintln!` are defined in terms of the same formatting machinery as `print!` and `println!`. The only difference is the destination.

The macros panic if the write to standard error fails. [TODO: the author should confirm. `print!` panics on a failed write to standard output, and the abstract says the new macros are "exactly the same" except for the stream, so the same behaviour follows. The draft treats this as a consequence of the abstract and has not checked the implementation.]

Locking. `print!` takes the lock on standard output for the duration of one call, so that the output of one call is not interleaved with the output of another thread. [TODO: confirm for the current implementation.] The same should hold for standard error, so that one `eprintln!` call produces one uninterrupted line. [TODO: the author should confirm that the implementation does this.]

Buffering. Standard output is typically line buffered when connected to a terminal, and standard error is unbuffered. [TODO: the author should say whether Rust's `Stderr` follows this, and whether `eprint!` without a newline appears immediately.]

Test harness. The test harness in Rust captures the output of `print!` and `println!` during a test, and shows it only if the test fails. [TODO: the author should say whether `eprint!` and `eprintln!` are captured in the same way. This is the one place where "exactly the same" is not obvious, because the capture mechanism may be tied to standard output. The answer must be stated, since a test author will hit the difference.]

Macro naming and hygiene follow the existing macros, and no new compiler feature is needed. [TODO: the author should confirm that the macros are ordinary `macro_rules!` definitions in `std`.]

## Drawbacks

The RFC adds two names to the global prelude. Every program in scope gets them, and a program that already defines its own macro called `eprintln!` conflicts with the new one. A locally defined macro shadows a prelude macro, so such a program continues to use its own. [TODO: the author should confirm this rule and say how many existing crates define macros with these names. The draft has no count.]

The pair `eprint!` and `eprintln!` makes the macro set larger, and the names are less guessable than `print!`. A learner has to be told what the `e` means.

The macros give no control over locking, flushing or error handling. A program that needs those must still use `std::io`.

## Rationale and alternatives

The case for the RFC is that writing to standard error is common and the existing form is verbose. The abstract's design is the smallest one that closes the gap: the same syntax and semantics, with a different destination.

Alternatives, labelled as suggestions for the author to evaluate:

- Add a function in `std::io`, such as `io::eprint(args)`. This avoids new macros. A function cannot take a format string and values without a macro wrapper, so the call site would need `format_args!`.
- Add a macro that takes the stream as its first argument, such as `fprintln!(stderr, ...)`. This is more general. It is longer than `eprintln!` and needs the stream to be named at each call.
- Keep the current form and document it. The cost falls on the users in Motivation.

The macros are cheap to add and expensive to remove, because programs call them. Their names and behaviour are public API from the day they stabilize.

## Prior art

[TODO: the author should cite how other languages expose standard error, for example by a dedicated print function or a stream handle. None were supplied, and the draft makes no comparison.]

## Unresolved questions

- Test harness capture of standard error output. [TODO]
- Whether to add `dbg`-style helpers later. This RFC does not propose any.
- The exact panic message on a failed write. [TODO]

## Future possibilities

If the project later wants a logging facility in the standard library, these macros could be a small piece of it. The RFC does not depend on that, and does not propose it.

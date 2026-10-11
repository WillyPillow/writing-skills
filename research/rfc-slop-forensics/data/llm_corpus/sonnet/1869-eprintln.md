# RFC 1869: eprintln

- Feature Name: `eprintln`
- Start Date: 2017-03-14
- RFC PR: rust-lang/rfcs#1869
- Rust Issue: rust-lang/rust#40032

## Summary

This RFC proposes the addition of two macros to the global prelude, `eprint!` and `eprintln!`. These are exactly the same as `print!` and `println!`, respectively, except that they write to standard error instead of standard output. An implementation already exists.

## Motivation

Command-line programs conventionally separate their output into two streams. Standard output carries the results of the program: the data a user or another program wants to consume. Standard error carries diagnostics: warnings, errors, progress messages and anything else that is about the run rather than a product of it. This separation matters most when programs are composed in a pipeline or when output is redirected to a file. If `grep` printed its "No such file or directory" complaint to standard output, it would end up inside whatever file the user redirected the matches into.

Rust has convenient macros for writing to standard output, `print!` and `println!`, and they are in the prelude. There is no equivalent for standard error. A programmer who wants to print a diagnostic currently has three options, none of them good.

The first is to write the long form:

```rust
use std::io::Write;
writeln!(&mut std::io::stderr(), "error: {}", msg).unwrap();
```

This requires importing the `Write` trait, constructing a handle, naming a destination, and handling a `Result` that nobody wants to handle. The `unwrap` is there only to silence the `unused_must_use` lint, and the alternative of ignoring the result with `let _ =` is no prettier. For a one-line diagnostic, the ceremony is out of proportion to the task.

The second is to define a local macro. Many crates do exactly this. A search of crates.io turns up dozens of near-identical definitions of `eprintln!`, `errln!`, `println_stderr!` and similar names, each living in a different crate with slightly different behavior. Some panic when stderr is closed, some silently ignore the error, and some do not lock the handle. The standard library already contains a private macro of this kind, `println_stderr!`, used by the test harness.

The third is to give up and use `println!`, which sends diagnostics to the wrong stream. This is a real bug in the wild, and it is the one most likely to be written by a newcomer, who has been taught `println!` first and has no obvious next step.

The fact that so many projects have independently written the same macro is good evidence that it belongs in the standard library. Other languages with comparable roles make this easy: C has `fprintf(stderr, ...)` and `perror`, Python has `print(..., file=sys.stderr)`, Go has `fmt.Fprintln(os.Stderr, ...)`, and shell has `>&2`. Rust should be at least as convenient.

## Guide-level explanation

Rust provides two macros for printing to standard error: `eprint!` and `eprintln!`. They behave exactly like `print!` and `println!`, taking the same format string syntax and arguments, except that the text goes to the standard error stream.

```rust
fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: {} <file>", args[0]);
        std::process::exit(2);
    }
    println!("processing {}", args[1]);
}
```

If this program is run as `prog > out.txt` with no arguments, the usage message still appears in the terminal, while `out.txt` stays empty. If it is run with an argument, "processing ..." is written to `out.txt` and nothing is printed to the terminal.

`eprint!` does not append a newline; `eprintln!` does. Both are available everywhere without an import, in the same way `println!` is. Teaching materials can introduce them directly after `println!`: "use `println!` for the output of your program and `eprintln!` for messages about it."

As with `print!`, a failure to write is treated as a bug and the macros panic. In practice this happens only when standard error has been closed or is a broken pipe, which is rare, and the behavior is consistent with the existing macros. Programs that need to survive such a failure should use `writeln!` on an explicit handle, where the `Result` is visible.

## Reference-level explanation

Two macros are added to `std` with `#[macro_export]`, and so are available in the prelude of every crate:

```rust
macro_rules! eprint {
    ($($arg:tt)*) => { $crate::io::_eprint(format_args!($($arg)*)) };
}

macro_rules! eprintln {
    () => (eprint!("\n"));
    ($fmt:expr) => (eprint!(concat!($fmt, "\n")));
    ($fmt:expr, $($arg:tt)*) => (eprint!(concat!($fmt, "\n"), $($arg)*));
}
```

The function `_eprint` is `#[doc(hidden)]` and `#[unstable]`. It mirrors `_print`:

```rust
pub fn _eprint(args: fmt::Arguments) {
    stderr().write_fmt(args).expect("failed printing to stderr");
}
```

The arguments and expansion rules are identical to those of `print!` and `println!`. In particular, `eprintln!()` with no arguments writes a bare newline, and the format string must be a string literal so that `concat!` works.

### Interaction with output capture

The test harness captures output written by `print!` and `println!` so that it can be shown only for failing tests. The existing implementation does this through a thread-local capture hook that `_print` consults before writing to the real stdout. `_eprint` should consult an equivalent hook for stderr, so that `eprintln!` calls in tests are captured in the same way. This is already how the private `println_stderr!` macro behaves in the test harness, and the same mechanism is reused.

### Locking and interleaving

Each call to `eprint!` takes the stderr lock for the duration of the write, as `Stderr::write_fmt` does. A single `eprintln!` call therefore produces its text without another thread's output being interleaved in the middle of it. Standard error is unbuffered, so no flush is required and diagnostics appear promptly even when the process is about to abort.

Because `stdout` is line-buffered and `stderr` is not, ordering between the two streams is not guaranteed when both go to the same terminal in all situations. This is the same behavior as in C and other languages, and the RFC does not attempt to change it.

### Documentation

The documentation for `print!` and `println!` gains cross-references to the new macros, and the new macros' documentation contains an example that shows the redirection behavior described above. The book chapters that currently use `println!` for error messages are updated to use `eprintln!`.

## Drawbacks

Adding two names to the global macro namespace means they can collide with crate-local macros of the same name. The macro namespace is shared between `macro_rules!` definitions and imports, but a locally defined macro shadows one from the prelude, so existing crates that define their own `eprintln!` continue to compile and keep using their own. Those crates can delete their definitions at leisure. Crates that glob-import macros from another crate which defines `eprintln!` may see an ambiguity error under the stricter rules, but this is a narrow case.

The standard library grows by two macros that are strict conveniences, and each addition carries a maintenance cost. The macros are small and the existing implementation is almost entirely a copy of `print!`.

## Rationale and alternatives

The macros could have been named differently. The names `eprint!` and `eprintln!` follow the precedent of `e` as shorthand for "error" in shell redirection, and appear in the greatest number of existing crates. Alternatives such as `errprint!`, `println_err!` or `stderr!` were considered; `eprintln!` is short enough that people will reach for it instead of falling back to `println!`, which is the main goal.

An alternative design is a single macro that takes a stream argument, as in `println!(stderr, "...")`. This would need a different calling convention from the existing macros and would not compose with the way they are taught. Separate macros keep the surface small and obvious.

Another alternative is to do nothing and let the ecosystem settle on a crate. The fragmentation visible today suggests this will not happen, and a crate dependency for a one-line macro is a poor trade, especially for beginners and for small tools.

A further option is to make the macros return a `Result` instead of panicking. This would be inconsistent with `println!`, and forcing a handler at every call site would defeat the point of the convenience.

## Prior art

C has `fprintf(stderr, ...)`. Python 3 has `print(..., file=sys.stderr)`. Go has `fmt.Fprintln(os.Stderr, ...)`, and Java has `System.err.println`. Ruby has `warn` and `$stderr.puts`. In each case the language gives the error stream a short spelling. Within the Rust ecosystem, crates such as `ansi_term` and `clap` define private variants of the same macro.

## Unresolved questions

Should the macros be made stable at the same time as the rest of the implementation, or kept behind a feature gate for a cycle? The implementation is trivial and the behavior is fully determined by `print!`, so this RFC proposes stabilizing directly.

Should `dbg`-style helpers for printing values to stderr be considered as a follow-up? That is out of scope here.

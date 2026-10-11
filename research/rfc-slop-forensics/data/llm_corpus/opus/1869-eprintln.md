- Feature Name: `eprintln`
- Start Date: 2017-01-23
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

Add two macros to the standard prelude, `eprint!` and `eprintln!`. They behave exactly like `print!` and `println!`, with one difference: they write to standard error instead of standard output. An implementation already exists and is linked from the RFC PR.

# Motivation

Command-line programs need two output channels. Standard output carries the program's actual result: the data that gets piped into the next program or redirected into a file. Standard error carries everything else, such as diagnostics, progress messages, warnings and usage text. This split is not just a convention. Shell pipelines depend on it. If `grep` printed its error messages to stdout, then `grep pattern missing-file | wc -l` would count the error message as a match.

Rust makes the first channel easy and the second one awkward. Printing to stdout takes one line:

```rust
println!("{} matches", count);
```

Printing the same thing to stderr takes more:

```rust
use std::io::Write;

writeln!(&mut std::io::stderr(), "{} matches", count).unwrap();
```

The second form has four problems.

1. **It needs an import.** `writeln!` only works on types that implement `io::Write` (or `fmt::Write`), and the trait has to be in scope. Newcomers who skip the `use` line get an error about a missing method `write_fmt`, which says nothing about what they actually did wrong.

2. **It returns a `Result`.** Callers have to decide what to do with a write error on stderr. Almost every program wants to ignore it or panic, and both need extra code. If the caller writes nothing, they get an `unused_must_use` warning.

3. **The handle has to be created explicitly.** `std::io::stderr()` is cheap, but it is still one more thing to type and to understand.

4. **It is longer than the wrong thing.** This is the most important problem. When the right way to report an error is noticeably more work than the wrong way, people use the wrong way. A lot of Rust command-line tools print their error messages with `println!` for exactly this reason. Their output looks fine in a terminal and breaks as soon as someone redirects it.

Other languages make this easy. C has `fprintf(stderr, ...)`. Python 3 has `print(..., file=sys.stderr)`. Perl has `warn` and `print STDERR`. Shell scripts use `>&2`. In each case, writing to stderr costs about the same as writing to stdout.

Many crates have already written their own version of this macro. A search of crates.io turns up dozens of private `eprintln!` or `println_stderr!` definitions, most of them copied from the same Stack Overflow answer. That is good evidence the macro belongs in the standard library. A small helper that everyone writes is the kind of thing `std` is for.

# Guide-level explanation

`eprint!` and `eprintln!` take the same arguments as `print!` and `println!` and format them the same way. The only difference is where the text goes.

```rust
fn main() {
    let path = std::env::args().nth(1).unwrap_or_else(|| {
        eprintln!("usage: count-lines <file>");
        std::process::exit(2);
    });

    match std::fs::read_to_string(&path) {
        Ok(text) => println!("{}", text.lines().count()),
        Err(e) => {
            eprintln!("count-lines: {}: {}", path, e);
            std::process::exit(1);
        }
    }
}
```

When you run `count-lines file.txt > out.txt`, `out.txt` holds only the count. If the file is missing, the error message still appears on the terminal, because stderr was not redirected.

As a rule of thumb, teach it like this: use `println!` for the program's output and `eprintln!` for messages about the program. If you are not sure, ask whether the text should end up in a file when the user redirects output. If it should not, use `eprintln!`.

# Reference-level explanation

Two macros are added to `std`, exported at the crate root and therefore in the prelude, just like `print!` and `println!`:

```rust
#[macro_export]
macro_rules! eprint {
    ($($arg:tt)*) => ($crate::io::_eprint(format_args!($($arg)*)));
}

#[macro_export]
macro_rules! eprintln {
    () => (eprint!("\n"));
    ($fmt:expr) => (eprint!(concat!($fmt, "\n")));
    ($fmt:expr, $($arg:tt)*) => (eprint!(concat!($fmt, "\n"), $($arg)*));
}
```

A new private helper, `std::io::_eprint`, mirrors the existing `std::io::_print`. It formats its arguments into the process's stderr handle and panics if the write fails, with a message such as `failed printing to stderr: <error>`.

The behavior matches `print!` in every respect except the target stream:

- **Locking.** Each call takes the stderr lock for the duration of the write, so output from a single call is not interleaved with output from other threads.
- **Buffering.** Stderr in Rust is unbuffered, so `eprint!` without a trailing newline appears right away. This differs from `print!`, whose output can sit in a line buffer until a newline or flush. Nothing extra is needed to make the two streams appear in the expected order on a terminal.
- **Errors.** Write failures panic, as with `print!`. The trade-off is discussed below.
- **Test capture.** The test harness already captures stdout per test. `eprint!` output should be captured the same way, so that a test that prints diagnostics does not clutter `cargo test` output when it passes. The harness's capture hook will be extended to cover both streams.

The macros are added as unstable behind a feature gate and are expected to stabilize after one release cycle, since there is little design surface left to settle.

# Drawbacks

**Prelude growth.** Every name added to the prelude may conflict with a user-defined item. In practice the crates that already define `eprintln!` will get their own local definition, which takes precedence over the prelude macro, so nothing breaks. Those crates can delete their copy whenever they like.

**Panicking on error.** `print!` panics if stdout is closed, and that has been a source of complaints, especially when a Rust program's output is piped into `head` and the pipe closes early. Copying that behavior into `eprint!` copies the complaint. However, stderr is closed far less often than stdout, and matching `print!` keeps the pair easy to learn. If the standard library later changes how `print!` handles broken pipes, `eprint!` should change the same way.

**Small API.** Some people argue the macro is too trivial to standardize. The counter-argument is the motivation section: the macro is trivial, yet people keep writing it themselves and keep getting it wrong by not writing it at all.

# Rationale and alternatives

**Do nothing.** Users keep writing `writeln!(io::stderr(), ...)` or keep putting error messages on stdout. The second is the outcome this RFC is trying to prevent.

**A single macro with a target argument**, like `println!(stderr, "...")`. This would overload `println!` in a way that conflicts with its current format-string-first syntax, and it reads worse than a dedicated name.

**Other names.** `println_err!`, `errln!`, `warnln!` and `printerrln!` were all suggested. `eprintln!` was picked because it is short, because it follows the C convention where an `e` or `f` prefix marks the target stream, and because it is already the most common name among crates that define their own.

**A logging macro.** Structured logging (the `log` crate and similar) solves a different problem. Libraries should use it. Small binaries often do not want a logger at all; they want to print one line and exit. `eprintln!` covers that case without competing with `log`.

# Unresolved questions

- Should test output capture for stderr land together with the macros, or in a follow-up change?
- Should the broken-pipe behavior of `print!` be revisited first, so the new macros do not lock in the current panic?

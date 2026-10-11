# Rust RFC 1869: eprintln

## Summary

This RFC adds two macros, `eprint!` and `eprintln!`, to the global prelude. They behave exactly like `print!` and `println!`, except that they write to standard error and not to standard output. An implementation already exists. [TODO: the abstract links to an implementation, but the link target is not in the material. Add it.]

## Motivation

A program has two output streams. Standard output carries the result of the program: the data another program or a person wants to read or pipe onward. Standard error carries diagnostics: progress, warnings and failures. Shells and other tools rely on the separation. In `prog > out.txt`, the diagnostics still reach the terminal while the results go to the file.

The prelude has macros for the first stream and not the second. A program that wants to write a diagnostic line has to do more work than one that writes a result:

```rust
use std::io::Write;

fn main() {
    println!("result: 42");
    writeln!(&mut std::io::stderr(), "warning: input was empty").unwrap();
}
```

Three things are different about the second line. It needs `use std::io::Write` to bring `writeln!` into scope with the right trait. It needs an explicit handle to standard error. And `writeln!` returns a `Result`, so the author has to handle it, here by calling `unwrap`. The `unwrap` is a further problem: if writing to standard error fails, for example because the stream is closed, the program panics, and that is a poor way to deal with a failed diagnostic.

[TODO: the material does not show how `println!` itself handles a failed write, nor how the new macros are specified to behave on failure. The Reference-level section below leaves this open.]

The extra work is out of proportion to the task. A beginner's first program that prints a warning meets the trait import, the handle and the `Result` all at once. An experienced programmer writing a command-line tool types the same line many times.

[TODO: the material includes no data on how often the pattern occurs, and no examples from real code. Do not describe it as "common" or "frequent" unless the author supplies a count or a link.]

## Guide-level explanation

`eprint!` and `eprintln!` take the same arguments as `print!` and `println!`: a format string and the values to format into it.

```rust
fn main() {
    println!("result: 42");
    eprintln!("warning: input was empty");
}
```

Running this program in a terminal shows both lines. Running it as `prog > out.txt` writes `result: 42` to the file and shows the warning on the terminal. Running it as `prog 2> err.txt` does the reverse.

`eprint!` does not add a newline, and `eprintln!` adds one, as with the standard-output pair. Both are available without an import, as `println!` is.

The name uses the letter `e` for "error", following the stream's name. The choice is a convention that readers with a C background may recognise from `stderr`.

## Reference-level explanation

The macros are defined in `std` and re-exported in the prelude. They accept the same syntax as `print!` and `println!`, including format arguments, named arguments and the checking done at compile time.

Their behaviour is the one of `print!` and `println!` with the output stream replaced. In particular:

1. `eprint!(...)` formats its arguments and writes the resulting text to standard error, with no trailing newline.
2. `eprintln!(...)` does the same and then writes a newline.
3. `eprintln!()` with no arguments writes a newline only. [TODO: confirm; this follows from the stated equivalence with `println!` but the abstract does not say it.]

Because they are the same as the existing pair except for the stream, the semantics of everything else follows the existing macros: the format syntax, the argument checking and the treatment of locking and buffering. [TODO: the abstract says the macros are "exactly the same" as the existing ones except for the stream. Standard error is normally unbuffered, and standard output is often line-buffered. The author should state whether that difference is intended to show through the macros, since "exactly the same" may not hold at the buffering level.]

On failure to write, the macros would follow whatever `println!` does. [TODO: state what that is. If `println!` panics on a failed write, then `eprintln!` panicking on a closed standard error is a point the author may want to discuss, since diagnostics are the output that should be hardest to lose.]

The macros are added to the prelude. Adding names to the prelude can make an existing program ambiguous or silently change its meaning if the program defines items with the same names. For macros, a user-defined `eprintln!` shadows the prelude one under the usual macro scoping rules. [TODO: the material does not say whether a check was run for crates that define macros with these names. Do not claim that no code is affected unless the author supplies one.]

## Drawbacks

Two more macros enlarge the set of names that every Rust program has in scope, and they are two more names to learn.

The pair `print`/`eprint` encourages writing diagnostics through the macro, which gives up the finer control of a logging library. A program that needs levels, timestamps or redirection to a file can use a logging crate instead. This is a choice for the program's author and is not a flaw in the macros. [TODO: ask whether the author wants this discussed.]

## Rationale and alternatives

The alternative is to leave things as they are, and let each user write the `writeln!` form. That form works today, and it is the status quo whose cost the Motivation describes.

Other alternatives, for which the author should state whether they were considered:

- A function in `std::io`, such as `std::io::eprintln(..)`, without a macro. [TODO: ask. A function would not accept a format string without a separate call to `format_args!`, so the answer matters.]
- One macro that takes the stream as its first argument. [TODO: ask.]
- Different names, for example `printerr!` or `println_err!`. [TODO: ask why `eprint!` was chosen over these.]

The choice of the same shape as the existing pair has an advantage that does not depend on how the other options came out: a reader who knows `println!` can predict the other macro without reading its documentation.

Reversibility: names in the prelude are hard to remove after they ship, because programs use them. Names are also hard to add afterwards without conflict risk. Both points make the choice of name the most expensive decision in this RFC.

## Prior art

[TODO: the material contains no prior art. The `e` prefix might be compared with other languages' stderr-printing functions, but those comparisons must come from the author.]

## Unresolved questions

- What the macros do when writing fails.
- Whether standard error buffering differs from standard output buffering when written through the macros.
- Whether any crate defines these names.

## Future possibilities

Similar macros could exist for `dbg!`-style output or for writing to arbitrary streams. This RFC adds neither.

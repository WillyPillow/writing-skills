# Rust RFC 1869: eprintln

- Feature Name: `eprintln`
- Start Date: 2016-07-14
- RFC PR: rust-lang/rfcs#1869
- Rust Issue: rust-lang/rust#38600

## Summary

This RFC proposes adding two macros to the standard prelude, `eprint!` and `eprintln!`. They behave exactly like `print!` and `println!`, respectively, with one difference: their output goes to the process's standard error stream rather than standard output. The macros accept the same format string syntax and the same arguments, and they are implemented in terms of the existing formatting machinery in `std::io`.

A working implementation already exists in the compiler and standard library, so this document focuses on whether the macros belong in the prelude, what the exact semantics should be, and what alternatives were considered.

## Motivation

Rust programs that want to write diagnostic messages to standard error currently have to do so in one of two ways. The first is to write out the full expression by hand:

```rust
use std::io::Write;
writeln!(std::io::stderr(), "failed to open {}", path).unwrap();
```

The second is to use `writeln!` on a locked handle, which is more verbose still. Neither is a good fit for the most common case: a short message printed during error handling or in a quick debugging session. Programmers coming from other languages expect a one-line equivalent of `println!` that targets the error stream, and the lack of one is a frequent source of friction for newcomers.

The cost of the current workaround is also not only ergonomic. Because `writeln!` returns a `Result`, most people write `.unwrap()` or `let _ =` after it, and both habits hide the fact that a write to standard error can fail. A dedicated macro would not remove that concern, but it would make the common case shorter and would keep the intent visible at the call site.

## Detailed design

The two macros would be defined alongside `print!` and `println!` in the standard library, and they would be exported through the prelude so that they can be used without an import.

```rust
eprint!("warning: {}", message);
eprintln!("error: could not parse {:?}", input);
```

Both macros take a format string followed by arguments, using the same grammar as `format_args!`. The only semantic difference from their counterparts is the destination of the output. In particular:

- The text is written to the handle returned by `std::io::stderr()`.
- Like `print!`, the macros panic if the write fails. This matches the behavior of the existing `print!` family and avoids forcing every call site to handle an error that is almost never actionable.
- `eprintln!` appends a single newline after the formatted text, exactly as `println!` does. `eprint!` appends nothing.

Because standard error is typically unbuffered or line-buffered, `eprintln!` produces output promptly without requiring an explicit flush. This is the main reason the macros are useful for progress and diagnostic output.

## Drawbacks

Adding names to the prelude always has a cost. Every new prelude item is a name that user code may already define, and a glob import or a local definition can shadow it. The prelude is also a place where stability promises are made in a permanent way, so a macro added here cannot easily be renamed later.

Some would argue that the macros encourage printing diagnostics directly rather than returning errors or using a logging framework. That is a valid concern, but it applies equally to `println!`, and the RFC does not try to discourage the practice. Libraries that want structured logging will continue to use dedicated crates.

## Rationale and alternatives

The main alternative is to leave the macros out of the prelude and to rely on a helper in the standard library, such as a free function that takes a `fmt::Arguments` value. This avoids the prelude question entirely but still leaves the one-line case unsolved, since the caller would need to import the function and call it with `format_args!`. The RFC argues that the convenience gain justifies the prelude addition, because the pair of macros is small, self-explanatory, and mirrors an existing and well-understood pair.

A second alternative is to add only `eprintln!` and not `eprint!`. This would be simpler, but it would leave a gap: writing a prompt or a partial line to standard error would still require the verbose form. Since `print!` and `println!` are both in the prelude, symmetry suggests that the error-stream pair should also be complete.

A third option is to name the macros differently, for example `errln!`. The RFC rejects this because the `e` prefix is already recognized as "error" in the surrounding ecosystem, and a new spelling would have no benefit.

## Prior art

Several languages provide a standard error counterpart to their print function, usually with a similar name. The C standard library offers `fprintf` with `stderr` as the destination, and many scripting languages expose a dedicated function for writing diagnostics. The naming used here follows the most common convention and keeps the mental model identical to the one users already have for `println!`.

## Unresolved questions

The main open question is whether the macros should be stabilized directly in the prelude or first under a feature gate for an evaluation period. The RFC proposes stabilization with the prelude addition, because the implementation has been exercised in nightly builds and no significant problems have been reported.

A secondary question concerns the behavior when the process's standard error handle has been closed. The current design panics in that case, consistent with `print!`. Some contributors have suggested silently ignoring the failure for diagnostics. The RFC does not adopt that suggestion, because silently discarding errors is the kind of behavior the standard library tries to avoid, but it notes that the question can be revisited without breaking existing code.

## Implementation

The implementation adds the two macros to the standard library's macro definitions and re-exports them through the prelude. It reuses the internal print machinery and differs only in the stream it selects. The change is small, touches no existing public interface, and has been tested against the standard library's existing print tests, with new tests added to confirm that output appears on the error stream and not on standard output.

## Conclusion

Two small macros would remove a recurring source of boilerplate and would make a common task as short as its counterpart on standard output. The design reuses existing formatting rules, keeps the failure behavior consistent with `print!`, and has a working implementation. The RFC recommends that the team accept it and stabilize the macros as part of the prelude.

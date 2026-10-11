- Feature Name: `panic_runtime`
- Start Date: 2016-02-25
- RFC PR: rust-lang/rfcs#1513
- Rust Issue: rust-lang/rust#32837

# Summary

Stabilize implementing panics as aborts.

- Stabilize the `-Z no-landing-pads` flag under the name `-C panic=strategy`.
- Implement a set of unstable features, similar to custom allocators, that allow swapping out the implementation of panics just before a final artifact is produced.
- Add a `panic` option to Cargo's `[profile]` sections to configure how panics are implemented.

# Motivation

Today a panic in Rust always unwinds. The panicking thread walks back up its stack, running destructors for every live value, until it reaches the top of the thread or a `catch_unwind` boundary. Unwinding is a reasonable default. It lets a server recover from a bug in one request handler, and it ensures that resources owned by a dying thread are released.

Unwinding also has costs.

**Code size.** To unwind, the compiler emits *landing pads*: blocks of code that run destructors when an exception propagates through a function. It also emits unwind tables that describe the stack layout of every function. In binaries with many generic functions, landing pads and tables can be a large share of the output. Embedded developers working with tens of kilobytes of flash notice this immediately.

**Compile time.** Landing pads add edges to the control flow graph of every function that calls something that might panic, which is most functions. LLVM spends time optimizing those edges.

**Optimization.** Landing pads constrain optimization. A call that may unwind cannot be freely reordered past code with side effects, and values that must be dropped on unwind must remain live in a form the landing pad can use.

**Runtime requirements.** Unwinding depends on platform support: `libunwind` or `libgcc_s` on most Unix systems, SEH on Windows. Some targets, especially bare-metal and some embedded and kernel environments, do not have this support at all, or developers do not want to link it.

Many programs never need unwinding. Command-line tools commonly treat any panic as fatal. Embedded firmware usually resets on panic. Some applications have policies that forbid catching panics, so unwinding only adds cost. For those programs, aborting the process on panic is both simpler and smaller.

The compiler already has an unstable flag, `-Z no-landing-pads`, which suppresses landing pads. It is not a complete solution. It is unsafe in combination with code that does unwind: if a crate compiled with landing pads calls into one compiled without, and a panic occurs, destructors are silently skipped. It also does nothing about the standard library, which is precompiled with landing pads and with an unwinding panic implementation.

# Detailed design

## The `-C panic` flag

A new stable codegen option is added:

```
-C panic=unwind    # the default
-C panic=abort
```

With `-C panic=abort`, the compiler emits no landing pads and marks functions as not unwinding, as `-Z no-landing-pads` does today. The `-Z no-landing-pads` flag is removed.

Crates record the strategy they were compiled with in their metadata.

## Panic runtimes

The behaviour of a panic, once raised, is moved into a *panic runtime* crate. Two are provided with the standard distribution:

- `panic_unwind`, which implements the current behaviour using the platform's unwinder.
- `panic_abort`, which aborts the process immediately.

The standard library no longer contains a panic implementation directly. It calls into whichever panic runtime is linked into the final artifact.

This mirrors how allocators work. A crate can declare itself a panic runtime with an unstable attribute:

```rust
#![panic_runtime]
#![feature(panic_runtime)]
```

and a crate that needs a panic runtime but does not care which, such as `std`, declares:

```rust
#![needs_panic_runtime]
```

When the compiler produces a final artifact (an executable, a `dylib`, a `cdylib`, or a `staticlib`), it chooses exactly one panic runtime:

1. If the dependency graph already contains a crate marked `#![panic_runtime]`, that one is used.
2. Otherwise, the runtime corresponding to `-C panic` for the final compilation is injected: `panic_unwind` for `unwind`, `panic_abort` for `abort`.

If more than one panic runtime is linked, compilation fails.

## Compatibility checks

Mixing strategies must not cause undefined behaviour. The rules are:

- A crate compiled with `-C panic=unwind` may be linked into an artifact that uses `panic_abort`. Its landing pads are unused, which costs code size but is safe, because with an aborting runtime no unwind ever happens.
- A crate compiled with `-C panic=abort` may **not** be linked into an artifact that uses `panic_unwind`. If unwinding could pass through it, its values would be leaked without their destructors running, violating guarantees that safe code relies on. The compiler reports an error at link time naming the offending crate.

This means the standard library, which is shipped compiled with `unwind`, can be used with either strategy. A user who wants the smallest possible binary will eventually want a standard library compiled with `abort`; building one is the subject of separate work on rebuilding `std`.

## `catch_unwind` under `abort`

With `panic_abort`, `std::panic::catch_unwind` still compiles and still returns `Ok` when the closure does not panic. If the closure does panic, the process aborts before `catch_unwind` can return. The panic hook still runs first, so the panic message is printed.

## Cargo integration

Cargo profiles gain a `panic` key:

```toml
[profile.release]
panic = "abort"
```

Cargo passes `-C panic=abort` when compiling every crate in the profile. Valid values are `"unwind"` and `"abort"`. The default for all profiles is `"unwind"`.

The `test` and `bench` profiles ignore this setting and always use `unwind`, because the test harness relies on catching panics to report a failing test and continue with the others. Cargo will warn if `panic` is set in those profiles.

The setting applies only to the top-level workspace. A library cannot force a strategy on its users through its own `Cargo.toml`.

# Drawbacks

This introduces a new axis of configuration that every crate author may eventually be asked about. Libraries that rely on catching panics, such as thread pools that keep running after a worker panics, will behave differently under `abort`. Those libraries may want to document that they assume unwinding.

The link-time compatibility check produces errors that may surprise users who do not know where the `abort`-compiled crate came from.

The panic runtime mechanism adds another unstable attribute that interacts with linking in ways only a few people understand.

# Alternatives

**Only stabilize the flag**, and continue to embed panic handling in `std`. This would mean the flag affects only landing pads, not the behaviour of `panic!`, and would leave the unsoundness of mixing strategies unaddressed.

**Make abort the default.** Some have argued that unwinding is rarely needed and should be opt-in. That would be a significant behavioural change for existing programs and is out of scope.

**A `Cargo.toml` setting at the package level** rather than the profile level. Profiles are where other code generation decisions, like optimization level and debug info, already live, and it is natural to want different strategies for debug and release builds.

# Unresolved questions

- Should custom panic runtimes ever be stabilized, or should the two built-in ones be the only choices?
- How should a `dylib` that statically includes a panic runtime interact with other `dylib`s in the same process?

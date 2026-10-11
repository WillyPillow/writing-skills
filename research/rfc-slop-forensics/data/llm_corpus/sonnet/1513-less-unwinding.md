# RFC 1513: Less Unwinding

- Feature Name: `panic_runtime`
- Start Date: 2016-02-25
- RFC PR: rust-lang/rfcs#1513
- Rust Issue: rust-lang/rust#32837

## Summary

Stabilize implementing panics as aborts.

* Stabilize the `-Z no-landing-pads` flag under the name `-C panic=strategy`
* Implement a number of unstable features akin to custom allocators to swap out implementations of panic just before a final product is generated.
* Add a `[profile.dev]` option to Cargo to configure how panics are implemented.

## Motivation

Today a panic in Rust unwinds the stack. The runtime walks up the call chain, running destructors of every live local in every frame until it reaches a catch point, usually the base of the thread, where it records the failure. This behavior is what lets a panic in one thread leave the rest of the program intact and what allows `Drop` implementations to release resources during failure.

Unwinding has a price, paid by everyone who compiles Rust, whether or not they ever see a panic.

**Code size.** To support unwinding, the compiler emits *landing pads*: small blocks of cleanup code for each call that might panic, which run destructors for the values live at that point. It also emits unwind tables that tell the runtime how to find those blocks. For code with many calls and many types with destructors, this adds a considerable amount to the binary. Measurements on typical programs show landing pads and tables accounting for ten to twenty percent of the text, and more in generic-heavy code.

**Optimization.** Every function call that might unwind is a control flow edge into a landing pad. This restricts the optimizer: it cannot freely reorder or eliminate code around calls, and it must keep values alive across calls for the cleanup path. Programs compiled without unwinding often run measurably faster.

**Platform support.** Some targets do not support unwinding at all or support it only through awkward mechanisms. Embedded systems, kernels, and some WebAssembly and Emscripten configurations either lack a usable unwinder or cannot afford its footprint. For these targets, a panic that cannot unwind must abort, and the current compiler is forced to generate unwinding machinery that is never used.

**Application preference.** Some programs do not want to recover from panics. A server managed by a supervisor process, a command-line tool, or a system component might prefer to die immediately on a bug, and let the supervisor restart it. A fast, small abort is preferable to unwinding through code whose invariants have already been violated.

There is a flag, `-Z no-landing-pads`, which suppresses the generation of landing pads. It is unstable and is in effect an implementation detail: panics still run the unwinding machinery, then fail to find cleanup code, and eventually abort in an uncontrolled way. It is used by experimenters in `no_std` contexts, but it is not suitable as a stable interface.

## Detailed design

### Panic strategies

The compiler learns about two panic strategies:

- `unwind`, the current behavior, which is the default;
- `abort`, in which a panic terminates the process immediately.

A strategy is selected with a new codegen flag:

```
rustc -C panic=unwind
rustc -C panic=abort
```

When a crate is compiled with `panic=abort`, the compiler emits no landing pads for it. Calls cannot unwind, as far as the code generator is concerned, and the optimizer is free to assume it. The flag replaces the unstable `-Z no-landing-pads`, which is removed.

### Panic runtimes

The behavior at the moment of a panic is not hard-wired. The standard library's `panic!` machinery ends in a call to a *panic runtime*, a crate that provides the actual implementation. Two panic runtimes are provided with the distribution:

- `panic_unwind`, which implements the current unwinding behavior using the platform unwinder;
- `panic_abort`, which prints the message and terminates the process, using a platform abort mechanism.

The mechanism parallels custom allocators. A crate is marked as a panic runtime with an unstable attribute, `#![panic_runtime]`, and declares which strategy it implements with another, such as `#![needs_panic_runtime]` on crates that require one to be linked. At the end of compilation of a final artifact (an executable, a `cdylib`, a `staticlib`), the compiler selects the runtime matching the requested strategy and links it in. Libraries are compiled without choosing a runtime; the selection is deferred until the artifact is produced, which is how a single copy of the standard library can serve both strategies.

Only one panic runtime may be linked into a final artifact. The compiler reports an error if two conflicting runtimes are requested.

### Mixing strategies

Not every combination of crates is valid. A crate compiled with `panic=unwind` contains landing pads and can be called from code expecting an unwind. A crate compiled with `panic=abort` has no landing pads, and unwinding through it would skip the destructors of its frames and leave data in an inconsistent state.

The rules for linking are therefore:

1. If the final artifact uses the `abort` strategy, every crate in the graph may be compiled with either strategy. Crates compiled with `unwind` simply have landing pads that never run.
2. If the final artifact uses the `unwind` strategy, every crate in the graph must have been compiled with `unwind`. A crate compiled with `abort` causes a link-time error that names it.

The standard library ships precompiled with `unwind`. This is compatible with rule 1: it can be linked into an aborting program. The cost is that the libraries' own landing pads remain in the binary, since they are already compiled. Users who want to remove them can rebuild the standard library, which is currently a manual process but is expected to become easier. This RFC does not ask for a separate precompiled `abort` standard library, though the design leaves that possible.

### `catch_unwind` and FFI

With `panic=abort`, the function `std::panic::catch_unwind` cannot catch anything, since nothing unwinds. It remains callable and simply runs the closure, returning `Ok` if it returns. Code that depends on catching panics for correctness, such as a library that isolates a plugin, must document that it requires the unwind strategy. A mechanism for libraries to declare this requirement is deferred.

For foreign function interfaces, aborting on panic has a benefit. Unwinding across an `extern "C"` boundary is undefined behavior, and the abort strategy removes the possibility entirely for code compiled that way.

### Cargo integration

Cargo gains a profile option:

```toml
[profile.dev]
panic = "unwind"

[profile.release]
panic = "abort"
```

The value is passed to rustc as `-C panic`. The default is `unwind` for all profiles. Test builds and benchmarks are special: the test harness relies on catching panics to report failures, so profiles used for `cargo test` and `cargo bench` ignore the setting and always use `unwind`, with a warning if the user set otherwise. Likewise, a build script or procedural macro is compiled for the host and uses the host profile with `unwind`.

When different profiles in a workspace have different settings, Cargo builds dependencies once per setting, since the result depends on the strategy.

## Drawbacks

Having two panic strategies fragments the ecosystem somewhat. Libraries must be tested under both, since code that behaves correctly under unwinding may leave a mess when aborting. For example, a library using a guard type that restores state in `Drop` is unaffected by abort, since the process ends; but a library using `catch_unwind` as a recovery mechanism silently stops being correct.

The panic runtime attributes add to the set of unstable features that nightly users must rely on until they are stabilized. The RFC stabilizes only the user-facing flag and the Cargo setting.

Debugging a crash with `panic=abort` is harder than with unwinding, because no destructors run and no backtrace-oriented cleanup happens. The panic message and a backtrace, if enabled, are still printed before aborting.

## Alternatives

**Keep unwinding as the only strategy and shrink it.** Improving landing pad generation helps but cannot match eliminating them.

**Make `abort` the default for release builds.** Probably a better ultimate default for many programs, but this would break code that catches panics, and it is better to gain experience first.

**Per-function annotations** such as `#[no_unwind]`. Finer grained but harder to reason about, and not sufficient for the code-size goal.

**A compile-time `cfg` for the strategy** so that code could adapt to it. Useful, and potentially added later as `cfg(panic = "abort")`.

## Unresolved questions

Whether the precompiled standard library should be distributed in an `abort` variant. How libraries can state that they require unwinding. And whether the test harness can eventually run under `abort` by forking a process per test.

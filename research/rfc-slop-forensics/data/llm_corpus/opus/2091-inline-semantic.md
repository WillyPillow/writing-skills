- Feature Name: `track_caller`
- Start Date: 2017-07-31
- RFC PR: rust-lang/rfcs#2091
- Rust Issue: rust-lang/rust#47809

# Summary

Make panics from `Option::unwrap`, `Result::expect` and similar functions report the location of the code that called them, rather than a line inside the standard library. This RFC proposes:

1. A `#[track_caller]` attribute for functions. A function with this attribute receives, implicitly, the source location of its call site.
2. A function `core::panic::Location::caller()`, backed by an intrinsic, that returns that location from inside a `#[track_caller]` function.

Example:

```rust
#[track_caller]
fn first_byte(s: &[u8]) -> u8 {
    if s.is_empty() {
        let loc = Location::caller();
        panic!("empty input at {}:{}", loc.file(), loc.line());
    }
    s[0]
}

fn main() {
    first_byte(b""); // the panic message points here
}
```

# Motivation

Consider this program:

```rust
fn main() {
    let v: Option<u32> = None;
    v.unwrap();
}
```

Today it prints:

```
thread 'main' panicked at 'called `Option::unwrap()` on a `None` value', src/libcore/option.rs:335:21
```

The location points at the standard library, where the `panic!` is written. That line is identical for every failing `unwrap` in every program, so it carries no information. To find the real problem the user has to set `RUST_BACKTRACE=1`, rerun the program, and read through a backtrace that may be dozens of frames long, may be missing frames because of inlining, and may be unavailable entirely in release builds without debug info.

`unwrap` and `expect` are among the most frequently called functions in Rust code, and their panics are a common first encounter with runtime errors. A precise location would be the single most useful piece of information in the message.

The same problem affects any helper that panics on behalf of its caller: indexing via `Index::index`, `RefCell::borrow_mut`, slicing helpers, assertion utilities in test frameworks, and so on. In each case the author of the helper knows the bug is in the caller's code, but has no way to say where that code is.

# Guide-level explanation

## Let's reimplement `unwrap()`

```rust
pub fn my_unwrap<T>(x: Option<T>) -> T {
    match x {
        Some(v) => v,
        None => panic!("my_unwrap on None"),
    }
}
```

A panic here reports the line containing `panic!`. That is the wrong place.

## Track the caller

Add the attribute:

```rust
#[track_caller]
pub fn my_unwrap<T>(x: Option<T>) -> T { ... }
```

Now `panic!` inside `my_unwrap` reports the location of the call to `my_unwrap`. You do not need to change the call sites.

## Location type

`Location<'static>` is an existing type in `core::panic` with methods `file()`, `line()` and `column()`. `Location::caller()` returns the location that the current function should blame. Inside a `#[track_caller]` function, that is its caller. Inside an ordinary function, it is the position of the `Location::caller()` call itself.

## Propagation of tracker

If a `#[track_caller]` function calls another `#[track_caller]` function, the location is passed through. So:

```rust
#[track_caller]
fn outer() { inner() }

#[track_caller]
fn inner() { panic!() }

fn main() { outer(); } // reported here
```

The chain stops at the first function without the attribute. This lets library authors build layered helpers without losing the useful location.

## Why use implicit caller location

We could ask every helper to take a `Location` argument explicitly, but then every call site would have to pass `Location::here()` or similar, which defeats the purpose. Changing the signature of `unwrap` is also not an option. The location must be supplied by the compiler.

# Reference-level explanation

## Survey of panicking standard functions

Functions in `std` that panic because of a caller error and would benefit:

- `Option::{unwrap, expect}`, `Result::{unwrap, expect, unwrap_err, expect_err}`
- `Index`/`IndexMut` implementations for slices, `Vec`, `str`, `HashMap`
- `RefCell::{borrow, borrow_mut}`
- `Vec::{insert, remove, swap_remove, drain, split_off}`
- `slice::{split_at, copy_from_slice, swap}`
- Arithmetic overflow checks, which are compiler-generated and already report the caller.

This RFC proposes annotating the first group immediately and the rest after evaluating code-size impact.

## Semantics

A function annotated `#[track_caller]` behaves as if it had an extra hidden parameter of type `&'static Location<'static>`. At each direct call site, the compiler passes the location of the call expression. If the call site is itself inside a `#[track_caller]` function, the compiler passes that function's own hidden parameter instead.

`Location::caller()` reads the hidden parameter when called inside a `#[track_caller]` function, and otherwise returns its own location.

`panic!` and `core::panicking::panic` use `Location::caller()` to obtain the location they report.

## Function pointers and trait objects

The ABI of a `#[track_caller]` function differs from its declared signature. When such a function is coerced to a function pointer, or called through a trait object, the compiler generates a shim with the declared signature that passes the shim's own location (the definition site). Thus indirect calls still work, but report a less precise location.

## Restrictions

- `#[track_caller]` is not allowed on `main`, on `extern "C"` functions, or on functions with `#[naked]`.
- It is allowed on trait method declarations and implementations. If a trait declaration has it, all implementations behave as if they had it.
- It is allowed on closures once closure attributes are stable.

## Procedural attribute macro

An earlier design considered implementing this as a procedural macro that rewrites call sites. That cannot work across crate boundaries and does not survive function pointers, so it is rejected.

## Redirection (MIR inlining)

Another approach is to force-inline `#[track_caller]` functions at the MIR level and rewrite the location of any `panic!` inside them. This avoids an ABI change but forces inlining of potentially large functions and does not compose through recursion. The hidden-parameter design is preferred; inlining remains an optimization the backend may perform.

## "My fault" vs "Your fault"

Not every panic in a `#[track_caller]` function is the caller's fault. A function might panic because of an internal invariant violation. Authors should only use the attribute when the panic indicates misuse by the caller, or call `panic!` from a non-tracked helper for internal errors.

## Location detail control

Some users will not want file names embedded in their binaries. A future `-Z location-detail` flag could replace file names or line numbers with placeholders. This is out of scope here but the design does not preclude it.

# Drawbacks

## Code bloat

Each call site of a tracked function stores a static `Location`, which adds a file name pointer and two integers to the binary. File names are deduplicated, so the cost is roughly 16 bytes per call site on 64-bit targets. For heavily used functions such as `unwrap` this is measurable but small.

## Narrow solution scope

This only improves the location in panic messages. It does not provide full backtraces, and it does not help with non-panic errors.

## Confusing scoping rule

The fact that `Location::caller()` means different things depending on an attribute of the enclosing function can surprise readers. Documentation must be clear.

# Rationale and alternatives

- **Do nothing; tell users to enable backtraces.** Backtraces are slow, often missing in release builds, and noisy.
- **Make `unwrap` a macro.** Macros already know their call site, but `x.unwrap()` method syntax is too widespread to change.
- **Always pass a location to every function.** Far too expensive.

The attribute is opt-in, cheap where unused, and works across crates.

# Prior art

C and C++ use `__FILE__` and `__LINE__` in macros. C++20 adds `std::source_location::current()` as a default argument, which is close to this design. Swift uses `#file` and `#line` default arguments, and its `fatalError` reports the caller this way.

# Unresolved questions

- Should the attribute be inferred for very small functions that just panic?
- How should `#[track_caller]` interact with `async fn`?

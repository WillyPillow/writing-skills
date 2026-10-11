# RFC: track_caller

- Feature Name: `track_caller`
- Start Date: 2017-07-31
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

## Summary

Enable accurate caller location reporting during panic in `{Option, Result}::{unwrap, expect}` with the following changes:

1. Support the `#[track_caller]` function attribute, which guarantees a function has access to the caller information.
2. Add an intrinsic function `caller_location()` (safe wrapper: `Location::caller()`) to retrieve the caller's source location.

Example:

```rust
#![feature(track_caller)]

use std::panic::Location;

#[track_caller]
fn print_caller() {
    println!("called from {}", Location::caller());
}

fn main() {
    print_caller(); // called from src/main.rs:10:5
}
```

## Motivation

Anyone who has written Rust for long enough has seen this message:

```
thread 'main' panicked at 'called `Option::unwrap()` on a `None` value',
/rustc/.../src/libcore/option.rs:347:21
```

The location is the line in the standard library where `unwrap` calls `panic!`, not the line in the user's program where `unwrap` was invoked. For a program with hundreds of `unwrap()` calls, this is almost useless: the programmer must rerun with `RUST_BACKTRACE=1`, and then find the right frame in a long trace, which may not exist at all in release builds where debug information is stripped.

The cause is simple. `panic!` records the location of the macro invocation, and the invocation is inside `unwrap`. For ordinary functions that is exactly what a programmer wants. For functions whose entire purpose is to panic on behalf of a caller, the interesting location is that of the caller.

Several workarounds exist and all are unsatisfying:

- Replace `unwrap()` with `expect("some message")` everywhere. This is verbose and the message must be unique to find a call site.
- Turn every such function into a macro. Macros capture `file!()` and `line!()` at the call site, but they lose type inference, method syntax and ordinary scoping.
- Use `#[inline(always)]`. This does not change what location `panic!` records.

We want these functions to remain ordinary functions yet report the caller's location.

## Guide-level explanation

### Let's reimplement `unwrap()`

Consider a hypothetical version of `Option::unwrap`:

```rust
impl<T> Option<T> {
    pub fn unwrap(self) -> T {
        match self {
            Some(t) => t,
            None => panic!("called `Option::unwrap()` on a `None` value"),
        }
    }
}
```

The panic reports the line inside `unwrap`. To fix this, annotate the function:

```rust
impl<T> Option<T> {
    #[track_caller]
    pub fn unwrap(self) -> T {
        match self {
            Some(t) => t,
            None => panic!("called `Option::unwrap()` on a `None` value"),
        }
    }
}
```

Now, the panic reports the line in the user's code that called `unwrap`.

### Track the caller

A function with `#[track_caller]` is given a hidden extra piece of information: the source location of the call expression that invoked it. Inside the function, `Location::caller()` returns this value:

```rust
#[track_caller]
fn log(msg: &str) {
    let loc = Location::caller();
    eprintln!("[{}:{}] {}", loc.file(), loc.line(), msg);
}
```

The `panic!` macro itself uses `Location::caller()` when its enclosing function is tracked, so panics inside a tracked function report the caller automatically.

### Location type

`Location` is a small, `Copy` type with accessors for `file()`, `line()` and `column()`. It is the same type that `PanicInfo::location()` already returns, so existing panic hooks continue to work.

### Propagation of tracker

If a tracked function calls another tracked function, the caller location is propagated rather than replaced. The inner function reports the location where the *outermost* tracked function was called:

```rust
#[track_caller]
fn outer() { inner() }

#[track_caller]
fn inner() { println!("{}", Location::caller()); }

fn main() {
    outer(); // prints the location of this line
}
```

If the intermediate function were not annotated, `inner` would report the line inside `outer`. This lets library authors choose where to stop attribution.

### Why do we use implicit caller location

An alternative is to make the location an explicit parameter. This makes signatures noisy and breaks trait implementations, for example `Index::index` and `Deref::deref`, where the signature is fixed by the trait. Because the argument is implicit, adding `#[track_caller]` is a non-breaking change in terms of function signatures and type checking, though not in terms of function pointer behavior; see below.

## Reference-level explanation

### Survey of panicking standard functions

The functions that benefit most are:

- `Option::{unwrap, expect}`
- `Result::{unwrap, expect, unwrap_err, expect_err}`
- `Index::index` implementations for slices, `Vec`, `str`, and `HashMap`
- `RefCell::{borrow, borrow_mut}`
- arithmetic operators in debug mode (overflow checks)
- `slice::split_at`, `Vec::remove`, `Vec::insert`, and similar bounds-checking APIs

### Procedural attribute macro

An early prototype implements `#[track_caller]` as a procedural macro that adds a hidden parameter and rewrites calls. This is rejected for the final design because it cannot work for trait methods, function pointers, or calls through generics.

### Redirection (MIR inlining)

The implementation is a compiler feature. A function marked `#[track_caller]` receives, at the ABI level, one extra trailing argument: a pointer to a static `Location` value. At each call site of a tracked function from an untracked context, the compiler creates a static `Location` for that call expression and passes its address. If the call is within another tracked function, the compiler passes along the incoming pointer.

Calls through a function pointer cannot know which function will be reached. For these, the compiler generates a *shim* that has the ordinary signature, loads the location of the shim's own definition site, and invokes the tracked function. The consequence is that, when a tracked function is coerced to a function pointer, the reported location is the one where the pointer is created or a fixed location, rather than where it is invoked. This is documented as a known limitation.

Trait methods may be annotated in the trait definition or the impl. If annotated in the trait, all implementations are treated as tracked; if an impl is annotated and the trait is not, calls through dynamic dispatch use a shim.

### Standard libraries

The attribute is applied across `core` and `alloc` in the cases surveyed above. Because the attribute does not change visible signatures, this can be done incrementally. Messages remain unchanged, and the location portion of the panic output improves.

### "My fault" vs "Your fault"

The distinction that guides use: when a function panics because the *caller* violated a documented precondition, the caller's location is right. When the function panics because of its own internal bug, the implementation location is better. `#[track_caller]` should be added only to the former. Mixing both in one function is possible by catching the case and calling an untracked helper.

### Location detail control

Embedding file paths in binaries has privacy and reproducibility implications. A compiler flag can control the amount of detail recorded, from full path and line and column, to line and column only, to nothing. This RFC does not specify the flag but requires that the machinery tolerate such a mode, reporting a placeholder location.

## Drawbacks

### Code bloat

Each call site of a tracked function now has one extra argument and, in the worst case, one extra static of roughly 24 bytes. Applied to `unwrap`, which is ubiquitous, this increases both code and data size. Deduplication of identical locations is not possible since each is distinct. In practice the cost is small compared with the debugging benefit, but embedded targets may be concerned.

### Narrow solution scope

The feature targets panic locations. It does not solve broader needs, such as backtrace-like chains of callers, or error values carrying their origin. Users hoping for a richer solution may be disappointed.

### Confusing scoping rule

The propagation rule requires reading both the callee and its callers to understand which location will be reported. A closure inside a tracked function is not itself tracked, so a `panic!` in the closure reports the closure's own location, which surprises some users.

## Rationale and alternatives

### Rationale

Of the alternatives, the compiler-supported implicit parameter is the only one that preserves existing syntax, works through traits, and has modest cost.

### Alternatives

- **Do nothing**, and recommend `expect` with a message.
- **Macros** for every panicking API, which lose type inference, method call syntax and break stable APIs.
- **Full backtraces by default**, which impose a large runtime cost and require debug information.
- **An explicit `&'static Location` parameter**, which pollutes signatures and cannot apply to operators and trait methods.

## Unresolved questions

- Should the attribute be allowed on closures and `async` functions?
- What exactly should happen when a tracked function is used as a function pointer or trait object?
- Should the location detail flag be part of this RFC or a follow-up?

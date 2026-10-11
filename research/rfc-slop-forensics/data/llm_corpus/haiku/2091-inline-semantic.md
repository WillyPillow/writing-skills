# RFC 2091: Accurate Caller Location for Panics via `#[track_caller]`

- Feature Name: `track_caller`
- Start Date: 2017-08-20
- Status: Proposed

## Summary

This RFC makes panic messages point to the place where the user called a function, rather than to a location inside the standard library. The proposal adds a function attribute, `#[track_caller]`, which tells the compiler that a function needs access to information about its caller. It also adds a function, `caller_location()`, which returns the source location of the call site. With these two features, the methods `unwrap` and `expect` on `Option` and `Result` can report the line in the user's code where the panic was triggered, which is the information a developer most needs.

## Motivation

When a program calls `unwrap()` on a `None` value, it panics, and the runtime prints a message. In the current implementation, the message names a location in the source of the standard library, typically a line inside `option.rs` or `result.rs`. The developer sees a path that they did not write and cannot easily navigate to the code that caused the problem.

Developers have worked around this for years by writing their own helper functions that check the value and panic with a clear message. Those helpers are repetitive, and they are not used by the library itself. The result is that most code reports unhelpful locations, and the cost of fixing it falls on every user.

The problem also affects other functions that panic on invalid input, such as indexing helpers and conversion methods. Each of these is a small wrapper around a check, and each would benefit from reporting the caller's location. The proposal aims to fix the family of functions, not just the two methods mentioned above.

## Guide-level explanation

A function marked `#[track_caller]` receives, implicitly, the location at which it was called. Inside the function, the programmer can ask for that location through `Location::caller()`, which returns a value describing a file, line, and column. The function itself does not need to take the location as an argument, and callers do not need to pass it.

```rust
#[track_caller]
fn checked_get(v: &[u32], i: usize) -> u32 {
    if i >= v.len() {
        panic!("index {} out of range", i);
    }
    v[i]
}
```

When a caller in the user's code invokes `checked_get`, the panic message reports the line of that invocation, not the line inside `checked_get`. The information propagates through the chain of calls: if a function marked `#[track_caller]` calls another function that is also marked, the location is forwarded to the outermost call that is not marked.

The standard library functions `unwrap` and `expect` on `Option` and `Result` are marked in this way. A user who calls `unwrap` on a `None` sees the location of their own call.

## Reference-level explanation

The attribute `#[track_caller]` may be applied to a function item, a method, or a closure that is not generic over its caller. The compiler passes an additional hidden argument to such a function, of type `&'static Location<'static>`, which describes the location of the call expression. When the function is called from another `#[track_caller]` function, the hidden argument is forwarded rather than replaced, so the location is that of the outermost non-tracked caller.

The intrinsic `caller_location()` returns the hidden argument as a value of type `&'static Location<'static>`. The safe wrapper is `Location::caller()`, which may only be called from within a function that carries the attribute. Calling it from elsewhere returns the location of the call to `Location::caller()` itself, which is useful for debugging but should not be relied upon.

The `Location` type exposes three accessors: `file()`, `line()`, and `column()`. The file name is the path as written in the source, after applying any path remapping that the build configuration requests. The line and column are one-based.

Attribute propagation follows the call graph. A call from a tracked function to another tracked function forwards the hidden argument. A call from an untracked function supplies the location of the call site. Trait methods are handled by applying the attribute to the implementation, and the attribute on a trait declaration does not propagate automatically unless the implementation also carries it.

Redirection through MIR inlining must preserve the hidden argument. The compiler performs inlining after this information is determined, so the location used in a panic message is the one that the source program specifies, regardless of whether the function is inlined.

## Survey of panicking standard functions

The RFC proposes to mark the following functions: `Option::unwrap`, `Option::expect`, `Result::unwrap`, `Result::expect`, `Result::unwrap_err`, and `Result::expect_err`. The survey found that these account for the large majority of panics originating from library code in typical programs. Indexing operations on slices and vectors are handled by the compiler and are not covered by this attribute.

## Drawbacks

The hidden argument adds a small cost to every call of a tracked function, both in code size and in run time. For most functions this cost is negligible, but for very small functions called in tight loops it may be measurable. The RFC proposes to limit the attribute to functions that panic, which keeps the cost confined.

The scoping rule for the attribute is subtle. A user who expects the location to be the innermost call may be surprised when the outermost call is reported. This is a deliberate choice, since the outermost call is the one the user wrote, but documentation must make it clear.

Narrowing the solution to a single attribute leaves other use cases unaddressed, such as logging helpers that want the caller's location for reasons other than panicking. Those cases can be handled by the same mechanism, but they are not the focus of this RFC.

## Rationale and alternatives

The alternative of passing the location as an explicit argument was considered and rejected. It changes the signature of every affected function, which is a breaking change for public APIs, and it requires every caller to supply the location manually.

Another alternative is a procedural macro that rewrites the body of each function to capture the location at the call site. This approach works without compiler support, but it cannot see the call site, only the definition, and so it cannot produce the required information.

A third option is to leave the standard library unchanged and recommend that users write their own checked helpers. This is the status quo, and it leaves the problem unsolved for the majority of programs that do not do so.

The chosen design follows the principle that the location of a panic should describe the code the programmer controls, and the attribute expresses that intent directly.

## Prior art

Languages with exceptions usually report the throw site, which is the closest analogue to this design. Several compiled languages provide an implicit call-site parameter for diagnostics. The proposal draws on these, but it limits the mechanism to the case that matters most in practice.

## Unresolved questions

- The behavior of `#[track_caller]` on functions that are used as function pointers needs to be specified, including whether the hidden argument is supplied when the pointer is called indirectly.
- The effect on binary size should be measured on a range of real programs before stabilization.
- The name of the intrinsic and the exact visibility of the `Location` constructor may change during implementation.

## Future possibilities

The same mechanism can be used for logging and tracing macros, and for assertion helpers in test frameworks. Those uses would benefit from a stable design, and this RFC provides the foundation for them.

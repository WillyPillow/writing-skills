# Rust RFC 1513: `panic_runtime` — less unwinding

- Start Date: (draft)
- RFC PR: (pending)
- Rust Issue: (pending)

## Summary

Stabilize implementing panics as aborts.

- Stabilize the `-Z no-landing-pads` flag under the name `-C panic=strategy`.
- Implement a number of unstable features akin to custom allocators to swap out implementations of panic just before a final product is generated.
- Add a `[profile.dev]` option to Cargo to configure how panics are implemented.

## Motivation

When a Rust program panics, the default behavior is to unwind the stack. Unwinding runs destructors for every value on each frame between the panic site and the catch point, and it allows a thread to be joined with an error result. This is valuable for many programs, particularly servers and libraries that wish to contain failures. However, unwinding has costs. It requires the compiler to generate landing pads, which are extra code paths that run during an unwind. These pads increase binary size and can inhibit some optimizations, because the compiler must assume that any call might unwind.

Many programs do not use unwinding at all. A command line tool that exits on the first error, or an embedded firmware image that has no operating system to catch a panic, gains nothing from the machinery and pays the cost in size and speed. Such users have asked for a way to choose abort-on-panic behavior without relying on undocumented flags.

The compiler already has an internal flag that disables landing pads, and some users have adopted it through the unstable interface. Using that flag is unsafe in practice, because it changes the behavior of the whole build, including standard library code that may expect to unwind. The RFC seeks to put this capability on a clean footing, with a stable name, a documented meaning, and a mechanism to ensure that the standard library and the program agree on the strategy.

## Guide-level explanation

A user may select the panic strategy with a compiler flag, `-C panic=abort` or `-C panic=unwind`. With `abort`, a panic prints its message and terminates the process immediately, without running destructors or catching the panic. With `unwind`, which is the default, the existing behavior applies.

The strategy can also be set in the Cargo profile for a build. A project may set the panic option in its development or release profile so that the choice travels with the build settings. Cargo ensures that dependencies are built with a compatible strategy, since a crate compiled for unwinding cannot be linked into a program that aborts without care.

Library authors should understand that a library which relies on catching panics with `catch_unwind` will not function in a program compiled with the abort strategy. The documentation of such libraries should state this requirement, and the standard library will document which functions behave differently under each strategy.

## Reference-level explanation

The flag `-C panic=strategy` accepts the values `unwind` and `abort`. The value chosen applies to all crates in the build, including the standard library, which the compiler links in a version matching the requested strategy. The standard library ships with both forms precompiled, so that a user does not need to rebuild it.

When the strategy is `abort`, the compiler does not generate landing pads. A panic calls a function that writes the message to standard error and then calls the process abort routine. Destructors are not run, and `catch_unwind` returns an error only in the sense that it is never reached, since the process has terminated.

Crate metadata records the strategy with which the crate was compiled. When linking, the compiler checks that all crates agree. A crate built with unwinding may not be linked into a program built with abort, unless the crate declares that it does not depend on unwinding. The check prevents a class of linker errors and undefined behavior that would otherwise arise silently.

The panic runtime, the component that implements the panic machinery, is treated as a special crate. Exactly one panic runtime is selected for a final product. A product built with the abort strategy selects the abort runtime, and the proposal provides the mechanism by which this selection happens just before the product is generated, so that libraries need not know which runtime will be used.

The Cargo profile option sets the strategy for the build. It applies to the profile in which it is specified, so that a development build and a release build may differ. Cargo passes the option to the compiler for each crate in the build, and reports a clear error if a dependency has been built with an incompatible strategy and cannot be relinked.

## Drawbacks

The change adds a configuration axis that users must understand. Projects that choose abort must check that their dependencies do not rely on unwinding, and the compiler's checks will catch some but not all cases. A dependency that uses `catch_unwind` for internal recovery may compile and link under abort yet behave differently at runtime.

Abort-on-panic also removes the ability of a server to contain a failure in one request. Projects that depend on that behavior must not choose abort. The RFC recommends that the documentation make this trade-off plain, but cannot prevent misuse.

## Rationale and alternatives

The main alternative is to leave the flag unstable and continue to advise users to rely on it informally. The authors rejected this because the flag has real users, and because unstable flags cannot be relied on in production.

A second alternative is to remove unwinding from the language entirely. This was not considered viable, since unwinding is essential for many uses and is part of the design of the standard library.

A third alternative is to make abort the default. The authors decided against this, because the default should preserve the behavior that most programs expect, and because changing it would break programs that rely on thread recovery.

## Prior art

Other languages handle failure in similar ways. Some systems languages offer a mode in which failures terminate the process, and some offer a choice at build time. The design here follows the common pattern of a compile-time setting that is checked for consistency across the build.

## Unresolved questions

The first question concerns how the panic runtime should be selected when a library is built as a dynamic library, since a dynamic library may be loaded into a program that has made a different choice. The authors suggest that the selection be fixed at link time and that the loader check consistency where the platform allows it.

The second question concerns whether the abort strategy should also change the behavior of the standard library's threads, since the join result of a panicked thread depends on unwinding. The RFC proposes that the thread API document the difference rather than change it.

## Future possibilities

Once the strategy is stable, the compiler could offer finer control, such as aborting only on certain kinds of panic or choosing abort for some crates and unwinding for others with a checked boundary. The panic runtime mechanism could also support user-supplied implementations, which would allow embedded systems to route panic messages to custom hardware without modifying the standard library.

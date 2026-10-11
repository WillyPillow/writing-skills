# Rust RFC 2480: liballoc

- Start Date: 2018-07-24
- RFC PR: (placeholder)
- Rust Issue: (placeholder)

## Summary

This RFC proposes to stabilize the `alloc` crate. The crate contains the part of the standard library that depends on a global heap allocator and on an allocation error handler, but that does not depend on operating system services. Stabilizing it makes the crate available to users who write code for environments that have an allocator but no operating system, such as embedded systems with a heap, kernels, and bare-metal runtimes that provide a custom allocator. The RFC describes the contents of the crate, the stability guarantees it would offer, and the changes needed in the surrounding ecosystem.

## Motivation

The Rust standard library is organized in layers. The `core` crate contains the language's essential types and operations and requires no allocator and no operating system. The `std` crate builds on `core` and adds everything that needs an operating system, such as files, threads, networking and the process environment. Between these two layers sits a set of types that need dynamic memory but nothing else: `Vec`, `String`, `Box`, `Rc`, `Arc`, and the collections such as `BTreeMap`. Today these types are only reachable through `std`, which means that a program that wants them must pull in the operating system interface even when it does not use it.

This has real costs. Code for embedded targets that have a heap but no operating system must either avoid these types or reimplement them. Libraries that want to offer collection types without assuming a host are forced to write their own. Crates that are logically portable therefore fragment into versions that differ only in which collections they use.

The `alloc` crate addresses this by providing the heap-dependent types in a crate that depends on the allocator but not on the operating system. Programs that have a global allocator can link `alloc` directly, and programs that also have an operating system can continue to use `std`, which re-exports everything in `alloc`.

## Guide-level explanation

A program that is built without the standard library declares that it uses the `alloc` crate and provides a global allocator. The allocator is a type that implements the `GlobalAlloc` trait and is marked with an attribute. The program also provides an error handler for the case in which an allocation fails. Once these are in place, the program may use `Vec`, `String`, `Box` and the other types from `alloc` in the same way that a program using `std` would use them.

```rust
#![no_std]
extern crate alloc;

use alloc::vec::Vec;

fn collect_squares(n: u32) -> Vec<u32> {
    (0..n).map(|i| i * i).collect()
}
```

The paths of the types in `alloc` match the paths of the same types in `std`. A library written against `alloc` can therefore be used by a program that uses `std`, because `std` re-exports the same items. This is the main property the RFC is designed to preserve.

## Reference-level explanation

The crate contains the following groups of items. The smart pointer types `Box`, `Rc` and `Arc` are included, along with the associated weak pointer types. The growable containers `Vec` and `VecDeque` are included, along with `String`. The ordered and unordered collections `BTreeMap`, `BTreeSet`, `LinkedList` and the other collections that allocate are included. The traits `ToOwned`, `ToString` and `Cow` are included, as are the formatting helpers that produce owned strings.

The crate does not contain anything that requires an operating system. Items such as file handles, environment variables, time sources based on the system clock, and threads are not present. Items that depend on a panic handler are present only if the panic handler is declared by the final program, and the crate does not supply one.

The allocation error handler is a function with a fixed signature that the program defines with an attribute. When an allocation fails in an infallible operation, the runtime calls this function, which is expected not to return. The default behavior when no handler is present is a compile-time or link-time error, not a silent fallback.

The stability of the crate follows the stability of the standard library. Items that are stable in `std` are stable in `alloc`, and the signatures are identical. Items that are unstable in `std` remain unstable in `alloc`, and the RFC does not propose to stabilize any item that is not already stable in the standard library, except for the allocator and error handler interfaces.

## Drawbacks

Stabilizing `alloc` commits the project to supporting a crate whose contents must be kept in sync with `std`. Any change to a type that lives in `alloc` must also be reflected in the re-export in `std`, and the boundary between the two crates must be maintained as the library grows.

The allocator interface is a fixed point that is harder to change after stabilization. If the global allocator trait needs a new method or a different signature, the change must be made compatibly, and this may limit what can be done in the future.

There is also a risk that users will misjudge the properties of code that uses `alloc`. A program that links `alloc` still may not be suitable for a target where allocation can fail in unexpected ways, and the documentation must make clear what the error handler is for.

## Rationale and alternatives

The alternative of leaving the heap-dependent types only in `std` was rejected because it forces embedded and kernel users to fork the standard library or to write their own collections. Several third-party crates already do this, and the result is duplication of effort and incompatible types.

Another alternative was to split the standard library into many small crates, one per type. This was judged too fine-grained, because it would make the dependency graph difficult to understand and would complicate the re-exports. A single crate with a clear boundary is easier to document and to test.

A third alternative was to move the allocation error handler into `core`. This was rejected because `core` is meant to be usable without any allocator, and the handler concerns only code that allocates.

The chosen design keeps the boundary simple: `core` for code without allocation, `alloc` for code with allocation but no operating system, and `std` for everything else.

## Prior art

Many other systems languages provide a similar layering. Their standard libraries typically separate code that needs no runtime, code that needs a heap, and code that needs an operating system. The experience of those languages suggests that the middle layer is valuable mainly when its boundary is clearly documented and when the allocator interface is kept small.

## Unresolved questions

The exact set of items to stabilize in the first release is still under discussion. Some collections have unstable APIs that have not been reviewed for use in constrained environments, and these may be left unstable until the review is complete.

It is not yet decided how the crate should behave on targets where the allocator can be replaced at run time. The current design assumes a single global allocator that is fixed when the program is built.

## Future possibilities

Once `alloc` is stable, it becomes easier to add heap-dependent types to the standard library without requiring them to be part of `std`. It also becomes possible for the ecosystem to write libraries that are generic over the presence of an operating system, which would reduce the number of crates that exist in parallel for embedded and hosted targets.

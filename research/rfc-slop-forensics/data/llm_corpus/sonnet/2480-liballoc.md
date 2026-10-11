- Feature Name: `alloc`
- Start Date: 2018-06-12
- RFC PR: rust-lang/rfcs#2480
- Rust Issue: rust-lang/rust#27783

# Summary
[summary]: #summary

Stabilize the `alloc` crate.

This crate provides the subset of the standard library's functionality that requires a global allocator (unlike the `core` crate) and an allocation error handler, but not other operating system capabilities (unlike the `std` crate).

# Motivation
[motivation]: #motivation

## Background

The standard library is split into layers. The `core` crate has no dependency on the operating system or on heap allocation. It provides primitive types, traits such as `Iterator` and `Clone`, `Option`, `Result`, `fmt`, slices, and atomics. The `std` crate sits on top, adds the operating system interfaces (files, threads, networking, time) and re-exports everything from `core` and from a middle layer.

That middle layer is the `alloc` crate. It holds `Box`, `Rc`, `Arc`, `Vec`, `String`, `BTreeMap`, `BTreeSet`, `BinaryHeap`, `LinkedList`, `VecDeque`, `Cow`, the `format!` and `vec!` macros, and the traits and types around allocation. It depends on `core` and on the existence of a global allocator, but not on an operating system.

The `alloc` crate exists today and is used internally by `std`. It is available on nightly, behind `#![feature(alloc)]`. It has not been stabilized, which means that stable Rust code cannot use it.

## The problem

Programs and libraries targeting environments without an operating system, such as embedded firmware, kernels, bootloaders and WebAssembly modules that avoid the standard library, are written with `#![no_std]`. In that mode only `core` is available by default. Developers in these environments very often have a heap, because they provide an allocator themselves, and they want `Vec` and `String`. Without a stable `alloc`, their choices are:

1. Stay on the nightly compiler.
2. Reimplement collections by hand.
3. Use a third-party crate that copies the standard library collections, which fragments the ecosystem and creates types that do not interoperate with the standard ones.

Each of these has real costs. A library that wants to work both with and without `std` currently needs a nightly feature gate, which forces its users onto nightly as well. Since libraries are dependencies of other libraries, this requirement spreads transitively.

Stabilizing `alloc` removes this barrier. A crate can say `extern crate alloc;`, use `alloc::vec::Vec`, and be usable from `no_std` environments on the stable compiler.

# Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

The `alloc` crate is the part of the standard library that needs a heap. To use it in a `#![no_std]` crate:

```rust
#![no_std]

extern crate alloc;

use alloc::vec::Vec;
use alloc::string::String;
use alloc::boxed::Box;

pub fn greet(name: &str) -> String {
    let mut s = String::from("Hello, ");
    s.push_str(name);
    s
}
```

If your crate is built with `std` available, the same types are re-exported from `std`, and they are identical types. A `Vec<u8>` from `alloc` is the same type as `std::vec::Vec<u8>`. There is no conversion cost, and a library written against `alloc` can interoperate with callers that use `std`.

## Providing a global allocator

A binary that uses `alloc` without `std` must provide a global allocator. This is done with the `#[global_allocator]` attribute, which was stabilized earlier, applied to a static of a type that implements `GlobalAlloc`:

```rust
use core::alloc::{GlobalAlloc, Layout};

struct MyAllocator;

unsafe impl GlobalAlloc for MyAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 { /* ... */ }
    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) { /* ... */ }
}

#[global_allocator]
static A: MyAllocator = MyAllocator;
```

Library crates do not need to do this. Only the final binary does. A library that depends on `alloc` simply requires that whoever links it supplies one.

## Handling allocation failure

When an allocation fails, the standard collections call an allocation error handler, which by default aborts or panics. In `std`, this prints a message and aborts the process. In `no_std` binaries that use `alloc`, the program must provide the handler. This RFC does not stabilize a mechanism for customizing the handler beyond what exists; it proposes that `alloc` be stabilized with the current requirement being met in whichever way is currently supported, and that the handler customization be handled separately.

## Libraries that support both modes

The typical pattern is a crate with a `std` feature:

```rust
#![cfg_attr(not(feature = "std"), no_std)]

#[cfg(not(feature = "std"))]
extern crate alloc;
#[cfg(feature = "std")]
use std as alloc;
```

With this, `alloc::vec::Vec` works in both configurations.

# Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

## What is stabilized

The following modules and items of `alloc` are stabilized, with their current names and the stability attributes they already carry in `std`:

- `alloc::alloc` (`alloc`, `dealloc`, `realloc`, `alloc_zeroed`, `Layout` re-exported from `core::alloc`, `GlobalAlloc`, `handle_alloc_error`)
- `alloc::borrow` (`Cow`, `ToOwned`, `Borrow` re-exported)
- `alloc::boxed` (`Box`)
- `alloc::collections` (`BTreeMap`, `BTreeSet`, `BinaryHeap`, `LinkedList`, `VecDeque`, and the associated iterators and entry types)
- `alloc::fmt` (`format`, and re-exports of the `core::fmt` items)
- `alloc::rc` (`Rc`, `Weak`)
- `alloc::slice` (the extension methods that allocate, such as `to_vec`, `concat`, `join`, `sort`)
- `alloc::str` (the methods that allocate, such as `to_owned`, `repeat`, `to_lowercase`)
- `alloc::string` (`String`, `ToString`)
- `alloc::sync` (`Arc`, `Weak`)
- `alloc::vec` (`Vec`, `IntoIter`, `Drain`)

The macros `format!` and `vec!` are exported from the crate root.

`HashMap` and `HashSet` are not in `alloc`. They depend on a source of randomness for their default hasher, which is an operating system capability, and thus remain in `std`.

## Re-exports from std

The `std` crate re-exports each of the above from `alloc`, at the same paths as today. Existing code that names `std::vec::Vec` continues to compile and refers to the same type.

## Inherent methods on primitives

Some inherent methods on `[T]` and `str` allocate and thus can't live in `core`. These are implemented in `alloc` using the `#[lang]` item mechanism, as they are today. Their stability is unchanged; they remain usable via `std` and become usable via `alloc` in `no_std` crates through the prelude of `std` or by importing the extension traits. Since inherent impls on primitives can only appear in the crate that holds the lang item, the methods are available in any crate that links `alloc`, without an import.

## Stability of the crate name

The crate is named `alloc`. Extern crate declarations of the form `extern crate alloc;` become stable. No additional feature gate is needed.

# Drawbacks
[drawbacks]: #drawbacks

**Larger stable surface.** Stabilizing the crate does not add new items, because every item is already stable via `std`. It does add a new path by which they can be named, and it commits the project to keeping the facade structure.

**Constrains the layering of std.** The division between `core`, `alloc` and `std` becomes part of the public contract. If the team later wanted to move an item between layers, it could re-export it so that paths do not break, but the constraint is real.

**Allocation error handling is incomplete.** Programs that cannot abort on allocation failure need fallible APIs, such as `try_reserve`, which are still being designed. Stabilizing `alloc` before they land gives `no_std` users the same infallible-by-default collections as `std` users, with the same weakness.

# Rationale and alternatives
[rationale-and-alternatives]: #rationale-and-alternatives

**Do nothing.** The ecosystem remains split between nightly-only `no_std` + `alloc` users and everybody else.

**Stabilize a smaller set.** One could stabilize only `Vec`, `String` and `Box`. This is easy to explain but arbitrary, and the remaining types would still have to be reachable somehow.

**Provide the types in core with a generic allocator parameter.** Types parameterized over an allocator are a more flexible design and are being explored separately. This RFC does not preclude it, and the stabilized paths would stay valid if it lands.

# Prior art
[prior-art]: #prior-art

C++ has the freestanding and hosted split, where freestanding implementations offer a subset of the library. Rust's layering is finer-grained, because it distinguishes between environments with and without a heap.

# Unresolved questions
[unresolved-questions]: #unresolved-questions

- How should the allocation error handler be customized on stable?
- Should the crate be re-exported under another name for people who already have a local module named `alloc`?

# Future possibilities
[future-possibilities]: #future-possibilities

Fallible allocation APIs, allocator-generic collections and a stable `#[alloc_error_handler]` attribute are natural follow-ups.

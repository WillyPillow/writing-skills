- Feature Name: `liballoc`
- Start Date: 2018-06-14
- RFC PR: [rust-lang/rfcs#2480](https://github.com/rust-lang/rfcs/pull/2480)
- Rust Issue: (to be created)

# Summary
[summary]: #summary

Stabilize the `alloc` crate. This crate provides the part of the standard library's functionality that needs a global allocator and an allocation error handler (which `core` does not have) but no other operating system capabilities (which `std` provides).

# Motivation
[motivation]: #motivation

Rust's standard library is split into layers:

- `core` has no dependencies at all. It provides primitive types, traits like `Iterator` and `Clone`, `Option`, `Result`, slices, `str`, and so on. It runs anywhere, including on bare metal with no heap.
- `std` depends on an operating system. It provides files, threads, networking, processes, environment variables, and also all the heap-allocated collections.

Between these two sits a large population of targets and programs: embedded firmware, kernels, bootloaders, WebAssembly modules without WASI, and libraries that want to be usable in all of those places. They have a heap, because someone has written an allocator for them, but they have no operating system. Today, such programs can use `#![no_std]` and get only `core`, or use `std` and fail to build for their target.

Inside the standard library, the heap-dependent types such as `Box`, `Vec`, `String`, `Rc`, `Arc`, `BTreeMap` and `VecDeque` already live in a separate crate called `alloc`, and `std` re-exports them. That crate is available on nightly as `extern crate alloc;` behind the `alloc` feature gate. In practice a large part of the `no_std` ecosystem already uses it, which means it requires nightly for no reason other than the feature gate.

The pieces needed to make `alloc` usable on stable have recently landed or are about to:

- `#[global_allocator]` and the `GlobalAlloc` trait are stable (Rust 1.28), so a `no_std` program can supply its own allocator.
- The allocation error handler, which `alloc` calls when allocation fails, can be defined with `#[alloc_error_handler]` (tracked separately).

What remains is to stabilize the crate itself.

Library authors benefit most. A crate that needs `Vec` but nothing else from `std` can declare `#![no_std]`, depend on `alloc`, and work in every environment, with no `std` feature flag and no conditional re-exports.

# Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

In a `#![no_std]` crate, add:

```rust
#![no_std]

extern crate alloc;

use alloc::vec::Vec;
use alloc::string::String;
use alloc::boxed::Box;
```

You can now use heap-allocated types exactly as you would with `std`. `std::vec::Vec` and `alloc::vec::Vec` are the same type; `std` simply re-exports `alloc`'s contents. Code that uses `alloc` paths therefore works unchanged whether or not the final binary links `std`.

A binary that uses `alloc` without `std` must provide a global allocator:

```rust
#[global_allocator]
static ALLOCATOR: MyAllocator = MyAllocator::new();
```

It must also provide an allocation error handler. Programs that link `std` get both automatically.

Libraries that are `no_std` + `alloc` do not provide either. They leave it to the final binary.

Note that `alloc` is not in the prelude of a `no_std` crate. You must `use` the items you need. `vec!` and `format!` are available as `alloc::vec!` and `alloc::format!`.

# Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

## Stable modules

The following modules of `alloc` become stable, with the same contents that `std` re-exports at the same paths:

- `alloc::boxed`
- `alloc::rc`
- `alloc::sync` (only on targets with atomic pointer operations)
- `alloc::vec`
- `alloc::string`
- `alloc::str` (the allocation-dependent `str` methods and `ToOwned`-related items)
- `alloc::slice` (sorting, `to_vec`, `concat`, `join`)
- `alloc::borrow` (`Cow`, `ToOwned`)
- `alloc::collections`, containing `BTreeMap`, `BTreeSet`, `BinaryHeap`, `LinkedList`, `VecDeque`, and the module-level iterators
- `alloc::fmt` (`format` function, `format!` macro support, re-exports of `core::fmt`)
- `alloc::alloc`, containing the `GlobalAlloc` re-export, `Layout`, `alloc`, `dealloc`, `realloc`, `alloc_zeroed`, and `handle_alloc_error`

The `vec!` and `format!` macros are exported from the crate root.

Any item that is stable in `std` at a re-exported path is stable at the corresponding `alloc` path. Items that are unstable in `std` remain unstable in `alloc`.

## What is not included

`HashMap` and `HashSet` are not part of this stabilization. They live in `std` because their default hasher, `RandomState`, needs a source of randomness from the operating system. Moving the hash table implementation into `alloc` without a default hasher is a reasonable follow-up but is outside the scope of this RFC.

`std::io`, `std::error::Error` and similar types are also not in `alloc` today. Some of them could move in future; this RFC does not commit to that.

## Relationship to `std`

`std` continues to re-export everything listed above. Types are identical, not just equivalent, so trait impls and type identities carry over. A library depending on `alloc` can be used by a binary depending on `std` with no conversion.

## Linking `alloc`

`alloc` is part of the sysroot. Like `core`, it does not need to appear in `Cargo.toml`. `extern crate alloc;` is required in Rust 2015 and Rust 2018 because `alloc` is not in the extern prelude for `no_std` crates. Adding it to the extern prelude is a possible future change.

## Missing allocator or error handler

If a binary links `alloc` but not `std` and does not define a `#[global_allocator]`, linking fails with an error explaining that a global allocator is needed. The same applies to the allocation error handler. These diagnostics are improved as part of this work.

# Drawbacks
[drawbacks]: #drawbacks

- **Another public crate in the standard distribution.** Users now face three crates instead of two and need to know where each item lives. The rule is short ("needs heap but not OS → `alloc`") but must be learned.
- **Commits to the split.** Once `alloc` is stable, moving an item from `alloc` up to `std` is breaking. Moving items down from `std` to `alloc` remains possible, as does moving items from `alloc` to `core`, provided re-exports are kept.
- **The allocation error handler is not yet stable.** Until it is, `no_std` binaries that use `alloc` still need nightly. Libraries, however, benefit immediately.

# Rationale and alternatives
[rationale-and-alternatives]: #rationale-and-alternatives

**Merge `alloc` into `core` behind a feature or cfg.** This would avoid a third crate but would make `core` depend on an allocator, either always or conditionally. Conditional APIs in `core` are hard to document and to reason about.

**Use Cargo features on `std`** ("std without OS"). This requires building `std` from source with different configurations, which Cargo does not yet support well, and the resulting crate name is the same for two very different sets of capabilities, which confuses diagnostics.

**Leave it unstable.** The `no_std` ecosystem continues to require nightly for basic collections, which is the situation this RFC exists to fix.

**Wait for a fully redesigned allocator API** (the `Alloc` trait, allocator-generic collections). That work is valuable but much larger. Stabilizing `alloc` with the global allocator does not prevent it. Allocator parameters can be added to collections later with defaults.

# Prior art
[prior-art]: #prior-art

C has a similar informal split: freestanding implementations provide a small subset of the library, and hosted implementations provide the rest. `malloc` sits awkwardly in between and is often provided by a separate library in embedded environments. C++ has freestanding and hosted implementations with a defined set of headers for each, and recent proposals extend the freestanding subset.

Within Rust, the `core`/`std` split itself and the `#[global_allocator]` stabilization are the direct precedents.

# Unresolved questions
[unresolved-questions]: #unresolved-questions

- Should `alloc` be added to the extern prelude so `extern crate alloc;` is unnecessary in Rust 2018?
- Should `HashMap` without a default hasher move to `alloc` as part of this RFC or a separate one?
- What is the timeline for stabilizing the allocation error handler, so that `no_std` binaries (not just libraries) work on stable?

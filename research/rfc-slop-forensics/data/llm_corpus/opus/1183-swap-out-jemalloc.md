- Feature Name: `allocator`
- Start Date: 2015-06-27
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

> **Note:** this RFC has been superseded by RFC 1974.

# Summary

Add compiler support for overriding the default allocator, so that a Rust program can use a different allocator by default. Also change the default allocator for dynamic and static libraries from jemalloc to the system `malloc`.

# Motivation

Every Rust program built with the standard toolchain today links jemalloc and routes every heap allocation through it: `Box`, `Vec`, `String`, and all the rest. jemalloc is a fine allocator with good performance for many workloads, but making it mandatory causes several problems.

**Libraries embedded in other programs.** When Rust code is compiled to a `staticlib` or `dylib` and linked into a C, C++, Python, or Ruby program, the host program already has an allocator. Bringing a second one in:

- adds a few hundred kilobytes to the binary;
- means memory allocated on one side of the FFI boundary cannot safely be freed on the other side, even when both sides believe they are using `malloc`;
- makes memory-debugging tools such as Valgrind, AddressSanitizer, and platform heap profilers less effective, because they hook the system allocator and do not see jemalloc's allocations;
- can conflict with a host that also links its own copy of jemalloc, with different configuration or symbol prefixes.

**Platforms without jemalloc.** Some targets, especially embedded and newer ones, do not support jemalloc well or at all. Each such target needs special cases in the build system today.

**Users who want a different allocator.** Applications with unusual allocation patterns may do better with tcmalloc, a bump allocator, a debugging allocator that tracks leaks, or simply the system allocator. Today, switching requires a custom build of the standard library.

**Reproducibility and auditing.** Some deployments require that every allocation go through the platform allocator for security hardening or compliance reasons.

There needs to be a supported way to say "use this allocator" without rebuilding `std`, and the default for libraries should be the system allocator.

# Detailed design

## Allocator crates

An *allocator crate* is a crate marked with the `#![allocator]` attribute. It must define the following functions with these exact names and signatures, and with no mangling:

```rust
#![allocator]
#![no_std]

#[no_mangle]
pub extern fn __rust_allocate(size: usize, align: usize) -> *mut u8;

#[no_mangle]
pub extern fn __rust_deallocate(ptr: *mut u8, old_size: usize, align: usize);

#[no_mangle]
pub extern fn __rust_reallocate(ptr: *mut u8, old_size: usize,
                                size: usize, align: usize) -> *mut u8;

#[no_mangle]
pub extern fn __rust_reallocate_inplace(ptr: *mut u8, old_size: usize,
                                        size: usize, align: usize) -> usize;

#[no_mangle]
pub extern fn __rust_usable_size(size: usize, align: usize) -> usize;
```

These match the low-level allocation functions that `liballoc` calls today. An allocator crate:

- must be `#![no_std]`, or must otherwise avoid depending on `liballoc`, because `liballoc` depends on it and the dependency cannot be circular;
- may depend on `libcore` and `liblibc`;
- must not itself allocate through Rust's heap.

## Declaring a dependency on an allocator

`liballoc` declares that it *needs* an allocator but does not name a specific one. It is marked with a new attribute:

```rust
#![needs_allocator]
```

Any crate that transitively depends on a `#![needs_allocator]` crate must, when the final artifact is linked, have exactly one allocator crate linked in.

## How the compiler chooses an allocator

When the compiler produces a final artifact (an executable, `dylib`, or `staticlib`), it looks at the dependency graph:

1. If exactly one allocator crate is explicitly linked, through `extern crate` anywhere in the graph, that allocator is used.
2. If more than one allocator crate is explicitly linked, compilation fails with an error naming the conflicting crates.
3. If none is explicitly linked, the compiler picks a default based on the kind of output:
   - **executables:** `alloc_jemalloc` on platforms that support it, otherwise `alloc_system`;
   - **`dylib` and `staticlib`:** `alloc_system`.

Intermediate `rlib` crates never pick an allocator. The choice is made only once, when linking the final artifact.

## Standard allocator crates

The distribution ships two allocator crates:

- `alloc_jemalloc` wraps the bundled jemalloc, as today.
- `alloc_system` calls the platform allocator: `malloc`/`free`/`realloc` with `posix_memalign` on Unix, and `HeapAlloc` and friends on Windows. For alignments larger than the platform guarantees, it over-allocates and adjusts the pointer.

Both are unstable to name directly for now, so selecting one explicitly requires nightly.

## Example

A user who wants the system allocator in an executable writes:

```rust
#![feature(alloc_system)]
extern crate alloc_system;

fn main() {
    let v = vec![1, 2, 3]; // allocated with malloc
}
```

A user with a custom allocator writes a crate:

```rust
#![feature(allocator)]
#![allocator]
#![no_std]

extern crate libc;

#[no_mangle]
pub extern fn __rust_allocate(size: usize, align: usize) -> *mut u8 {
    // call into the custom allocator
}
// ... remaining functions
```

and links it with `extern crate my_allocator;` from the executable.

# Drawbacks

**Performance regression for libraries.** Some libraries that are currently fast because of jemalloc will get slower on platforms whose system allocator is weaker, notably older glibc versions and Windows. Library authors can opt back into jemalloc, but only on nightly until the attributes stabilize.

**Global, link-time choice.** The allocator is chosen once for the whole program. There is no way to use different allocators for different collections. This RFC does not attempt to solve that problem, which is better handled by allocator-parameterized collections in the future.

**Linking surprises.** Because the choice depends on the output type, the same code can use different allocators when built as an executable and when built as a library. This could confuse people investigating performance.

**Symbol-based interface.** The interface depends on `#[no_mangle]` symbols with fixed names. That is simple but provides no type checking between `liballoc` and the allocator crate, and the names become a compatibility commitment.

# Alternatives

**Keep jemalloc everywhere.** This ignores the problems with embedding and platform support.

**Switch everything to the system allocator.** This is simpler but would regress performance for executables on platforms where jemalloc is significantly faster.

**A Cargo-level setting.** An allocator could be selected through `Cargo.toml` instead of `extern crate`. This would be more discoverable but would tie a compiler feature to Cargo and would not help users who invoke `rustc` directly.

**A trait-based global allocator.** Instead of fixed symbol names, allocator crates could implement a trait and register a static. This is more idiomatic and type-safe, and a future RFC could move in that direction. It requires more design work than this RFC tries to do.

# Unresolved questions

- What is the path to stabilizing allocator selection? Should stable Rust be able to choose between `alloc_system` and `alloc_jemalloc` before custom allocators are stable?
- How should allocator crates report out-of-memory conditions? Currently a null return makes `liballoc` abort.
- Should `__rust_usable_size` and `__rust_reallocate_inplace` remain mandatory, or should they get default implementations?

# RFC 1183: allocator

- Start Date: 2015-08-04
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

> **Note:** this RFC has been superseded by RFC 1974.

## Summary

Add support to the compiler to override the default allocator, allowing a different allocator to be used by default in Rust programs. Additionally, also switch the default allocator for dynamic libraries and static libraries to using the system malloc instead of jemalloc.

## Motivation

Rust currently ships with jemalloc as the allocator for every Rust program, and the allocator is linked into every artifact that the compiler produces. This has several consequences, some good and some less so.

**Performance.** jemalloc is a high-quality allocator with good behavior under multithreaded workloads and low fragmentation. For executables, which own the whole process, this is a clear advantage.

**No choice.** A program that would prefer a different allocator has no supported way to say so. Reasons are plentiful: a specialized allocator such as tcmalloc may fit a workload better, a debugging allocator might be needed to find memory errors, an embedded or kernel target may need a custom arena, and a user running on a platform where jemalloc is poorly supported may simply want the system one. Today the only recourse is to patch the compiler or to bypass `Box` and `Vec` altogether.

**Embedding.** When a Rust library is built as a `cdylib` or `staticlib` and loaded by a host program written in C, C++, Ruby, Python, or something else, the host already has an allocator. Bringing a second one into the process creates difficulty. Two allocators may interact badly if memory crosses the boundary, even where the interface is designed to prevent that. Symbol conflicts with a host that also uses jemalloc, and increased binary size, are further complaints. On some platforms, such as Windows with multiple C runtimes, the situation is especially fragile.

**Tooling.** Valgrind and similar tools understand the system `malloc` but see jemalloc as an opaque pool. This reduces the usefulness of memory-error detection on Rust programs.

These concerns suggest two separate changes: allow the allocator to be replaced, and choose different defaults for the artifacts where the Rust code is a guest and not the owner of the process.

## Detailed design

### Allocator crates

An allocator is a crate that provides a defined set of functions. This RFC specifies them as a set of unmangled `extern` symbols, so the interface is a stable ABI that does not depend on Rust's own types:

```rust
extern {
    fn __rust_allocate(size: usize, align: usize) -> *mut u8;
    fn __rust_deallocate(ptr: *mut u8, old_size: usize, align: usize);
    fn __rust_reallocate(ptr: *mut u8, old_size: usize, size: usize, align: usize) -> *mut u8;
    fn __rust_reallocate_inplace(ptr: *mut u8, old_size: usize, size: usize, align: usize) -> usize;
    fn __rust_usable_size(size: usize, align: usize) -> usize;
}
```

These functions take the size and alignment of the allocation, unlike C's `free`, which takes only the pointer. Rust always knows the layout of what it is freeing, and passing it allows allocators to avoid storing it.

A crate marked with the unstable attribute `#![allocator]` declares that it implements these functions. Such a crate has some restrictions. It may not depend on `std`, since `std` itself depends on the allocator. It may depend on `core` and on other crates that do not themselves allocate.

### Selecting an allocator

The compiler gains a notion of "the allocator for this artifact." The choice is made at the final link step, which is the only point at which all the crates in the dependency graph are known. A user selects an allocator by linking an allocator crate into the final artifact:

```rust
extern crate my_allocator;
```

If an artifact links exactly one allocator crate, it is used by all Rust code in that artifact, including the standard library. If it links more than one, the compiler reports an error. If it links none, the default for the artifact type is chosen.

Because the standard library does not hard-code its allocator, `liballoc` and everything above it call the `__rust_*` symbols, which are resolved at link time.

### Defaults by artifact type

The default allocator depends on the output type of the final artifact:

- **Executables** use jemalloc as they do today.
- **Dynamic libraries (`dylib` and `cdylib`) and static libraries (`staticlib`)** use the system allocator: `malloc` and `free` on Unix-like platforms, and `HeapAlloc` on Windows.

Two crates are provided with the distribution: `alloc_jemalloc` and `alloc_system`. The compiler chooses between them. A user can override either default by naming an alternative allocator crate.

The system allocator crate maps the `__rust_*` interface onto platform functions. For alignments no greater than the guaranteed alignment of `malloc`, it calls `malloc` and `free` directly. For larger alignments it uses `posix_memalign` where available, or an over-allocation scheme where it is not. `__rust_reallocate_inplace` returns the old usable size without doing anything, which is a legal behavior of that function.

### Interaction with `rlib` and `dylib` dependencies

Intermediate `rlib` artifacts do not choose an allocator, since they are not final. They record only that they depend on the allocator interface. The final artifact's link step provides the symbols.

A subtle case arises when a `dylib` is linked into an executable: the `dylib` has already chosen its allocator when it was built. If the two disagree, memory allocated in one and freed in the other would be returned to the wrong allocator. The compiler therefore requires that all dynamically linked Rust code in a process agree on the allocator, and reports a link-time error when it does not. Since `dylib`s built by default use the system allocator, mixing them into executables that default to jemalloc would be an error; the compiler resolves this by making an executable that links a Rust `dylib` use the allocator of the `dylib` unless the user overrides it.

## Drawbacks

- The allocator interface is a new piece of public API surface, even if unstable. Its design must anticipate future needs, such as a fallible `allocate`, and this RFC does not attempt to settle those.
- Having a different default for executables and for libraries makes the behavior of a program depend on artifact type, which could surprise users who move code between the two.
- Changing library defaults to the system allocator gives up some of jemalloc's performance in those cases. For most FFI-based embedding, allocation performance is not the bottleneck.
- Allowing arbitrary allocators means that bugs in a custom allocator can corrupt the entire program, including the standard library.

## Alternatives

**Keep jemalloc everywhere.** This is the simplest option, but it leaves unaddressed the complaints about embedding and debugging.

**Use the system allocator everywhere.** This gives up jemalloc's benefits for executables, which is where most users are measuring Rust's performance.

**A runtime-registered allocator.** Instead of linking, a user could call a function at startup to install a global allocator. This is more flexible but introduces an ordering problem, since allocation may occur before registration, and a runtime indirection cost on every allocation.

**A trait-based allocator.** An `Allocator` trait with a `#[global_allocator]` static would be more idiomatic Rust than a set of unmangled symbols. It is a better long-term design but requires language features not yet available, and the symbol-based approach leaves room to build such an API on top of it later.

**Per-collection allocators.** Making `Vec<T, A>` and `Box<T, A>` parameterized over an allocator is orthogonal; it enables local arenas but does not replace the need for a process-wide choice.

## Unresolved questions

- How should the interface expose failure, for example out-of-memory, so that panics or aborts may be customized?
- What should the stable name and attribute for allocator crates be?
- How does this proposal interact with `no_std` and `#![no_core]` targets that provide no system allocator at all?
- Should `reallocate_inplace` be part of the minimum interface?

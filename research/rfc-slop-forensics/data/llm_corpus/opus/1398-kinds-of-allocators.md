- Feature Name: allocator_api
- Start Date: 2015-12-01
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

Add a standard allocator interface and support for user-defined allocators, with the following goals:

1. Allow libraries (in libstd and elsewhere) to be generic with respect to the particular allocator, to support distinct, stateful, per-container allocators.
2. Require clients to supply metadata (such as block size and alignment) at the allocation and deallocation sites, to ensure hot paths are as efficient as possible.
3. Provide a high-level abstraction over the layout of an object in memory.

Regarding GC: we plan to allow future allocators to integrate themselves with a standardized reflective GC interface, but leave specification of such integration for a later RFC. The design describes a way to add such a feature in the future while ensuring that clients do not accidentally opt in and risk unsound behavior.

# Motivation

Today, every allocation in the standard library goes through a single global allocator. `Box`, `Vec`, `HashMap` and their relatives all call the same functions, and there is no way to ask a particular `Vec` to obtain its memory from somewhere else.

That is fine for most programs, but there are important use cases it does not serve:

- **Arenas and bump allocators.** A compiler, parser or game engine often allocates many short-lived objects with a common lifetime. Allocating them from an arena and freeing the arena in one step is far cheaper than individual frees.
- **Pools of fixed-size objects.** Network servers commonly allocate many buffers of identical size. A pool can satisfy these in constant time with no fragmentation.
- **Instrumentation.** Tracking how much memory a particular subsystem uses is easiest if that subsystem's containers share an allocator that counts.
- **Embedded and kernel code.** Environments without a general-purpose heap still want to use `Vec` and friends with memory carved out of a static region.
- **Specialised memory.** Some data must live in memory with particular properties: pinned for DMA, shared between processes, or allocated on a specific NUMA node.

Users who need these today must reimplement collections from scratch, which wastes effort and produces code that interoperates poorly with the rest of the ecosystem.

C++ has had per-container allocators since its first standard, and its experience is instructive. The original `std::allocator` design was stateless and type-parameterized in a way that made stateful allocators awkward, and later standards spent considerable effort fixing that. We want to learn from that history.

# Detailed design

## `Layout`

An allocation request is described by a `Layout`, which pairs a size with an alignment:

```rust
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub struct Layout {
    size: usize,
    align: usize,
}

impl Layout {
    pub fn from_size_align(size: usize, align: usize) -> Option<Layout>;
    pub fn new<T>() -> Layout;
    pub fn for_value<T: ?Sized>(t: &T) -> Layout;
    pub fn array<T>(n: usize) -> Option<Layout>;
    pub fn size(&self) -> usize;
    pub fn align(&self) -> usize;
    pub fn extend(&self, next: Layout) -> Option<(Layout, usize)>;
    pub fn repeat(&self, n: usize) -> Option<(Layout, usize)>;
    pub fn padding_needed_for(&self, align: usize) -> usize;
}
```

`align` must be a power of two, and `size` rounded up to `align` must not overflow. Constructors that could violate these invariants return `Option`.

The combinators `extend` and `repeat` let code compute the layout of composite structures, such as a header followed by an array, without hand-writing padding arithmetic. `extend` returns the combined layout and the offset at which the second component begins. This is the "high-level abstraction over layout" mentioned in the summary, and it is useful independently of custom allocators.

## The `Allocator` trait

```rust
pub unsafe trait Allocator {
    unsafe fn alloc(&mut self, layout: Layout) -> Result<*mut u8, AllocErr>;
    unsafe fn dealloc(&mut self, ptr: *mut u8, layout: Layout);

    unsafe fn realloc(&mut self, ptr: *mut u8, layout: Layout, new_layout: Layout)
        -> Result<*mut u8, AllocErr> { /* default: alloc, copy, dealloc */ }

    unsafe fn alloc_zeroed(&mut self, layout: Layout) -> Result<*mut u8, AllocErr> { ... }

    fn usable_size(&self, layout: &Layout) -> (usize, usize) { (layout.size(), layout.size()) }

    unsafe fn grow_in_place(&mut self, ptr: *mut u8, layout: Layout, new_layout: Layout)
        -> Result<(), CannotReallocInPlace> { Err(CannotReallocInPlace) }
    unsafe fn shrink_in_place(&mut self, ptr: *mut u8, layout: Layout, new_layout: Layout)
        -> Result<(), CannotReallocInPlace> { Err(CannotReallocInPlace) }

    fn oom(&mut self, err: AllocErr) -> ! { ... }

    // typed convenience methods
    unsafe fn alloc_one<T>(&mut self) -> Result<NonNull<T>, AllocErr> { ... }
    unsafe fn dealloc_one<T>(&mut self, ptr: NonNull<T>) { ... }
    unsafe fn alloc_array<T>(&mut self, n: usize) -> Result<NonNull<T>, AllocErr> { ... }
    unsafe fn dealloc_array<T>(&mut self, ptr: NonNull<T>, n: usize) -> Result<(), AllocErr> { ... }
}
```

Several design points deserve explanation.

**The trait is `unsafe`.** Implementors promise that a pointer returned from `alloc` is valid for the requested layout and does not alias any other live allocation. Collections rely on this for memory safety, so it cannot be left to an ordinary trait.

**Methods take `&mut self`.** Stateful allocators such as arenas need to update internal state. Taking `&mut self` lets them do so without interior mutability. An allocator that is shared between several containers can implement the trait for `&'a MyAlloc`, using interior mutability there.

**Deallocation takes the layout.** The caller must pass the same layout that was used to allocate. This is goal 2. Many allocators, particularly size-class allocators like jemalloc, can free memory much faster when they are told the size than when they must look it up. Collections always know the size of what they allocated, so requiring it costs callers nothing.

**`usable_size` and the in-place methods** let a `Vec` take advantage of slack space the allocator happens to provide, and let it try to grow without copying.

**Errors are returned, not panicked.** `alloc` returns `Result`. Containers that want to abort on failure call `oom`, whose default implementation aborts the process. Code that wants to handle allocation failure gracefully can do so.

## Making collections generic

Standard collections gain an allocator type parameter with a default:

```rust
pub struct Vec<T, A: Allocator = Global> { ... }

impl<T> Vec<T> {
    pub fn new() -> Vec<T>;
}

impl<T, A: Allocator> Vec<T, A> {
    pub fn new_in(alloc: A) -> Vec<T, A>;
}
```

`Global` is a zero-sized type that forwards to the global allocator. Because the parameter is defaulted, existing code that names `Vec<T>` continues to compile. The rollout is incremental: `RawVec` and `Box` first, then other collections as their implementations are adapted.

## GC integration (future work)

We expect that Rust may one day support tracing garbage collection for some types, and that a GC would need to know about every pointer into GC-managed memory, including pointers stored in memory obtained from user allocators. We do not specify that interface here. Instead, we note that if GC support is added, it will require allocators to opt in by implementing an additional marker trait. Allocators that do not implement it will not be usable for GC-tracked types, and the type system will reject attempts to do so. This ensures that the allocators written against this RFC cannot accidentally be used in a way that is unsound in the presence of a collector.

# Drawbacks

- Adding a type parameter to collections makes error messages and documentation more complex, even with a default.
- Allocator-generic code is harder to write correctly than code that assumes the global heap.
- Passing layouts on deallocation is a commitment that some foreign allocators cannot exploit and must ignore.

# Alternatives

- **Do nothing.** Users continue to fork collections.
- **Dynamic dispatch.** Store a `&dyn Allocator` in every collection. Simpler type signatures, but every allocation pays for an indirect call and every collection grows by a pointer, even when using the global heap.
- **Only allow swapping the global allocator.** Useful, and complementary, but does not support per-container allocators.

# Unresolved questions

- Whether `realloc` should be allowed to change alignment.
- Naming: `Allocator` versus `Alloc`.
- Whether `AllocErr` should carry the failed layout.

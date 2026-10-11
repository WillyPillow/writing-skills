- Feature Name: allocator_api
- Start Date: 2016-02-01
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary
[summary]: #summary

Add a standard allocator interface and support for user-defined allocators, with the following goals:

1. Allow libraries (in libstd and elsewhere) to be generic with respect to the particular allocator, to support distinct, stateful, per-container allocators.
2. Require clients to supply metadata (such as block size and alignment) at the allocation and deallocation sites, to ensure hot-paths are as efficient as possible.
3. Provide high-level abstraction over the layout of an object in memory.

Regarding GC: We plan to allow future allocators to integrate themselves with a standardized reflective GC interface, but leave specification of such integration for a later RFC. (The design describes a way to add such a feature in the future while ensuring that clients do not accidentally opt-in and risk unsound behavior.)

# Motivation
[motivation]: #motivation

Rust programs today allocate through a single, global allocator, chosen at link time. For many programs that is ideal. For others it is a limitation.

- A game engine wants to carve each frame's temporary data out of a bump arena, and discard the whole arena at once.
- A server wants to account memory per request and to cap it, so that a runaway request cannot exhaust the machine.
- An embedded system wants containers to live in a specific memory region, such as fast SRAM, and not on the general heap.
- A database wants to allocate pages with particular alignment for direct I/O.
- A tool for finding memory bugs wants to interpose on a subset of the allocations without instrumenting everything.

Today, each of these needs is met by writing a new container type, or by forking the standard one. This duplicates code and leaves users without the ecosystem of generic code written against `Vec` and `HashMap`.

C++ has had allocator parameters on its containers since the beginning, and has learned a number of lessons about what goes wrong. In particular, the original C++ interface hides the size from `deallocate`, forcing allocators to store it, and conflates the type of allocation with the policy of allocation. This RFC takes the opposite stance on both.

# Detailed design
[design]: #detailed-design

## The `Layout` type

A `Layout` describes the size and alignment of a block of memory.

```rust
pub struct Layout { /* size and align */ }

impl Layout {
    pub fn from_size_align(size: usize, align: usize) -> Option<Layout>;
    pub unsafe fn from_size_align_unchecked(size: usize, align: usize) -> Layout;
    pub fn new<T>() -> Layout;
    pub fn array<T>(n: usize) -> Option<Layout>;
    pub fn size(&self) -> usize;
    pub fn align(&self) -> usize;
    pub fn extend(&self, next: Layout) -> Option<(Layout, usize)>;
    pub fn pad_to_align(&self) -> Layout;
}
```

Constructors return `Option` where the inputs may be invalid: alignment must be a power of two, and the rounded-up size must not overflow `isize`. The `extend` method computes the layout of a struct built by appending a field, along with the field's offset, which lets library authors build composite layouts without hand-rolled arithmetic.

## The `Alloc` trait

```rust
pub unsafe trait Alloc {
    unsafe fn alloc(&mut self, layout: Layout) -> Result<*mut u8, AllocErr>;
    unsafe fn dealloc(&mut self, ptr: *mut u8, layout: Layout);

    unsafe fn realloc(&mut self, ptr: *mut u8, old: Layout, new: Layout)
        -> Result<*mut u8, AllocErr> { /* default via alloc/copy/dealloc */ }

    unsafe fn alloc_zeroed(&mut self, layout: Layout) -> Result<*mut u8, AllocErr> { /* default */ }
    fn usable_size(&self, layout: &Layout) -> (usize, usize) { (layout.size(), layout.size()) }
}
```

The central design decisions follow.

**Layout on deallocation.** `dealloc` receives the same `Layout` that was used to allocate. A conforming caller must pass exactly the layout of the original request. This lets allocators dispense with per-block headers: a size-class allocator can compute the class from the layout and place the block in the right free list without reading memory next to the pointer. For the hot paths in `Vec` and `Box`, which already know their sizes, this costs nothing.

**Errors.** Allocation returns a `Result`, so that clients may react to failure. The default behavior of the standard collections remains to abort on failure, but fallible APIs can be built on top of the trait.

**Unsafe trait.** The trait is `unsafe` to implement because the memory-safety of every collection that uses it depends on the allocator returning distinct, correctly aligned, non-overlapping blocks of at least the requested size.

**Receivers.** The methods take `&mut self`. An allocator is therefore allowed to maintain state without internal synchronization. A shared allocator that is used from multiple handles would implement `Alloc` on a handle type (such as `&'a MyAlloc`) and use interior mutability.

## Generic containers

Standard containers gain an allocator type parameter with a default:

```rust
pub struct Vec<T, A: Alloc = Heap> { /* ... */ }
```

The default `Heap` forwards to the global allocator, so existing code that mentions `Vec<T>` is unaffected. Constructors for the default case remain, and new constructors such as `Vec::new_in(alloc)` accept a custom allocator.

Because each container carries its allocator by value, per-container allocators are possible. A zero-sized allocator type adds no space overhead. A reference to a shared arena costs one pointer.

## Interaction with trait objects and type inference

Allocator parameters are type parameters, not trait objects, in the standard containers. This preserves the zero-cost property: monomorphization eliminates indirection. Users who want runtime polymorphism can implement `Alloc` for a `Box<dyn Alloc>` wrapper.

Default type parameters on structs do not influence inference in expression position, so `let v = Vec::new();` continues to infer the default. We rely on the existing behavior and acknowledge that the interaction between default parameters and inference has rough edges.

## Garbage collection

Some future allocators may be garbage collected. Allowing such an allocator to be used in a container is only sound if the container informs the collector about the pointers it stores. This RFC does not define that interface. To keep the door open without allowing accidental unsoundness, the trait `Alloc` as defined here promises *manual* memory management: blocks are freed explicitly. A later RFC may introduce a distinct marker trait for allocators that additionally support a reflective interface, and containers will require a specific bound to opt in. Because clients today cannot name that marker, no existing client can accidentally obtain a collected allocator.

## Zero-sized allocations

Calling `alloc` with a zero-size layout is undefined behavior for the allocator. Containers must not call it; they use a dangling, well-aligned pointer for zero-sized requests, as they do today.

# Drawbacks
[drawbacks]: #drawbacks

- Adding an allocator parameter increases the surface of every generic signature that mentions a container. This is a recognized pain point in C++ and elsewhere.
- Type inference with default type parameters is imperfect, and users may hit confusing errors in unusual cases.
- A stable allocator trait is a commitment. If we find that it is wrong, we are stuck with it.
- The `Layout`-on-free requirement is easy for a caller to get wrong, and getting it wrong is undefined behavior.

# Alternatives
[alternatives]: #alternatives

- **Global allocator only.** Simple, and sufficient for many programs, but unable to express arenas, accounting or regions.
- **Dynamic dispatch only.** Allocators as trait objects would avoid the type parameter at the cost of an indirection per allocation, and a pointer per container. This penalizes the common case.
- **Allocator as a type, not value (C++ `allocator_traits` style).** This does not support stateful allocators in a straightforward way.
- **Omit layout from `dealloc`.** This is the C `free` model. It forces allocators to store metadata, which wastes memory and time for small blocks.

# Unresolved questions
[unresolved]: #unresolved-questions

- Should `realloc` be able to change alignment? The draft allows it only if the allocator can honor it.
- Should `Alloc` be split into a base trait and extensions for allocators that support in-place growth?
- What is the right name for the default allocator type: `Heap`, `Global` or `System`?
- How should out-of-memory be reported in the infallible APIs when a custom allocator is in use?
- What is the precise interface of the future GC integration, and can the marker trait be introduced backwards-compatibly?

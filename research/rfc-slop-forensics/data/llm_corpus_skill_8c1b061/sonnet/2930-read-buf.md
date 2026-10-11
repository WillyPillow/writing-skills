# Rust RFC 2930: read_buf

## Summary

Add a buffer type that tracks which of its bytes are initialized, and a `Read` method that fills such a buffer. Implementors and callers can then read into uninitialized memory without writing unsafe code at every call site and without a pass that zeroes the buffer first.

## Motivation

The `Read` trait takes `&mut [u8]`. A slice of `u8` promises that every byte is initialized. A caller who owns a fresh allocation, such as the spare capacity of a `Vec<u8>`, therefore has to initialize it before the call, usually by zeroing it. The reader then overwrites those bytes with data, and the zeroing was wasted.

The waste grows with the buffer. A caller who reads a large file into a large buffer pays for one write across the whole buffer before the first byte of input arrives. A caller who reads in a loop into the same buffer pays once, but a caller who allocates per read pays every time. [TODO: add a measurement or a reference from the author's material that shows the size of this cost; none is supplied.]

There is a second problem. A caller can skip the zeroing by creating the slice over uninitialized memory with unsafe code. That is undefined behavior in Rust whether or not the reader looks at the bytes. Worse, nothing stops a reader from looking at them. A `Read` implementation is arbitrary safe code, and it may read from the buffer it was given, for example to compute a checksum of the previous contents. If the contents are uninitialized, that read is also undefined behavior, and the caller who wrote the unsafe block is the one who is wrong, even though the buggy line is inside someone else's `read`.

So the current trait leaves callers a choice between a cost and a hazard. This RFC aims to remove the choice. The goal is a safe interface where a reader can be handed memory of unknown initialization, where the reader cannot observe uninitialized bytes through safe code, and where callers can learn how much of the buffer is now initialized so later reads can skip work.

## Guide-level explanation

### The buffer type

`ReadBuf` wraps a region of memory and keeps two counts that depend on each other. The filled count says how many bytes at the front contain data from the reader. The initialized count says how many bytes at the front have been written to at some point, which is always at least the filled count. Bytes beyond the initialized count are uninitialized.

A caller creates a `ReadBuf` over a byte slice, in which case everything starts initialized, or over a slice of `MaybeUninit<u8>`, in which case nothing does. [TODO: confirm the exact constructors and their names.]

### Reading into it

A new method on `Read` takes a `ReadBuf` and fills part of it. A reader that cannot do better than the old interface still works: the default implementation of the new method initializes the remainder of the buffer, calls the old `read` on it, and advances the filled count by the number of bytes returned. A reader that can write directly into uninitialized memory, such as one that wraps a file descriptor, overrides the method and passes the raw pointer to the operating system.

### What a reader may do

A reader receives the unfilled part of the buffer through accessors. One accessor returns the unfilled part as `MaybeUninit<u8>` memory, which is safe to write and unsafe to assume initialized. Another initializes the unfilled part and returns a normal `&mut [u8]` for readers that want the old behavior. After writing, the reader declares how many bytes it filled. Declaring more bytes than were written is unsafe, because the caller will treat those bytes as data.

A short example shows the shape:

```rust
let mut storage = [MaybeUninit::<u8>::uninit(); 4096];
let mut buf = ReadBuf::uninit(&mut storage);
reader.read_buf(&mut buf)?;
let data: &[u8] = buf.filled();
```

[TODO: check the names against the author's design; the method and constructor names here are placeholders for the shape, not the proposal's final API.]

The caller reads the result through `filled()`, which returns a normal slice of exactly the bytes the reader declared. The caller never sees the uninitialized tail.

## Reference-level explanation

### Invariants

The type maintains one invariant: filled is at most initialized, and initialized is at most the capacity. Every safe method preserves it. The unsafe methods state in their documentation what the caller must guarantee for the invariant to hold afterward.

The invariant is the reason there are two counters rather than one. With only a filled count, a caller who reuses a buffer for a second read would not know that the first read left some of the tail initialized, and would have to treat the whole tail as uninitialized again. With both counters, the second read can skip initialization for the part already written, so a loop over one buffer pays for initialization at most once per byte of capacity.

### Behavior across calls

When a caller clears the filled count to reuse the buffer, the initialized count stays. A reader that falls back to the old `read` only initializes the bytes between the initialized count and the capacity. [TODO: confirm that clearing preserves the initialized count in the author's design.]

### Failure cases

A reader that returns an error after partially filling the buffer leaves the filled count wherever it had advanced. The caller decides whether to keep the data. A reader that panics may leave the counters inconsistent with the memory. The type guards against that by advancing the counters only after the write is complete, so the invariant holds at every point where a panic can unwind. [TODO: ask the author whether panic behavior was analyzed; this paragraph states the intended property without evidence that it holds.]

### Soundness

The central safety argument is that safe code cannot reach an uninitialized byte. The only accessors that expose the unfilled part return `MaybeUninit<u8>`, which has no safe read. The accessor that returns `&mut [u8]` initializes first. The filled accessor returns only bytes at or below the filled count. Unsafe code can break the invariant, and each unsafe method names the obligation.

## Drawbacks

The trait grows a second read method. Every implementor now has a default that works and an override that is faster, and documentation has to explain when to write the override. Wrappers that forward to an inner reader must forward the new method as well, or they silently fall back to the slow path. A wrapper that forgets is correct but slow, and nothing flags it.

The new buffer type adds surface that every consumer of `Read` may eventually need to learn. Code that is happy with `&mut [u8]` can stay as it is, but the library's own adapters have to migrate to get the benefit.

The two-counter design has a cost in complexity. A single counter would be easier to explain, and the RFC accepts the extra counter because it is the only way to avoid repeated initialization on reuse.

## Alternatives

**Change the signature of `read` to take `&mut [MaybeUninit<u8>]`.** This would remove the need for a second method. It would break every existing implementor and caller, and in the existing ecosystem that is not an acceptable price. [TODO: ask the author whether the breaking option was weighed, and what the stated reason for rejecting it was.]

**Mark `Read` implementations as trusted.** A trait could promise that implementors never read their buffer, and callers could pass uninitialized memory to trusted ones. This pushes the hazard onto an unsafe marker that every implementor must get right and that cannot be checked. [TODO: ask the author whether this was considered.]

**Keep the status quo and document zeroing.** Callers who need speed use unsafe code at their own risk. The RFC rejects this because the unsafe code is undefined behavior as written and the hazard in the motivation section remains. [TODO: confirm.]

## Unresolved questions

- Should the buffer be a distinct type or a view over the existing slice types?
- Should vectored reads get the same treatment in this RFC, or in a follow-up?
- What are the final names for the type and the methods?
- Does the default implementation need to guard against a reader that returns a count larger than the buffer? [TODO: ask the author.]

## Prior art

[TODO: the author has supplied no prior art. If other languages or crates offer a comparable interface, describe how each differs from this design.]

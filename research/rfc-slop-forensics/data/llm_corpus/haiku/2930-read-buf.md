# Rust RFC 2930: `read_buf`

- Start Date: (draft)
- RFC PR: (pending)
- Rust Issue: (pending)

## Summary

The current design of the `Read` trait is nonoptimal as it requires that the buffer passed to its various methods be pre-initialized even though the contents will be immediately overwritten. This RFC proposes an interface to allow implementors and consumers of `Read` types to robustly and soundly work with uninitialized buffers.

## Motivation

The `Read` trait is one of the most widely used abstractions in the standard library. Its central method, `read`, takes a mutable slice of bytes and fills some prefix of it with data from the source, returning the number of bytes written. The slice must be initialized before the call, because Rust's safety guarantees do not allow safe code to hand out a reference to uninitialized memory.

For many callers this is a small cost. They allocate a buffer, zero it, and pass it in. For high-throughput code, however, the zeroing is wasted work. A typical use reads a large amount of data into a buffer, overwriting every byte, so the initial zeroing touches the same memory twice. On large buffers, the extra pass can be a measurable fraction of total runtime, and on some platforms it causes additional page faults when the memory is first touched.

Users have tried to avoid this cost with unsafe code. They create a buffer with `Vec::with_capacity` and set its length without initializing it, then pass a slice of uninitialized memory to `read`. This is unsound in general, because a `Read` implementation is allowed to read the bytes it is given, and reading uninitialized memory is undefined behavior. Some implementations do not read the buffer, but the trait does not promise this, so the unsafe pattern depends on implementation details.

The problem is therefore that the design forces a choice between a safe but slow interface and a fast but unsound workaround. This RFC aims to remove that choice by providing a new interface that tracks how much of a buffer has been initialized and written.

## Guide-level explanation

The proposal introduces a buffer type that wraps a possibly uninitialized slice and keeps two counters. One counter records how many bytes at the start of the buffer have been initialized. The other records how many bytes have been filled with data, which is the portion the caller is interested in. The new read method takes this buffer rather than a plain slice.

A consumer that wants to read into uninitialized memory creates the buffer from a slice of `MaybeUninit<u8>`, calls the new read method, and then looks at the filled portion. The consumer never reads bytes that the implementation has not written, because the buffer's accessors only expose the filled region as initialized data.

An implementor of `Read` provides the new method. The default implementation of the new method calls the old `read` on the initialized portion of the buffer, zeroing any part that is not yet initialized first. This gives every existing reader the new interface without any change to its code, though the default path still pays the zeroing cost. Readers that can write into uninitialized memory directly override the method to avoid it.

## Reference-level explanation

The new buffer type has a lifetime and wraps a mutable reference to a slice of `MaybeUninit<u8>`. It maintains an invariant that the first `initialized` bytes of the slice are initialized, and that `filled` is no greater than `initialized`. Methods are provided to get the filled portion as an initialized slice, to get the unfilled portion as an uninitialized slice for writing, to advance the filled count after a write, and to initialize the remaining unfilled bytes with zeros.

The trait gains a method that takes a mutable reference to this buffer and returns an `io::Result<()>`. The method must advance the filled count by the number of bytes it wrote, and must not reduce the filled count or move bytes that were already filled. The method must also keep the initialized count accurate, so that any bytes it writes are recorded as initialized.

The safety contract is central. An implementation of the new method that advances the filled count past bytes it did not write is incorrect and may cause undefined behavior, so the method that advances the count is marked unsafe, and the caller of that method takes responsibility for its correctness. Safe wrappers exist for the common cases where the write is performed by a well-tested routine.

For consumers, the proposal provides a convenience function that reads until the buffer is full or the source is exhausted, and an extension that reads an entire stream into a vector, growing it as needed. These functions are safe to call because they maintain the invariants internally.

## Drawbacks

The new interface adds complexity to the library. It introduces a second buffer type, two sets of counters, and a set of invariants that implementors must understand. Some readers will find the distinction between initialized and filled bytes confusing, particularly when they first encounter the API.

The unsafe method that advances the filled count is a sharp edge. Although the design limits its use to implementations that can justify it, a bug in such an implementation can still cause undefined behavior, and the RFC accepts that risk as the price of the performance gain.

## Rationale and alternatives

One alternative is to leave the trait unchanged and rely on the unsafe workaround. The authors rejected this because it is unsound in general and places the burden of correctness on each user.

A second alternative is to change the signature of `read` to accept an uninitialized slice directly. This would break every existing implementation and caller, and would still require some way to communicate how many bytes were written. The authors preferred a new method that can coexist with the old one during a transition.

A third alternative is to add a separate trait for readers that support uninitialized buffers. This would avoid changing `Read`, but it would split the ecosystem, since generic code would need to bound on both traits. The chosen design keeps a single trait with a default implementation, which allows generic code to benefit gradually.

The use of a buffer type that tracks both initialized and filled counts follows from the observation that a reader often initializes more memory than it fills, for example when it zeroes a small region before a partial read. Tracking both quantities avoids repeated zeroing.

## Prior art

Several other systems expose similar distinctions. Some C interfaces separate the capacity of a buffer from its used length, and some operating system calls return a count of bytes written into memory that the caller provided without initialization. The Rust design takes the idea of separate counters and wraps it in types that encode the invariants, so that the common case is safe.

## Unresolved questions

The first open question concerns the exact name and location of the buffer type, and whether it should be public in the first stable release or only used internally by the standard library at first.

The second question concerns the default implementation of the new method on types that do not override it. The authors proposed zeroing the unfilled region, but noted that a future design might allow a reader to declare that it does not read the buffer at all, which would permit a cheaper default for some sources.

The third question is how the new interface should interact with asynchronous readers, which have their own buffer conventions. The authors suggested that this be handled in a follow-up proposal.

## Future possibilities

If this interface is adopted, the standard library can use it internally in the functions that read whole files and streams, which would reduce the cost of those operations without any change to user code. The buffer type could also be used for writing, so that a writer can fill a buffer from a generator without first zeroing it. The authors leave these extensions to later work.

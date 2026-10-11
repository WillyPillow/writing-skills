# An interface for reading into uninitialized buffers

## Summary

The `Read` trait requires callers to pass a buffer that is already initialized. The callee then overwrites the contents without reading them. This RFC proposes an interface that lets both implementors and consumers of `Read` work with uninitialized buffers, and that stays sound.

[TODO: the supplied material is the title and abstract only. Names of new types and methods below are suggestions for the author to confirm.]

## Context

`Read` methods take a buffer that the caller owns. Rust requires a caller to hand over initialized memory, so a caller that allocates a fresh buffer must first write something into it, usually zeros. The `Read` implementation then overwrites that data.

The first write is wasted work. The abstract calls the current design "nonoptimal" for this reason. [TODO: add measured cost. The abstract does not give one. A benchmark that compares a read into a zeroed buffer with a read into an uninitialized buffer would let a reviewer judge how much the wasted write matters.]

The obvious fix has a safety problem. If a caller passes uninitialized memory as `&mut [u8]`, the program has undefined behavior, because Rust treats a reference to a byte slice as pointing to initialized bytes. [TODO: confirm this is the soundness problem the author has in mind.] In addition, a `Read` implementation is arbitrary code. A safe caller cannot trust it to report truthfully how many bytes it wrote. An implementation that returns a count larger than what it wrote would let uninitialized bytes be read as if they were initialized.

[TODO: describe at least one concrete existing `Read` implementation and what it does with the buffer. A specific case grounds the problem.]

## Goals and non-goals

Goals:

1. A consumer can call a read method without first initializing the buffer.
2. An implementor of `Read` can fill a buffer without being forced to write to bytes it does not need to write.
3. Safe code can use the interface without undefined behavior, even if an implementation misbehaves. [TODO: state how the author would verify this goal.]

Non-goals:

1. This RFC does not remove or deprecate the existing methods that take initialized slices. [TODO: confirm.]
2. This RFC does not change `Write`. [TODO: confirm. A reader might expect symmetrical treatment.]
3. This RFC does not promise that existing implementations get faster without changes. [TODO: confirm.]

## Design

### The central tension

The interface has to reconcile two facts. A caller wants to hand over memory that may be uninitialized. A callee must be able to report which part of that memory it initialized, and the caller must be able to rely on the report without trusting arbitrary code.

The rest of the design follows from this tension. [TODO: the author should say which of the sub-decisions below was hardest, and spend the most words on it.]

### A buffer type that tracks initialization

Instead of a plain slice, the read method receives a buffer type that holds three facts: the underlying storage, how much of it is filled with data, and how much of it is known to be initialized.

The reason for tracking both is as follows. A caller who reuses the same buffer across many reads need not initialize it again after the first read, because the buffer remembers which prefix was initialized. [TODO: confirm that this reuse case is a goal of the design.]

Sketch of the shape, for the author to replace:

```rust
// Suggestion only.
fn read_buf(&mut self, buf: &mut ReadBuf<'_>) -> io::Result<()>;
```

[TODO: give the real signatures and the names of the types. Show only the parts that bear on a trade-off.]

### How implementors fill the buffer

An implementation writes into the unfilled part of the buffer and then advances the filled marker. The type offers a safe path, which initializes any bytes the implementation did not write, and an unsafe path, where the implementation promises it has initialized the bytes it claims. [TODO: confirm that the design has both paths. This is inferred from the abstract's phrase "robustly and soundly", and the author must correct it.]

The unsafe path puts the burden of correctness on the implementor. A safe wrapper limits where that burden applies. [TODO: describe which implementations in the standard library use the unsafe path.]

### Default implementation

Existing implementors do not provide the new method. The trait therefore needs a default that calls the existing method with a slice. The default must initialize the unfilled bytes first, because the old method requires an initialized slice. This means existing implementations remain correct and gain no speed until they override the new method. [TODO: confirm. This is the design's compatibility story and it needs the author's confirmation, not an inference from the abstract.]

### Decisions that are costly to reverse

The method added to `Read` and the buffer type are public API, so they are expensive to undo. The internal layout of the buffer type is cheaper to change if its fields stay private. [TODO: confirm which fields are public.]

## Alternatives

The supplied material does not say which alternatives the author considered. The following are suggestions for the author to evaluate; none is a record of what happened.

1. *Make the existing methods accept uninitialized memory directly.* This changes a stable signature and breaks every implementation. [TODO]
2. *Add an unsafe method to `Read` that takes a raw pointer and a length.* This is simple and fast. It gives safe callers no help and puts a soundness obligation on every call site. [TODO]
3. *Keep the status quo and tell users to reuse zeroed buffers.* This costs the initial write once per buffer. When a program reads once into a new buffer, as many one-shot reads do, it costs one write per read. [TODO: the author should confirm whether such patterns are common.]

[TODO: for each, give the author's reason for rejecting it, tied to a goal.]

## Drawbacks

1. The trait gains a method and a new type, so the learning surface grows. [TODO]
2. Two ways to read exist, and users must pick one. Documentation has to say when to use which. [TODO]
3. The unsafe path creates a place where a mistaken implementor causes undefined behavior. The design limits the damage to that implementor. [TODO: confirm.]

## Failure behavior

[TODO: describe what happens when an implementation reports more bytes than it initialized in the safe path, and when it panics partway through a fill. State what the caller sees in each case.]

## Evidence

The supplied material includes no benchmark or prototype. The proposal's benefit currently rests on the argument that the first write is wasted. [TODO: add a measured result, or state plainly that none exists and limit the claim to the argument.] [TODO: add one worked example of a caller using the new interface, from allocation to use.]

## Rollout

1. Add the buffer type and the new trait method with its default.
2. Override the method in selected standard-library implementations. [TODO: choose which.]
3. Mark the feature as unstable first, to collect feedback. [TODO: confirm.]

Rollback before stabilization: remove the unstable items. After stabilization, the items cannot be removed without breaking users.

## Unresolved questions

1. Should the buffer type be usable outside `Read`, for example with asynchronous readers? [TODO]
2. What is the right name for each type and method? [TODO]
3. Should vectored reads receive the same treatment now, or in a later proposal? [TODO]

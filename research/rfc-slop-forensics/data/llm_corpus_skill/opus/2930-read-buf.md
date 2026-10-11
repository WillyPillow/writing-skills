# RFC 2930: read_buf

## Summary

Add a way to pass uninitialized memory to `Read` implementations without undefined behavior. The proposal introduces a buffer type that tracks which bytes are initialized and which are filled, and a new `Read` method that takes it. The method has a default implementation, so existing implementors keep working unchanged.

## Motivation

`Read::read` takes `&mut [u8]`. In Rust, a `&mut [u8]` must point to initialized bytes; creating one over uninitialized memory is undefined behavior even if no byte is read through it. A caller that wants to read into fresh memory, such as the spare capacity of a `Vec<u8>`, must therefore initialize the memory first, usually by writing zeros.

Those zeros are overwritten immediately. For a reader that fills the whole buffer, the zeroing is pure overhead: one extra write pass over memory for every read. [TODO: give a measured cost, for example throughput of `read_to_end` on a large file with and without zeroing, and the hardware it was measured on. Without a number, the motivation rests on the mechanism alone.]

The obvious fix is to skip the zeroing and hand the uninitialized memory to `read` anyway. That is unsound, for a reason that shapes the rest of this RFC. `Read` is a safe trait. A safe implementation of `read` is allowed to read from `buf` before writing it, for example:

```rust
impl Read for Weird {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        let n = buf[0] as usize; // reads caller's memory
        Ok(n.min(buf.len()))
    }
}
```

That implementation is legal, contains no `unsafe`, and is silly. If the caller passed uninitialized memory, it reads an uninitialized byte, which is undefined behavior. It may also return a length that claims bytes were written when they were not, so the caller later reads uninitialized memory too. Generic code that calls `read` on an unknown `R: Read` cannot rule out an implementation like this one. So the caller cannot skip initialization, however well-behaved the common readers are.

The problem therefore is not that `read` is badly written. Its signature cannot express "these bytes may be uninitialized, and you must only write to them". The goal of this RFC is to add a signature that can express it, so that:

1. a caller can pass uninitialized memory to any `Read` type without `unsafe` in the caller,
2. no safe implementation can cause the caller to observe uninitialized bytes, and
3. readers that write directly into the buffer, such as a file or socket reader, never pay for zeroing.

## Guide-level explanation

A `ReadBuf` wraps a byte slice that may be partly uninitialized. It divides the slice into three regions, in order: bytes that are filled with data, bytes that are initialized but not yet filled, and bytes that are uninitialized.

```text
[ filled | initialized, unfilled | uninitialized ]
0      filled                  initialized     capacity
```

A reader appends data at the end of the filled region. A caller reads only the filled region. Safe code can never see the uninitialized region as `&[u8]`.

`Read` gains a method:

```rust
fn read_buf(&mut self, buf: &mut ReadBuf<'_>) -> io::Result<()>;
```

Its default implementation initializes the unfilled part of the buffer, calls `read` on it, and advances the filled region by the returned count. A type that does not override `read_buf` behaves exactly as today, including the cost of zeroing.

A type that does override it, such as `File`, passes the buffer's raw pointer to the operating system, which writes the bytes, and then marks that many bytes as filled. Marking bytes as filled is the one `unsafe` operation in the API, because the implementor promises those bytes were written.

A caller reading into a vector's spare capacity writes:

```rust
let mut buf = ReadBuf::uninit(vec.spare_capacity_mut());
reader.read_buf(&mut buf)?;
let n = buf.filled().len();
unsafe { vec.set_len(vec.len() + n) };
```

[TODO: confirm the constructor names and whether std provides a safe helper on `Vec` so the caller avoids `set_len`.]

## Reference-level explanation

The key design decision is to track the initialized region separately from the filled region. The reason is repeated reads into one buffer. After a default `read_buf` zeroes 64 KiB and `read` fills only 100 bytes, the remaining bytes are now initialized. If the buffer did not remember that, the next call would zero them again. Tracking the initialized length lets the default implementation zero each byte at most once over the buffer's lifetime.

The invariant is `filled <= initialized <= capacity`. Each method preserves it:

- `initialize_unfilled` writes zeros up to capacity and returns the unfilled region as `&mut [u8]`. This is the safe path for implementors.
- `unfilled_mut` returns the unfilled region as `&mut [MaybeUninit<u8>]`. Writing through it is safe; reading through it requires `unsafe`.
- `assume_init(n)` is `unsafe` and declares that the next `n` bytes after the filled region are initialized.
- `add_filled(n)` advances the filled region, and panics if that would pass the initialized region.

`add_filled` is safe because the panic keeps the invariant: a reader cannot mark as filled any byte it has not first made initialized. Only `assume_init` can extend the initialized region without writing through safe code, and it is `unsafe`, so the implementor carries the proof obligation.

[TODO: confirm the exact method set. The list above is the assistant's sketch from the abstract's goal.]

The default methods on `Read` that read into growable buffers, such as `read_to_end`, are changed to call `read_buf` on the vector's spare capacity. This is where the benefit reaches most users, because they call `read_to_end` and do not call `read_buf` directly. [TODO: list the other default methods that will route through `read_buf`.]

## Drawbacks

The API has three regions and an `unsafe` method, which is more to learn than a slice. Most users never see it, but implementors of performance-sensitive readers do.

Wrapper readers, such as a decompressor or a `Take` adapter, only benefit if they also override `read_buf` and forward the buffer. Until each wrapper is updated, a chain of readers pays for zeroing at its first non-updated layer. [TODO: list the std wrappers that will be updated as part of this RFC.]

The default `read_buf` zeroes the whole unfilled region, even if the inner `read` returns only a few bytes. For a type that has not overridden `read_buf`, a large buffer can cost more than it does today, where the caller might have zeroed only what it needed. The initialized tracking bounds the cost to once per byte per buffer. [TODO: check whether any std caller would see a regression from this.]

## Rationale and alternatives

The deciding constraint is soundness in generic code: the caller must be safe against any safe implementation of `Read`. That rules out every design in which the caller passes uninitialized memory as `&mut [u8]`, regardless of how implementors are documented.

[TODO: the following are suggestions for the author to evaluate, not options known to have been considered. The author should state which were considered and why they lost.]

1. An `unsafe` marker on `Read` through which an implementor promises never to read the buffer. This keeps the `&mut [u8]` signature, but the promise covers the whole implementation and is hard to audit. It also does not express partial initialization across repeated calls.
2. Passing `&mut [MaybeUninit<u8>]` without the tracking type. This is sound, but every implementor that wants a safe `&mut [u8]` must zero the whole slice each call, losing the at-most-once property.
3. Leaving `Read` unchanged and asking performance-sensitive callers to use OS-specific APIs. This keeps std simple, but generic code cannot benefit.

## Unresolved questions

1. Whether `ReadBuf` borrows its storage or can own it.
2. Whether `Write` needs a matching change for vectored or uninitialized writes. [TODO: likely out of scope; author to confirm.]
3. The name of the type and method.
4. How async I/O traits outside std should adopt the same buffer type.

# RFC 2930: read_buf

## Summary

Add a buffer type, `ReadBuf`, that tracks how much of a byte buffer has been initialized and how much has been filled with data. Add a method `Read::read_buf` that reads into a `ReadBuf`. Callers can then pass uninitialized memory to a reader without zeroing it first, and implementations of `Read` can write into that memory using only safe code.

## Motivation

`Read::read` takes `&mut [u8]`. A `&mut [u8]` must point to initialized bytes: creating one over uninitialized memory is undefined behavior, even if no byte is ever read through it. A caller that allocates a fresh buffer for a read therefore has to initialize it, usually by zeroing, before it can call `read`. The reader then overwrites the zeroed bytes with data.

The zeroing is wasted work whenever the reader fills the buffer. Its cost grows with the buffer size and is paid on every fresh allocation. `Read::read_to_end`, for example, grows a `Vec<u8>` and must initialize each new region of capacity before passing it to `read`. [TODO: give a measurement of the zeroing cost from a benchmark or a profile of a real program, with buffer sizes and the reader used.]

The standard library has worked around this problem internally. [TODO: describe the existing mechanism, if any, by which `std` skips initialization for trusted readers, and why it cannot be extended to third-party `Read` implementations.] A caller outside `std` has no sound way to skip the zeroing. The tempting approach, calling `set_len` on a `Vec` and passing the uninitialized tail to `read`, is unsound for an arbitrary reader. A `Read` implementation is allowed to read from the buffer it receives, and nothing in the trait's signature forbids returning a byte count larger than the number of bytes it wrote.

Two requirements follow. The caller must be able to hand over memory that is not yet initialized. And the caller must learn, without trusting the reader, which bytes now hold data.

## Guide-level explanation

A `ReadBuf` wraps a slice of possibly uninitialized bytes and splits it into three regions:

```
[ filled | initialized, unfilled | uninitialized ]
0        filled                  initialized      capacity
```

The filled region holds data the reader produced. The initialized region extends past it to cover bytes that are known to be initialized but do not yet hold data from this read. The rest is uninitialized.

A caller who wants to read into a fresh allocation writes:

```rust
let mut storage = [MaybeUninit::<u8>::uninit(); 8192];
let mut buf = ReadBuf::uninit(&mut storage);
reader.read_buf(&mut buf)?;
let data: &[u8] = buf.filled();
```

`filled()` returns a `&[u8]` over the filled region, which is always initialized. No `unsafe` code appears at the call site.

A reader that implements `read_buf` writes data with safe methods such as `ReadBuf::append(&[u8])`, which copies bytes into the buffer and advances both the filled and initialized positions. A reader that wraps an operating-system call needs to pass a raw pointer and length to the kernel. It uses `unsafe` methods to get the unfilled region as `&mut [MaybeUninit<u8>]` and then to tell the `ReadBuf` how many bytes the call wrote.

## Reference-level explanation

### `ReadBuf`

```rust
pub struct ReadBuf<'a> {
    buf: &'a mut [MaybeUninit<u8>],
    filled: usize,
    initialized: usize,
}
```

The type maintains `filled <= initialized <= buf.len()`, and every byte below `initialized` is initialized. Safe methods cannot break these invariants.

The main safe methods are:

```rust
impl<'a> ReadBuf<'a> {
    pub fn new(buf: &'a mut [u8]) -> Self;                 // all initialized
    pub fn uninit(buf: &'a mut [MaybeUninit<u8>]) -> Self; // none initialized
    pub fn capacity(&self) -> usize;
    pub fn filled(&self) -> &[u8];
    pub fn remaining(&self) -> usize;
    pub fn initialize_unfilled(&mut self) -> &mut [u8];
    pub fn append(&mut self, data: &[u8]);
    pub fn clear(&mut self);
}
```

`initialize_unfilled` zeroes any uninitialized part of the unfilled region, advances `initialized` to the end, and returns the unfilled region as `&mut [u8]`. This method is how existing `read` implementations are adapted, as shown below. `clear` resets `filled` to zero and keeps `initialized`, so a buffer reused across reads is zeroed at most once.

The unsafe methods are:

```rust
impl<'a> ReadBuf<'a> {
    pub unsafe fn unfilled_mut(&mut self) -> &mut [MaybeUninit<u8>];
    pub unsafe fn assume_init(&mut self, n: usize);
    pub fn add_filled(&mut self, n: usize);
}
```

`unfilled_mut` is unsafe because the caller could write `MaybeUninit::uninit()` into a byte below `initialized`, which would break the invariant. `assume_init(n)` asserts that the first `n` unfilled bytes are initialized. `add_filled(n)` advances `filled` and panics if the result would pass `initialized`. It is safe because of that check.

### `Read::read_buf`

```rust
pub trait Read {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize>;

    fn read_buf(&mut self, buf: &mut ReadBuf<'_>) -> io::Result<()> {
        let n = self.read(buf.initialize_unfilled())?;
        buf.add_filled(n);
        Ok(())
    }
}
```

The default implementation keeps every existing reader correct without changes. It zeroes the uninitialized tail once and then calls `read`. A reader that returns a count larger than the slice it was given makes `add_filled` panic rather than expose uninitialized memory.

A reader that overrides `read_buf` reports progress by advancing the `ReadBuf` instead of by returning a count. The caller computes the number of new bytes from the change in `filled().len()`. Because the `ReadBuf` enforces its own invariants, the caller does not need to trust the reader's arithmetic, which is the second requirement from the motivation.

Standard library types that wrap file descriptors and sockets override `read_buf` to pass the unfilled region directly to the system call. `read_to_end` and `BufReader` switch to calling `read_buf`, so they stop zeroing memory when the underlying reader overrides it. [TODO: list which `std` readers will override `read_buf` in the first implementation.]

### Why a separate type

Passing `&mut [MaybeUninit<u8>]` directly to a new trait method would let the reader write to uninitialized memory, but it would leave the caller unable to tell how much of the slice the reader initialized without trusting a returned count. It would also lose the information that part of a reused buffer is already initialized, so callers that read repeatedly into one buffer could not avoid re-zeroing. The `initialized` field carries that information across calls. [TODO: confirm that these were the reasons for a dedicated type, and record any other designs the author evaluated.]

## Drawbacks

`Read` gains a second required concept. Implementors who want the performance benefit have to learn `ReadBuf` and, for system-call wrappers, write `unsafe` code that is subtle: calling `assume_init` with too large a count is undefined behavior.

The API surface is larger than a single method. `ReadBuf` needs its own documentation, and every adapter in the ecosystem that forwards `Read` (compression, encryption, framing) has to forward `read_buf` as well, or its callers fall back to zeroing. [TODO: estimate how many widely used adapters would need updating, if that data is available.]

Adding `read_buf` with a default body does not break existing implementations of `Read`. [TODO: confirm there are no name clashes with inherent or extension-trait methods named `read_buf` in major crates.]

## Rationale and alternatives

[TODO: record which of these were considered and why each lost. None is presented as having been evaluated.]

[TODO: Was a freeze or "initialize with arbitrary bytes" operation considered, which would make uninitialized memory safe to expose as `&mut [u8]`? It would need language support.]

[TODO: Was an unsafe marker trait for readers that promise not to read from the buffer considered? It avoids a new type but moves the soundness proof to every implementor.]

[TODO: Was the status quo considered, with performance-sensitive users relying on `std`-internal shortcuts?]

## Unresolved questions

Whether `Write` needs a matching change for vectored or uninitialized buffers is out of scope here. How `read_buf` interacts with `read_vectored` is open. [TODO: decide whether a `read_buf_vectored` method is part of this RFC.] The names `ReadBuf`, `filled` and `initialized` are provisional.

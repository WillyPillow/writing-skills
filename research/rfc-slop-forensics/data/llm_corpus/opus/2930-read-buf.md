- Feature Name: `read_buf`
- Start Date: 2020-05-18
- RFC PR: rust-lang/rfcs#2930
- Rust Issue: rust-lang/rust#78485

# Summary

The `Read` trait requires that the buffer passed to its methods be initialized, even though an implementation will usually overwrite the contents immediately. This RFC proposes a new buffer type and a new `Read` method that let implementors and callers work with uninitialized buffers soundly and efficiently.

# Motivation

The core method of `Read` is:

```rust
fn read(&mut self, buf: &mut [u8]) -> io::Result<usize>;
```

A `&mut [u8]` must point to initialized memory. Producing one from uninitialized memory is undefined behavior, even if nobody reads the bytes before they are written. So a caller who wants to read into a freshly allocated buffer must first fill it, typically with zeros:

```rust
let mut buf = vec![0; 64 * 1024];
let n = reader.read(&mut buf)?;
```

For a single small read this cost is negligible. For code that reads large amounts of data into newly allocated buffers, such as `read_to_end`, network servers allocating a buffer per connection, or decompression libraries, zeroing memory that is about to be overwritten shows up in profiles. In some benchmarks of `read_to_end` on large files, the zeroing accounts for a measurable fraction of total time.

The standard library has tried to avoid this cost before. An unstable method, `Read::initializer`, let a reader declare that it would never read from the buffer it was given, which allowed callers to skip zeroing. That approach has two problems.

First, it is unsound in the presence of safe code. `Read` is a safe trait. A safe implementation of `read` is allowed to inspect `buf` before writing to it. If a caller hands it uninitialized memory on the strength of an `initializer` claim made by a different, possibly wrapping, implementation, the result is undefined behavior reachable from safe code. The `initializer` method had to be `unsafe` to implement, which put a burden on every reader wrapper to forward it correctly.

Second, even when all implementations are well behaved, the API does not track *how much* of a buffer has been initialized. A caller that reads into a large buffer in several steps loses the knowledge that earlier reads initialized part of it, and has to either zero again or track the information manually with unsafe code.

We want an API where:

1. Callers can pass uninitialized memory without zeroing it.
2. Implementations that are written in entirely safe code remain sound.
3. Knowledge of which bytes are initialized is preserved across calls, so it never has to be re-established.

# Guide-level explanation

This RFC introduces a buffer type, `ReadBuf`, which wraps a slice of possibly uninitialized bytes and tracks two positions within it:

```
[ filled | initialized but unfilled | uninitialized ]
0        filled                     initialized       capacity
```

- The *filled* region contains bytes that have been read and are valid data.
- The *initialized* region contains every byte known to be initialized. It always includes the filled region and may extend beyond it.
- The rest of the buffer is uninitialized.

`Read` gains a new method:

```rust
fn read_buf(&mut self, buf: &mut ReadBuf<'_>) -> io::Result<()>;
```

An implementation of `read_buf` appends data to the filled region. The caller learns how many bytes were read by comparing the filled length before and after the call.

A safe implementation can obtain an initialized slice to write into with `initialize_unfilled`, which zeroes the uninitialized part of the buffer the first time it is needed and records that it has done so. Subsequent calls do not zero again. An implementation that uses unsafe code to write directly into uninitialized memory, such as one that calls the operating system's `read`, can use `unfilled_mut`, which returns `&mut [MaybeUninit<u8>]`, and then call `assume_init` and `add_filled` to record what it wrote.

The default implementation of `read_buf` calls `read` with the result of `initialize_unfilled`. So every existing reader automatically supports `read_buf`, safely, at the cost of zeroing once. Readers that care about performance can override `read_buf` to avoid even that.

Callers that use `read_buf` with a reused buffer benefit even with default implementations, because the buffer remembers that it was initialized and is not zeroed a second time.

# Reference-level explanation

```rust
pub struct ReadBuf<'a> {
    buf: &'a mut [MaybeUninit<u8>],
    filled: usize,
    initialized: usize,
}

impl<'a> ReadBuf<'a> {
    pub fn new(buf: &'a mut [u8]) -> ReadBuf<'a>;
    pub fn uninit(buf: &'a mut [MaybeUninit<u8>]) -> ReadBuf<'a>;

    pub fn capacity(&self) -> usize;
    pub fn filled(&self) -> &[u8];
    pub fn filled_mut(&mut self) -> &mut [u8];
    pub fn initialized(&self) -> &[u8];
    pub fn initialized_mut(&mut self) -> &mut [u8];
    pub fn remaining(&self) -> usize;

    pub fn initialize_unfilled(&mut self) -> &mut [u8];
    pub fn initialize_unfilled_to(&mut self, n: usize) -> &mut [u8];
    pub unsafe fn unfilled_mut(&mut self) -> &mut [MaybeUninit<u8>];

    pub fn clear(&mut self);
    pub fn add_filled(&mut self, n: usize);
    pub fn set_filled(&mut self, n: usize);
    pub unsafe fn assume_init(&mut self, n: usize);
    pub fn append(&mut self, buf: &[u8]);
}
```

The invariant is `filled <= initialized <= capacity`.

- `new` creates a buffer from an initialized slice, so `initialized` starts at its full length.
- `uninit` creates a buffer from uninitialized memory, so `initialized` starts at zero.
- `add_filled` and `set_filled` panic if they would move `filled` past `initialized`. This is what keeps safe code sound: a safe implementation cannot claim to have filled bytes that it has not provably initialized.
- `assume_init(n)` marks the first `n` bytes of the unfilled region as initialized. It is `unsafe` because the caller asserts that those bytes were written.
- `unfilled_mut` is `unsafe` because the caller must not write uninitialized bytes into the region, which would de-initialize memory that the buffer believes is initialized.
- `clear` resets `filled` to zero but leaves `initialized` unchanged, so a reused buffer is not re-zeroed.

The default `read_buf` is:

```rust
fn read_buf(&mut self, buf: &mut ReadBuf<'_>) -> io::Result<()> {
    let n = self.read(buf.initialize_unfilled())?;
    buf.add_filled(n);
    Ok(())
}
```

If a misbehaving `read` returns a count larger than the slice it was given, `add_filled` panics, matching how other standard library code treats an out-of-range count today.

`read_buf_exact` is also added, as the counterpart of `read_exact`.

Standard library readers that wrap system calls (`File`, `TcpStream`, `UnixStream`, `Stdin`, `ChildStdout`) override `read_buf` to read directly into the unfilled region. Adapters such as `BufReader`, `Take`, `Chain`, and `&[u8]` override it to forward the buffer. `read_to_end` and `io::copy` are reimplemented on top of `read_buf`.

`Read::initializer` and the `Initializer` type are removed.

# Drawbacks

This adds a new type and a new method to one of the most widely implemented traits in the ecosystem. Wrapper types have to override `read_buf` to forward it, or they will silently fall back to the slower path. That is a performance trap rather than a soundness one, but it is easy to miss.

The `ReadBuf` API is not small, and has several methods with similar names. Some users will find it hard to know which one to call.

# Rationale and alternatives

**Change `read` to take `&mut [MaybeUninit<u8>]`.** This would be a breaking change to a stable trait.

**Keep `initializer`.** Its soundness depends on every wrapper forwarding it correctly through unsafe code, and it does not track partial initialization.

**Have `read_buf` return the number of bytes read** instead of updating `filled`. This is closer to `read`, but separates the count from the buffer, so a bad count from safe code could no longer be caught by the buffer's own invariant.

# Unresolved questions

- Should `Write` get a corresponding vectored or uninitialized-buffer API?
- How should `read_buf` interact with vectored reads (`read_vectored`)? A `ReadBufs` type over multiple slices is possible but left for later.
- Should `ReadBuf` be generic over the element type, for use outside of I/O?

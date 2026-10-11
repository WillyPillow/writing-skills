# RFC 2930: read_buf

- Feature Name: `read_buf`
- Start Date: 2020-08-25
- RFC PR: rust-lang/rfcs#2930
- Rust Issue: rust-lang/rust#78485

## Summary

The current design of the `Read` trait is nonoptimal as it requires that the buffer passed to its various methods be pre-initialized even though the contents will be immediately overwritten. This RFC proposes an interface to allow implementors and consumers of `Read` types to robustly and soundly work with uninitialized buffers.

## Motivation

### Background

The core of the `Read` trait is the `read` method:

```rust
pub trait Read {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize>;
}
```

The caller passes a mutable slice, the implementation fills some prefix of it, and the return value says how many bytes were written. Bytes past that count are untouched.

Rust requires that a `&mut [u8]` point to initialized memory. Creating a reference to uninitialized bytes is undefined behavior, even if no code reads them. So a caller that wants to read into a freshly allocated buffer must first fill it with something, usually zeros:

```rust
let mut buf = vec![0; 8192];
let n = reader.read(&mut buf)?;
```

The zeroing is wasted work. Its cost is proportional to the buffer size, and for workloads that read large amounts of data in moderately sized chunks it can be a measurable fraction of the total time. Benchmarks of reading from files and sockets into large buffers have shown overheads of several percent, and more for fast sources like in-memory readers or pipes.

### Why not just give `read` an uninitialized slice?

An obvious shortcut would be to make the buffer `&mut [MaybeUninit<u8>]`. This breaks every existing implementation of `Read`, which expects to write into initialized bytes and sometimes reads from them. It also makes the common case, where the buffer is already initialized, harder to use.

Another approach, used in earlier versions of the standard library, was an unsafe method `initializer()` that let a reader declare it never reads from the buffer. This puts the burden on the implementer to promise something subtle, and a single mistaken promise is unsound. Wrapper types such as `BufReader` and `Take` also have to forward the promise correctly. The mechanism proved fragile and was removed from the stable surface.

### Goals

The solution should:

1. avoid the cost of initializing buffers that will be overwritten;
2. keep safe code safe: a safe implementation of `Read` must not be able to cause undefined behavior;
3. remain compatible with existing `Read` implementations and callers;
4. avoid repeatedly initializing the same memory when a buffer is reused across calls.

## Detailed design

### `BorrowedBuf` and `BorrowedCursor`

The proposal introduces two types in `std::io`.

`BorrowedBuf<'a>` wraps a borrowed slice of possibly uninitialized bytes and tracks two watermarks: how much of the buffer is *filled* with data written by a reader, and how much is known to be *initialized*. The filled region is always a prefix of the initialized region, and the initialized region is a prefix of the buffer.

```rust
pub struct BorrowedBuf<'a> { /* ... */ }

impl<'a> BorrowedBuf<'a> {
    pub fn capacity(&self) -> usize;
    pub fn len(&self) -> usize;                // length of filled region
    pub fn init_len(&self) -> usize;           // length of initialized region
    pub fn filled(&self) -> &[u8];
    pub fn unfilled<'this>(&'this mut self) -> BorrowedCursor<'this>;
    pub fn clear(&mut self) -> &mut Self;      // reset filled to zero, keep init
}

impl<'a> From<&'a mut [u8]> for BorrowedBuf<'a>;
impl<'a> From<&'a mut [MaybeUninit<u8>]> for BorrowedBuf<'a>;
```

Creating a `BorrowedBuf` from `&mut [u8]` marks the entire buffer as initialized. Creating it from `&mut [MaybeUninit<u8>]` marks none of it as initialized.

`BorrowedCursor<'a>` is a write handle on the unfilled part of a `BorrowedBuf`. It is what a reader receives.

```rust
pub struct BorrowedCursor<'a> { /* ... */ }

impl<'a> BorrowedCursor<'a> {
    pub fn capacity(&self) -> usize;           // bytes remaining to fill
    pub fn written(&self) -> usize;            // bytes filled through this cursor
    pub fn init_ref(&self) -> &[u8];
    pub fn init_mut(&mut self) -> &mut [u8];
    pub fn uninit_mut(&mut self) -> &mut [MaybeUninit<u8>];
    pub fn ensure_init(&mut self) -> &mut Self;
    pub fn append(&mut self, buf: &[u8]);
    pub unsafe fn advance(&mut self, n: usize) -> &mut Self;
    pub unsafe fn set_init(&mut self, n: usize) -> &mut Self;
    pub fn reborrow<'this>(&'this mut self) -> BorrowedCursor<'this>;
}
```

The cursor offers three ways to fill its buffer.

- `append` copies a slice into the unfilled region, initializing as it goes. It is entirely safe and covers readers that already have the data in memory.
- `ensure_init` zero-fills any uninitialized part of the unfilled region and returns a handle to initialized memory. A reader that cannot work with uninitialized memory, for example one that delegates to a legacy `read`, calls this first. Because the buffer tracks which bytes are initialized, zeroing happens at most once for each byte across any number of reads into the same buffer.
- `uninit_mut` exposes the unfilled region as `MaybeUninit<u8>` for readers that write directly, such as one that passes the pointer to a system call. After writing, the reader tells the cursor how many bytes were written using the unsafe `advance` method (and `set_init` if more bytes are known to be initialized than are being marked as filled).

The invariants are encoded in the types. Safe code can never observe an uninitialized byte, and only the unsafe methods carry a proof obligation.

### New `Read` method

A new provided method is added to `Read`:

```rust
pub trait Read {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize>;

    fn read_buf(&mut self, buf: BorrowedCursor<'_>) -> io::Result<()> {
        default_read_buf(|b| self.read(b), buf)
    }
}
```

The default implementation calls `ensure_init`, then `read` on the initialized slice, and then `advance` by the number of bytes read. All existing implementations therefore work unchanged. Types that can do better override `read_buf`. For instance, `File` and `TcpStream` read directly into the uninitialized region with a system call, then advance the cursor by the returned count.

Error semantics follow `read`. A call that produces zero new bytes and returns `Ok(())` signals end of file for a non-empty cursor.

### Using `read_buf` from `read_to_end` and `read_exact`

The convenience methods are rewritten on top of `read_buf` where this helps:

- `read_to_end` grows a `Vec<u8>` and reads directly into its spare capacity, via a `BorrowedBuf` over the uninitialized tail. The reader no longer pays to zero the new space each time the vector grows.
- `read_buf_exact` is added as the analog of `read_exact` for cursors.
- `BufReader` uses `read_buf` to fill its internal buffer, which is allocated uninitialized and tracked with a `BorrowedBuf` so that repeated fills only initialize it at most once.

### Safety discussion

The soundness argument has three parts. First, `BorrowedBuf` never hands out a reference to uninitialized memory typed as `u8`; it hands out `MaybeUninit<u8>` for the unknown portion. Second, the amount initialized only grows, and `advance` and `set_init` are unsafe because the caller vouches that the bytes are initialized. Third, reborrowing a cursor yields a new cursor with the same region and a lifetime restricted to the borrow, so a nested reader cannot move the watermarks backward.

A buggy safe `Read` implementation can write garbage or return a wrong count, but it cannot cause undefined behavior, because all the ways to claim bytes as initialized are unsafe.

## Drawbacks

This adds two nontrivial types and a new method to one of the most widely implemented traits in the standard library. Documentation and teaching materials will have to describe when to use `read` and when `read_buf`.

Having both `read` and `read_buf` raises the possibility that an implementer overrides one inconsistently with the other. The default implementation of `read_buf` delegates to `read`, but there is no default in the other direction, so implementers who write only `read_buf` must also provide `read`.

The unsafe methods on `BorrowedCursor` are a new place for unsound code to hide. They are narrow, and most readers will use safe methods only.

## Alternatives

**Return `&mut [MaybeUninit<u8>]` from a new unsafe trait method.** Simple, but offers no tracking of which parts are initialized, which loses the "initialize at most once" property.

**An `initializer` marker on `Read`.** Already tried, and it required implementers to make an unsafe promise.

**Change `read` to take `&mut [MaybeUninit<u8>]`.** Breaks the ecosystem.

**A `Buf` trait with generic implementations, along the lines of the `bytes` crate.** More flexible, but a much larger surface for the standard library, and unnecessary for the problem at hand.

## Unresolved questions

Whether `BorrowedBuf` and `BorrowedCursor` belong in `std::io` or in `core` so they can be used by `no_std` code. Whether vectored reads should get a corresponding `read_buf_vectored`. And whether the name `BorrowedCursor` is the best fit. These can be settled during the unstable period.

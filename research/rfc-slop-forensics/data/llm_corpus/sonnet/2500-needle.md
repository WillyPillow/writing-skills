# RFC 2500: needle

- Feature Name: `needle`
- Start Date: 2018-07-21
- RFC PR: rust-lang/rfcs#2500
- Rust Issue: rust-lang/rust#56345

## Summary

Generalize the needle (née pattern) API to support `&str`, `&mut str`, `&[T]`, `&mut [T]`, `Vec<T>` and `&OsStr`.

## Motivation

### Stabilize the Pattern API

The standard library has an unstable `Pattern` trait, which powers methods such as `str::find`, `str::split`, `str::trim_matches` and `str::replace`. Callers can pass a `char`, a `&str`, a closure `FnMut(char) -> bool`, a `&[char]` or a `&&str`, and the method does the right thing. This is among the most ergonomic parts of the string API, and it has been unstable since before 1.0. The trait cannot be implemented outside `std`, so users cannot add their own kinds of pattern, and its design only covers `&str`.

Meanwhile, slices have no comparable story. To split a `&[u8]` on a subsequence, or find a subslice inside a `&[T]`, a user must write the loop by hand or depend on a crate such as `memchr` or `twoway`. `<[T]>::split` accepts only a predicate on single elements, and there is no `<[T]>::find` taking a subslice. `OsStr` has almost no searching API at all.

Stabilizing the pattern API for `str` alone would lock in a design that cannot grow to cover these types. The point of this RFC is to design a single abstraction that serves all of them, and to stabilize that one.

### Implement OMG-WTF-8

`OsStr` on Windows is stored as WTF-8, a superset of UTF-8 that permits unpaired surrogates. Searching an `OsStr` for a `&str` is surprisingly subtle, because a surrogate pair in the haystack may be split across the boundary of a match. The OMG-WTF-8 specification refines WTF-8 so that such splits are well defined: a haystack can be cut in the middle of a four-byte sequence, producing two ill-formed halves that are still valid OMG-WTF-8. With this encoding, `OsStr` can offer `find`, `split` and `contains` without allocating or transcoding. Doing so requires the pattern abstraction to be expressed in terms of a haystack type that is not `str`, so the two goals are linked.

## Guide-level explanation

A **needle** is something you search for. A **haystack** is something you search in. The same vocabulary works across types: you can look for a `char` in a `&str`, a `&str` in a `&str`, a `&[u8]` in a `&[u8]`, or a `&str` in an `&OsStr`.

```rust
let s = "foo, bar, baz";
assert_eq!(s.find(", "), Some(3));
assert_eq!(s.split(',').count(), 3);

let bytes = b"foo\r\nbar\r\n";
let lines: Vec<_> = bytes.split_str(b"\r\n").collect();
assert_eq!(lines, [&b"foo"[..], &b"bar"[..], &b""[..]]);

use std::ffi::OsStr;
let path = OsStr::new("a.tar.gz");
assert!(path.contains(".tar"));
```

Existing code keeps working: every needle that `str` accepts today still works with the same meaning. The new capability is that slices and `OsStr` accept the analogous set. For a `[T]` haystack, a needle can be a single `&T`, a `&[T]`, a predicate `FnMut(&T) -> bool`, or a `&[T; N]` for any `T: PartialEq`.

A user can also write their own needle by implementing the `Needle` trait. For example, a needle matching an ASCII-case-insensitive keyword, or a regular expression, can be used with `split`, `find` and `replace` on any haystack it supports. The `regex` crate can implement `Needle<&str>` and `Needle<&[u8]>` directly, instead of providing its own parallel `split` and `find` methods.

## Reference-level explanation

### API

The central abstractions are `Haystack`, `Needle` and `Searcher`.

```rust
pub unsafe trait Hay {
    type Index: Copy + PartialOrd + Debug;
    fn empty<'a>() -> &'a Self;
    fn start_index(&self) -> Self::Index;
    fn end_index(&self) -> Self::Index;
    unsafe fn next_index(&self, index: Self::Index) -> Self::Index;
    unsafe fn prev_index(&self, index: Self::Index) -> Self::Index;
    unsafe fn slice_unchecked(&self, range: Range<Self::Index>) -> &Self;
}

pub trait Haystack: Sized {
    type Target: Hay + ?Sized;
    fn into_target(self) -> Self;
    unsafe fn from_target_range(target: Self::Target, range: Range<Index>) -> Self;
}

pub trait Needle<H: Haystack>: Sized {
    type Searcher: Searcher<H::Target>;
    type Consumer: Consumer<H::Target>;
    fn into_searcher(self) -> Self::Searcher;
    fn into_consumer(self) -> Self::Consumer;
}
```

A `Hay` is the borrowed, unsized form of the type being searched (`str`, `[T]`, `OsStr`). A `Haystack` is any owner or borrower of a hay that can be cut into sub-haystacks: `&str`, `&mut str`, `&[T]`, `&mut [T]`, `Vec<T>` and `&OsStr`. This is what makes `&mut` and owning variants possible. For example, `split` on a `&mut [T]` yields disjoint `&mut [T]` pieces.

A `Searcher` finds the first or last match within a hay. A `Consumer` answers a simpler question, whether the needle matches at a fixed position, and powers `starts_with`, `ends_with` and `trim_matches`. Splitting these roles lets a needle such as a single `char` implement a trivial consumer without the cost of constructing a full searcher.

Indices are not `usize` in general. For `str` and `[T]` they are, but for `OsStr` on Windows they carry the additional information needed to represent a position in the middle of a surrogate pair. A needle never inspects the index representation; it only passes indices back to the hay.

### Standard library changes

The methods on `str` that currently use `Pattern` are re-expressed in terms of `Needle<&str>`. The following methods gain equivalents on `[T]`, `Vec<T>` and `OsStr` where they make sense: `contains`, `starts_with`, `ends_with`, `find`, `rfind`, `split`, `rsplit`, `splitn`, `split_terminator`, `matches`, `match_indices`, `trim_matches`, `trim_start_matches`, `trim_end_matches`, `replace` and `replacen`. Methods that exist on `[T]` today with different semantics, such as `<[T]>::split` taking a predicate, are kept and extended by a blanket `Needle` implementation for `FnMut(&T) -> bool`, so existing calls still compile.

Existing `Pattern` implementations are preserved by making `Pattern` a deprecated alias for `Needle<&str>`.

### Performance

The existing `str` implementations rely on specialized algorithms: `memchr` for single bytes, Two-Way for substrings, and ASCII fast paths for character classes. These must not regress. The design keeps the searcher type a plain associated type with no dynamic dispatch, so monomorphization produces the same code as before. The `Hay::next_index` and `slice_unchecked` operations compile down to pointer arithmetic for `str` and `[T]`. Benchmarks for `find`, `split` and `replace` on the existing `str` test corpus are part of the stabilization criteria, with a threshold of no more than a 3% regression on any case.

For byte slices, the Two-Way searcher is now available where before callers needed an external crate. For `OsStr` on Windows, searches use the OMG-WTF-8 searcher, which is a thin wrapper around the UTF-8 one with boundary fixups only at the ends of a match.

## Drawbacks

The abstraction is more complicated than `Pattern`. There are three traits and associated index types where there used to be one. It increases the learning curve for people implementing their own needles, although those are a small fraction of users.

Compile times might increase, since each method becomes generic over more types. Because most callers use concrete types at the call site, the extra instantiation cost should be small, but it is not zero.

Changing a trait already used in stable signatures, even through `Pattern` which has no stable implementors, constrains future evolution. The trait names `Needle` and `Haystack` become public vocabulary.

## Rationale and alternatives

### Principles

1. Whatever works today must keep working with identical behavior.
2. Performance must be at least as good for `str`.
3. The design should be open for user extension, because the value of a trait is largely in what third parties build on it.
4. The abstraction should not leak the encoding of the hay.

### Design rationales

The split between `Hay` and `Haystack` handles ownership. A single trait over `&str` would not cover `&mut str` and `Vec<T>` without duplicating every adaptor. The cost is a layer of indirection in the signatures, hidden from callers by inference.

Using an associated `Index` type rather than `usize` is what allows OMG-WTF-8. Making this index opaque would be unnecessary for `str` alone, but without it the `OsStr` design would need a separate implementation.

The Searcher/Consumer split reflects an observed asymmetry: the `starts_with` family is common and hot, and does not require scanning.

### Miscellaneous decisions

The name `Needle` was chosen over `Pattern` because "pattern" collides with pattern matching in the language and with regular expression patterns in the ecosystem. The old name remains as a deprecated alias for one release cycle.

### Alternatives

One alternative is to stabilize `Pattern` as it is and add a separate `SlicePattern` trait for slices. This keeps the stable surface small but guarantees two nearly identical APIs and no path to `OsStr`.

Another is to leave searching to external crates. `memchr`, `regex` and `bstr` do a good job, but the standard library already has the machinery for `str`, and generalizing it avoids a fragmented ecosystem.

A third is to use specialization to provide separate implementations for each haystack. Specialization is not stable and is unlikely to become so soon.

## Prior art

### Previous attempts

RFC 528 originally introduced a string pattern API, and the current `Pattern` trait descends from it. Earlier proposals for stabilizing slice searching stalled on the lack of a unifying abstraction. The `bstr` crate provides byte-string searching with its own set of methods.

### Haskell

Haskell's `Data.Text` and `Data.ByteString` expose `breakOn`, `splitOn` and `isInfixOf` on concrete types, with the `ListLike` and `MonoTraversable` classes providing partial abstraction. Libraries such as `split` work over lists with predicates and delimiters. Haskell has not settled on a single searcher abstraction, which suggests the difficulty is real and the trade-offs here are reasonable.

## Unresolved questions

Should `Needle` be implemented for regular expressions in the standard library? No; that is left to the `regex` crate.

Should the `Index` type be exposed on stable, or hidden behind the `Haystack` trait methods? This RFC proposes that implementing `Hay` remain unstable, while using needles and implementing `Needle` for existing hays is stable.

How should `&mut str` replacement interact with in-place case conversion? This is left for later.

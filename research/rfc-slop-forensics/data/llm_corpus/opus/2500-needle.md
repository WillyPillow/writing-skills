- Feature Name: `needle`
- Start Date: 2018-07-23
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

Generalize the string pattern API, renamed here from "pattern" to "needle", so that searching works on `&str`, `&mut str`, `&[T]`, `&mut [T]`, `Vec<T>` and `&OsStr`, not just `&str`. Split the API into two layers: a *haystack* trait that describes what can be searched, and *searcher* traits that describe how to search it. Then stabilize the result, so that third-party crates can supply their own needles and haystacks.

# Motivation

## Stabilize the pattern API

`str::find`, `str::split`, `str::replace` and about twenty other methods accept a generic `P: Pattern<'a>`. That is why `s.find('x')`, `s.find("xy")`, `s.find(char::is_whitespace)` and `s.find(&['a', 'b'][..])` all work. The `Pattern` trait itself, though, has been unstable since 1.0. As a result:

- Crates such as `regex` cannot implement `Pattern`, so you cannot write `s.split(&re)`. Each such crate reinvents `split`, `find_iter`, `replace` and the rest.
- Slices get only a small subset of the string methods. `[T]::split` exists, but there is no `[T]::find`, no `[T]::replace`, and no way to search a slice for a subslice at all.
- `OsStr` has almost no search methods. Code that handles paths and environment variables often has to convert to `str` (losing non-UTF-8 data) just to call `starts_with`.

The current `Pattern` trait cannot be stabilized as it stands. It is tied to `&'a str` and `char` indices, it has no story for mutable haystacks, and its `Searcher` trait mixes up the job of the haystack (knowing where boundaries are) with the job of the algorithm (finding matches).

## Implement OMG-WTF-8

On Windows, `OsStr` is stored as WTF-8, which can contain unpaired surrogates. Matching a needle against such data needs care: a needle that ends in a high surrogate must be able to match the first half of a surrogate pair in the haystack. The encoding this RFC calls OMG-WTF-8 extends WTF-8 so that a slice can begin or end in the middle of a surrogate pair. Once a needle API exists that is generic over haystacks, `OsStr::split` and similar methods fall out of the same code as `str::split`, as long as `OsStr` slicing is defined. OMG-WTF-8 is the minimum change that defines it.

# Guide-level explanation

Two words do most of the work.

- A **haystack** is something you search in: a string slice, a byte slice, a vector, an OS string.
- A **needle** is something you search for: a character, a substring, a predicate, a set of characters, a regex.

All the familiar methods now live as free functions in `core::needle::ext`, generic over both:

```rust
use std::needle::ext;

let words: Vec<&str> = ext::split("a,b,,c", ',').collect();
let pos = ext::find(&[1, 2, 3, 4, 3][..], &[4, 3][..]);   // Some(3)
let fixed = ext::replace(Vec::from(&b"hello"[..]), b'l', b"L");
```

The inherent methods on `str` and `[T]` keep working and become thin wrappers over these functions, so existing code is unchanged.

To make your own type searchable, implement `Haystack`. To make your own type usable as a needle, implement `Needle<H>` for the haystacks it supports. A regex crate, for example, would implement `Needle<&str>` for `&Regex`, and immediately get `split`, `rsplit`, `matches`, `replace`, `trim_start_matches` and the rest.

# Reference-level explanation

## API

The core traits look like this, with some bounds and lifetimes shortened:

```rust
pub unsafe trait Hay {
    type Index: Copy + Eq;
    fn empty<'a>() -> &'a Self;
    fn start_index(&self) -> Self::Index;
    fn end_index(&self) -> Self::Index;
    unsafe fn next_index(&self, index: Self::Index) -> Self::Index;
    unsafe fn prev_index(&self, index: Self::Index) -> Self::Index;
    unsafe fn slice_unchecked(&self, range: Range<Self::Index>) -> &Self;
}

pub unsafe trait Haystack: Deref<Target: Hay> + Sized {
    fn empty() -> Self;
    unsafe fn split_around(self, range: Range<Self::Target::Index>) -> [Self; 3];
    unsafe fn slice_unchecked(self, range: Range<Self::Target::Index>) -> Self;
    fn restore_range(&self, original: Range<_>, parent: Range<_>) -> Range<_>;
}

pub unsafe trait Searcher<A: Hay + ?Sized> {
    fn search(&mut self, span: Span<&A>) -> Option<Range<A::Index>>;
}

pub unsafe trait Consumer<A: Hay + ?Sized> {
    fn consume(&mut self, span: Span<&A>) -> Option<A::Index>;
}

pub trait Needle<H: Haystack>: Sized {
    type Searcher: Searcher<H::Target>;
    type Consumer: Consumer<H::Target>;
    fn into_searcher(self) -> Self::Searcher;
    fn into_consumer(self) -> Self::Consumer;
}
```

`Hay` is the unsized data (`str`, `[T]`, `OsStr`). `Haystack` is the owning or borrowing handle to it (`&str`, `&mut [T]`, `Vec<T>`). Keeping the two apart lets one searcher implementation serve every handle type over the same data. A `Searcher` finds the next match anywhere in a span. A `Consumer` checks for a match only at the start of a span, which is all that `starts_with` and `trim_start_matches` need, and is often much cheaper.

`Span` pairs a hay with the range being searched, so a searcher can look at bytes just outside the range when it needs context, for example to avoid matching inside a UTF-8 code point.

`split_around` is the key operation for mutable and owned haystacks. It splits `self` into before, match and after without aliasing, which is what lets `split` yield `&mut str` pieces or `Vec<T>` pieces safely.

## Standard library changes

- Add `core::needle` with the traits above and `core::needle::ext` with the generic algorithms.
- Implement `Hay` for `str`, `[T]` and `OsStr`, and `Haystack` for their shared, mutable and owned forms.
- Implement `Needle` for `char`, `&str`, `&String`, `FnMut(char) -> bool`, `&[char]`, and for `&[T]` and `FnMut(&T) -> bool` over slices.
- Re-implement the existing `str` and `[T]` methods on top of `ext`. Deprecate `core::str::pattern`.
- Change `OsStr` on Windows to OMG-WTF-8 and add the search methods.

## Performance

The two-way substring algorithm used by `str::find` today is kept. Specializations for single-byte needles still compile down to `memchr`. Benchmarks on a prototype show no regression on the existing string benchmarks, and a large speedup for slice-in-slice search, which today has to be written by hand with `windows()`.

# Drawbacks

- The API is large. Two trait layers plus an extension module is more to learn than one `Pattern` trait.
- Changing the `OsStr` encoding on Windows affects the internal representation. It should be invisible, but it touches unsafe code.
- The free functions in `ext` duplicate inherent methods. That is deliberate, but it can look redundant.

# Rationale and alternatives

## Principles

1. Existing code keeps compiling with the same behavior.
2. One algorithm implementation per needle, shared by all haystack handle types.
3. No performance loss for the common cases.
4. Third parties can extend both sides.

## Design rationales

Splitting `Searcher` from `Consumer` lets anchored operations avoid a full search. Separating `Hay` from `Haystack` is what makes principle 2 possible. Making `Hay` an unsafe trait puts the burden of index validity on the few implementers rather than on every caller.

## Miscellaneous decisions

The rename to "needle" avoids a clash with pattern matching in `match`, which confuses beginners reading docs. Double-ended searching is kept as a separate `ReverseSearcher` trait rather than folded into `Searcher`, because many needles, such as regexes, cannot search backward efficiently.

## Alternatives

Stabilize the existing `Pattern` as is, accepting that it covers only `&str`. Or provide separate, unrelated APIs for slices and `OsStr`. Both leave the duplication problem in place.

# Prior art

## Previous attempts

RFC 528 introduced the current `Pattern` trait. Several later pre-RFCs tried to extend it to slices and ran into the lack of a haystack abstraction.

## Haskell

The `split` and `stringsearch` packages are generic over list-like containers but need separate code per container type. Rust's trait system allows sharing one implementation, which is the main improvement this design aims for.

# Unresolved questions

- Exact naming of the `ext` module and whether its functions should become inherent methods on more types.
- Whether `Vec<T>` haystacks should support in-place `replace` that changes length.
- How to expose OMG-WTF-8 slicing without committing to the encoding publicly.

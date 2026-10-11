# Rust RFC 2500: needle

- Feature Name: `needle`
- Start Date: 2018-08-03
- RFC PR: rust-lang/rfcs#2500
- Rust Issue: rust-lang/rust#56345

## Summary

This RFC proposes a generalization of the string pattern API that the standard library currently calls `Pattern`. The generalized trait, which this document calls `Needle`, would allow searching and splitting not only `&str` values but also `&mut str`, slices `&[T]` and `&mut [T]`, owned `Vec<T>`, and `&OsStr`. The goal is a single, coherent way to ask "where does this sub-sequence occur?" across the most common sequence-like types in the language.

The name is provisional. The word "needle" is meant to contrast with "haystack," the value being searched, and the RFC uses it throughout for readability.

## Motivation

The current pattern machinery was designed for strings. It works well for `str::find`, `str::split`, and related methods, and it supports a number of pattern types including characters, closures over characters, and string slices. However, the same kind of search is frequently needed on byte buffers and on slices of arbitrary element types, and in those cases users fall back to ad hoc loops or to third-party crates.

Two more pressures motivate the change. First, operating-system strings such as `OsStr` are only partially supported by the existing search functions, which makes portable code that handles paths and environment variables more awkward than it should be. Second, the existing `Pattern` trait exposes details that are hard to extend without breaking changes, so any generalization has to be designed carefully to avoid locking in a shape that will later prove too narrow.

The RFC does not aim to make every search operation available on every type. Its scope is the search and split interface that users reach for most often, and it treats the core question as a matter of how a needle is compared against a haystack.

## Guide-level explanation

From the point of view of a user, the change should feel like a natural extension. A slice search that today requires a manual loop would be written as a method call:

```rust
let bytes = b"hello, world";
let index = bytes.find(b"world");
```

The same method would accept a single element, a sub-slice, or a predicate, in the same way that string search already accepts a character, a string, or a closure. Users who already know the string API should not need to learn new concepts. The only new idea is that the thing being searched for is called a needle, and that the set of acceptable needles depends on the type of the haystack.

Mutable variants such as searching through `&mut str` are provided for cases where a caller wants to find a region and then modify it in place. These variants do not change the matching rules, only the borrow that is returned.

## Reference-level explanation

The central change is a trait that describes how a needle searcher walks a haystack. The existing `Searcher` and `ReverseSearcher` traits are retained, but they are parameterized over the haystack type rather than fixed to `str`. A needle type implements a constructor method that returns a searcher for a given haystack, and the searcher yields match positions in order.

Matching is defined in terms of equality of elements. For slices, two windows match when their elements compare equal under `PartialEq`. For strings, the existing rules based on UTF-8 code points continue to apply, so that the observable behavior of current code does not change.

The RFC specifies that searchers must never report overlapping matches unless the method explicitly asks for them, and that empty needles behave as they do today: they match at every valid boundary of the haystack.

### API

The new trait is named `Needle`. It is implemented for the following types, in addition to the existing string needles:

- `&[T]` where `T: PartialEq`, for searching slices by sub-slice
- `&mut [T]` in the mutable search variants
- `Vec<T>` by reference, as a convenience so that owned buffers can be searched directly
- `&OsStr` for searching operating-system strings

Methods such as `find`, `rfind`, `contains`, `starts_with`, `ends_with`, `split`, and `replace` are provided through the existing method families and are generalized to accept any `Needle` whose haystack type matches.

### Standard library changes

The standard library's `str` and slice modules change in a limited way. Their existing method signatures remain, and new generic methods are added beside them. Code that calls the string methods with string arguments continues to compile without modification. The RFC notes that some type inference situations may change, and it proposes a transition period in which the more general signatures are introduced under a feature gate before stabilization.

## Performance

The generalized design preserves the performance characteristics of the current string search. The RFC asks implementers to keep the two-way and fast-path algorithms for string haystacks, and to use straightforward linear scanning for generic slices unless a specialization is available. It is expected that byte-slice search can use the same optimized routines as string search, since the matching rules coincide for `u8`.

Benchmarks in the prototype show no regressions for string workloads and a modest benefit for byte-slice search when the specialized path is taken. The RFC acknowledges that generic slice search without specialization is slower than hand-written code in some cases, and it argues that the simplicity of a single API outweighs that cost for most users.

## Drawbacks

The principal drawback is complexity. A single trait that serves strings, slices, and operating-system strings must balance several sets of matching rules, and the documentation must explain them clearly. There is a risk that users will be surprised by the difference between searching `&str` for a character and searching `&[u8]` for a byte, since the two may look similar but are not identical in their handling of multi-byte encodings.

Another drawback is that the trait surface becomes larger, which increases the amount of standard library code that must be maintained and tested. The RFC argues that this cost is acceptable because the existing string machinery already carries much of the same complexity.

## Rationale and alternatives

The RFC considered three alternatives. The first was to leave the pattern API alone and add separate, dedicated methods for slices and `OsStr`. This is simpler in the short term but produces a family of near-duplicate methods and makes it harder to write code that is generic over the haystack type.

The second alternative was to introduce a new crate outside the standard library that provides the generalized search. This keeps the standard library small but means that the most common cases would still depend on an external dependency, and it would fragment the ecosystem.

The third option, which the RFC adopts, is to generalize the existing trait and to make the change incremental, starting with the cases that have the clearest semantics.

## Principles

The design follows three principles. The first is that searching for a sub-sequence should look the same regardless of the element type. The second is that the existing string behavior should be preserved exactly, so that the generalization is a superset rather than a reinterpretation. The third is that the trait should leave room for future needle types without requiring changes to callers.

## Prior art

Several languages provide a generic substring or sub-sequence search over arrays and byte buffers, typically through a single method name. The RFC draws on these examples, and in particular on the observation that users rarely distinguish between searching a string and searching a sequence of bytes when they think about the task.

## Previous attempts

Earlier efforts to unify the pattern API were carried out on a more limited scope and stalled over questions about how to handle mutable haystacks and about whether the trait should be sealed. The present proposal addresses those questions by restricting the mutable variants to methods that return borrows and by keeping the trait open for implementation within the standard library only at first.

## Unresolved questions

The RFC leaves several questions open. It is not yet decided whether `Needle` should be exposed as a public trait or kept as an implementation detail behind the methods. The naming of the trait is also provisional. The interaction with `Cow` and with owned haystacks needs further study, and the team has asked for more data on how often each form is used in practice before settling the default behavior of the `Vec<T>` implementation.

## Conclusion

Generalizing the pattern API would give users one consistent search interface across strings, slices, and operating-system strings. The design keeps current behavior intact, provides a clear migration path through a feature gate, and avoids a proliferation of specialized methods. The RFC recommends proceeding with the staged plan and with further discussion of the open naming and exposure questions.

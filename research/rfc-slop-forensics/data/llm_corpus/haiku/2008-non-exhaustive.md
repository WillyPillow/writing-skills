# Rust RFC 2008: `non_exhaustive`

- Feature Name: `non_exhaustive`
- Start Date: 2016-11-14
- RFC PR: rust-lang/rfcs#2008
- Rust Issue: rust-lang/rust#44109

## Summary

This RFC introduces the `#[non_exhaustive]` attribute for enums, structs, and enum variants. The attribute records that a type or variant is expected to gain more members in the future. For an enum, it forces downstream crates to include a wildcard arm when matching on the enum, so that adding a variant later is not a breaking change. For a struct or an enum variant, it prevents downstream crates from constructing the type with a struct literal or matching it exhaustively, so that adding a field later is not a breaking change.

The attribute is intended as a post-1.0 successor to the earlier proposal in RFC 757, which covered the same problem space in a more limited form. This document keeps the core idea of that proposal and adds rules for structs and variants, along with the lint and diagnostic behavior that makes the attribute usable in practice.

## Motivation

Library authors frequently want to publish a public enum that describes a set of cases the library currently knows about, while reserving the right to add cases in a later minor release. Without a marker, the compiler treats every public enum as closed. A downstream `match` that lists every variant will stop compiling as soon as the upstream crate adds one more. Under Rust's stability guarantees, that outcome is a breaking change, and the upstream author is forced either to avoid adding variants or to bump a major version.

Structs have the same problem in a different form. A public struct with public fields can be built with a literal expression by any downstream crate. If the upstream author adds a field, every such literal breaks. Private fields avoid the problem but make the struct awkward to construct, since the only way to build it is through a function the author must provide.

The attribute addresses both cases with a single, explicit annotation. It tells the compiler and the reader that the set of variants or fields is open-ended, and it asks downstream code to be written so that new members can appear without breaking it.

## Guide-level explanation

An author marks an enum like this:

```rust
#[non_exhaustive]
pub enum ErrorKind {
    NotFound,
    PermissionDenied,
    TimedOut,
}
```

A downstream crate that matches on `ErrorKind` must provide a catch-all arm:

```rust
match kind {
    ErrorKind::NotFound => { /* ... */ }
    ErrorKind::PermissionDenied => { /* ... */ }
    ErrorKind::TimedOut => { /* ... */ }
    _ => { /* handle cases unknown at compile time */ }
}
```

A struct marked the same way cannot be constructed with a literal from another crate, and cannot be destructured with a pattern that lists every field without using `..`. The author remains free to add fields in a later release. Code in the defining crate is unaffected, since the attribute only changes how other crates see the type.

The attribute may also be placed on an individual enum variant that carries fields. In that case, downstream code may still name the variant in a pattern, but it must use `..` to ignore the fields it does not mention, and it cannot build the variant with a literal that lists all of its fields.

## Reference-level explanation

The attribute takes no arguments and may be applied to a `struct`, an `enum`, or a variant of an enum. Applying it to any other item is an error.

For an annotated enum, the compiler treats the enum as having an implicit additional variant from the point of view of exhaustiveness checking outside the defining crate. A `match` in a downstream crate is exhaustive only if it contains a wildcard or binding pattern that covers every value not otherwise listed. Inside the defining crate, the attribute has no effect, so the author can still write exhaustive matches and receive the usual compiler checks.

For an annotated struct or variant, the compiler forbids two things in downstream crates: constructing the type with a struct expression that lists every field, and matching it with a struct pattern that lists every field without a trailing `..`. Construction through a function or through struct update syntax from a value that already exists remains permitted. The defining crate is not restricted in either case.

Each restriction is reported with a diagnostic that names the attribute and the defining crate. The diagnostic should suggest the wildcard arm or the `..` rest pattern, so that the fix is obvious to a developer who did not write the upstream code.

The attribute does not change the layout, the calling convention, or the trait implementations of the type. It is a compile-time marker with no runtime effect.

## Drawbacks

The attribute adds a kind of friction for downstream users. A complete match now requires a wildcard arm, which can hide future variants from the compiler's warnings. Authors who use the attribute must document what their wildcard arms are expected to do.

The attribute also introduces a split between how a type behaves inside and outside its defining crate. Some developers find this surprising, and the error messages must explain it clearly.

## Rationale and alternatives

One alternative is to rely on documentation alone, asking authors to note that a type may grow. This does not help the compiler, and it leaves the most common mistake, an exhaustive downstream match, entirely to human attention.

A second alternative is to make every public enum non-exhaustive by default. This would make adding variants safe in all cases, but it would also make the common case of a small, closed set of options more verbose. It would also break existing code that relies on exhaustive matching, which is not acceptable under the stability guarantees.

A third alternative is to make private fields mandatory for structs that may grow. The problem is that private fields prevent construction entirely, and an author who wants users to build the value directly has to add constructor functions. The attribute keeps the struct constructible while still reserving the right to change it.

## Prior art

Several languages distinguish between closed and open type definitions, and some language communities have settled on conventions for growing a public API without breaking callers. The attribute draws on these conventions while making the choice explicit in the source code.

## Unresolved questions

The exact wording of the lint for unreachable wildcard arms inside the defining crate is still open. The RFC proposes that the lint not fire for annotated types, since the attribute has no effect there, but the implementation should confirm that this does not mask real mistakes.

It is also unresolved whether the attribute should be allowed on type aliases, and what it should mean for generic types whose parameters are not yet fixed. These questions can be answered during implementation without changing the core design.

## Future possibilities

A later revision could allow the attribute to carry a reason string, which tooling could display when it warns about a wildcard arm. The attribute could also interact with editions, so that a future edition makes certain patterns stricter. Neither change is needed for the initial design.

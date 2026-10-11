# Rust RFC 2008: non_exhaustive

Status: [TODO: RFC status, tracking issue and date]

## Summary

This RFC introduces the `#[non_exhaustive]` attribute for enums and structs. The attribute marks a type as open to future additions. On an enum, it forces downstream crates to include a wildcard arm in `match` expressions, so that adding a variant does not break them. On a struct or an enum variant, it prevents downstream crates from constructing the type or matching it exhaustively, so that adding a field does not break them.

## Motivation

The purpose of the attribute is to let the defining crate add variants and fields without a breaking change. The abstract does not describe a case where such a change broke downstream code, or what the break cost. [TODO: an instance from the author's material in which adding a variant or field to a published type broke downstream code. Give the crate, the version and the error.]

[TODO: how many downstream crates such a change would affect, if the author has measured this.]

## Relation to RFC 757

The abstract calls this RFC a post-1.0 version of RFC 757, with some additions. The relation is stated, so a reader can check the additions against RFC 757. [TODO: what RFC 757 proposed, taken from its text, so a reader can see what the post-1.0 version keeps.]

[TODO: the list of additions, each with the reason it was added. The abstract does not name them, and this section cannot be written without them.]

## Design: enums

The force is that adding a variant breaks any downstream `match` that lists every current variant. [TODO: a count or example of such matches in a named body of code, if the author has one.]

The decision is that downstream code must include a wildcard arm. The cost is that such code can no longer check, for the variants that exist today, that every case is handled, because the wildcard covers any future variant. [TODO: whether the author accepts this cost, and the reason.]

[TODO: the options considered for enums, including keeping the current behavior, each with the reason it lost.]

[TODO: the deciding reason for the enum design. The abstract says what the attribute does but not which factor decided it.]

## Design: structs and enum variants

The force is that adding a field breaks downstream code that builds the type with a literal or matches every field. The decision is that downstream crates may not construct the type or match it exhaustively.

The cost is that downstream crates lose struct literal construction, so the defining crate must provide some other way for users to create values. [TODO: how the defining crate would provide construction, and an example if the author has one.]

[TODO: the options considered for structs and variants, each with the reason it lost.]

## Reversibility

[TODO: what happens when the attribute is removed from a published type, and whether that removal is itself a breaking change. The abstract does not say, and the answer decides how much care the first decision needs.]

## Compatibility and semver

The abstract says that adding variants or fields to a type marked this way is not a breaking change. That is a compatibility claim, and it needs support. [TODO: the test of this claim, such as a set of additions and the downstream builds that were checked, with the results.]

## Open questions

[TODO: the unresolved points and the input each one needs. Candidates from this draft are the additions to RFC 757, the behavior when the attribute is removed, and the construction pattern for struct types.]

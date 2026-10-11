# Rust RFC 2008: non_exhaustive

## Summary

This RFC introduces the `#[non_exhaustive]` attribute for enums and structs. The attribute tells that more variants or fields may be added in the future. On an enum, it forces downstream crates to add a wildcard arm to `match` statements, so that a new variant is not a breaking change. On a struct or an enum variant, it prevents downstream crates from constructing the type or matching it exhaustively, so that a new field is not a breaking change. The RFC is a post-1.0 version of RFC 757, with some additions. [TODO: state which parts of RFC 757 are carried over, and which additions are new.]

## Motivation

A library author who adds a variant to a public enum breaks every downstream `match` that lists all the variants. The same is true for a public struct when a field is added and downstream code builds the struct with a literal. [TODO: give one example from a published library in which a release broke downstream code for this reason, with the library name and version.]

The obstacle is that the author cannot know, at the time of writing the type, whether a future variant or field will be needed. The attribute lets the author say that the type may grow, so that downstream code is written with that in mind from the start. [TODO: state whether the author has data on how often public enums grow after release.]

Without the attribute, the author has two bad options. The author can avoid adding variants or fields, which limits the library. Or the author can accept breaking releases. [TODO: state which of these the motivating library has taken, and at what cost.]

## Guide-Level Explanation

A library marks an enum with `#[non_exhaustive]` to say that new variants may be added. A downstream crate that matches on the enum must then include a wildcard arm. The wildcard arm handles any variant the downstream crate does not know about.

A library marks a struct the same way to say that new fields may be added. A downstream crate cannot build the struct with a literal, and it cannot match the struct exhaustively. It uses a constructor or a pattern with `..` instead, where the library provides one. [TODO: give the before and after code for each case. The examples are not in the material.]

[TODO: give the error that a downstream crate sees when it omits the wildcard arm, and when it tries to build a marked struct with a literal.]

## Reference-Level Explanation

[TODO: specify exactly which constructs are affected: enum definitions, struct definitions, enum variants, and any restrictions on combining the attribute with other attributes or with `#[repr]`.]

[TODO: specify how the attribute interacts with generics, with types that are re-exported from another crate, and with crates in the same workspace.]

## Drawbacks

Downstream code must write a wildcard arm even when the author knows every variant. The cost is a small amount of code and a possible warning for unreachable patterns in some cases. [TODO: state whether the author has checked the warning behavior, and in which cases it occurs.]

The attribute makes the type harder to use for the downstream author, because the type cannot be constructed directly. [TODO: state how a downstream author is expected to work around this, and whether the library must provide a constructor.]

## Rationale and Alternatives

The central tension is between the library author's freedom to change a public type and the downstream author's need to write code against it. The attribute resolves the tension by moving the cost of future growth to the downstream code that is written today. [TODO: state whether the author regards this cost as acceptable, and why.]

The alternative is to leave the rule as it is and rely on semver discipline. [TODO: state whether this was considered, and the reason it lost.]

The attribute is specified for both enums and structs because the breaking change is the same in both: a downstream match or literal fails when a new member appears. [TODO: confirm this reasoning with the author. A reviewer may argue the two cases differ.]

## Unresolved Questions

[TODO: list the open questions. Candidates include the exact form of the wildcard requirement in nested patterns, and whether the attribute should apply to unions.]

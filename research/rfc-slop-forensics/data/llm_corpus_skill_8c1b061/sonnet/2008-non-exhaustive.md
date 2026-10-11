# RFC 2008: non_exhaustive

- Feature Name: `non_exhaustive`
- Start Date: [TODO]
- RFC PR: [TODO]
- Rust Issue: [TODO]

## Summary

This RFC introduces the `#[non_exhaustive]` attribute for enums and structs. The attribute states that more variants or fields may be added in the future.

On an enum, the attribute forces downstream crates to include a wildcard arm in any `match` on it. Adding a variant later is then not a breaking change.

On a struct or enum variant, the attribute stops downstream crates from constructing the type with a literal and from matching it exhaustively. Adding a field later is then not a breaking change.

This is a post-1.0 version of RFC 757, with some additions. [TODO: list the additions. The abstract says "some additions" without naming them.]

## Motivation

A library that publishes a public enum makes a promise about its variants. Downstream code that matches on the enum without a wildcard arm compiles only while the variant list stays as it was. If the library adds a variant, every such `match` stops compiling. The library author therefore cannot add the variant in a minor release without breaking someone.

Consider a library with this error type:

```rust
pub enum Error {
    NotFound,
    PermissionDenied,
}
```

A downstream crate writes a `match` that handles both variants and has no `_` arm. If the library adds `Timeout`, the downstream crate fails to build. Under this RFC the library marks `Error` as `#[non_exhaustive]`, and the compiler rejects the downstream `match` from the start, so the downstream author writes the wildcard arm before any variant is added. [TODO: author's real example from a crate that hit this. The one above is constructed for illustration.]

The same problem applies to structs. A downstream crate can build a public struct with a literal that names every field, or can match on it with a pattern that names every field. Adding a field to the struct breaks both uses. The attribute prevents both, so the library may add the field later.

The tension in this design is between two parties. The library author wants room to evolve a type without a major version bump. The downstream author wants the compiler to check that every case is handled, and a forced wildcard arm gives up that check. The RFC resolves it in favor of the library author, and limits the loss to types the library chooses to mark. [TODO: the author's reasons for the resolution, and whether the loss of the exhaustiveness check was a concern raised in discussion. The material does not record the discussion.]

## Guide-level explanation

### Enums

Mark an enum:

```rust
#[non_exhaustive]
pub enum Error { NotFound, PermissionDenied }
```

Within the defining crate, the enum behaves as before: a `match` there may be exhaustive without a wildcard. In another crate, a `match` on `Error` must have a wildcard arm or another catch-all pattern:

```rust
match err {
    Error::NotFound => { /* ... */ }
    Error::PermissionDenied => { /* ... */ }
    _ => { /* ... */ }
}
```

The library can now add `Timeout` and the downstream code still compiles, taking the `_` arm for the new variant.

### Structs and variants

Mark a struct:

```rust
#[non_exhaustive]
pub struct Config { pub verbose: bool }
```

In another crate, `Config { verbose: true }` does not compile, because the literal would fix the field list. A pattern `Config { verbose }` must end with `..`, since more fields may exist. [TODO: author to state how a downstream crate then creates a `Config`. The expected route is a constructor function in the defining crate, but the abstract does not say.]

The attribute may also sit on an enum variant. [TODO: confirm. The abstract mentions "structs or enum variants" and the same rules for construction and matching. State whether a tuple variant or a unit variant can carry the attribute.]

## Reference-level explanation

The attribute has effect only across crate boundaries. The defining crate sees the type as it is written, so its own code can construct and match the type freely.

1. For an enum, a `match` outside the defining crate that has no wildcard or catch-all arm is an error.
2. For a struct or variant, a struct literal outside the defining crate is an error.
3. For a struct or variant, a pattern outside the defining crate that does not end in `..` is an error.

[TODO: author to state the crate boundary for items re-exported through another crate, and for crates in the same workspace. State also how the attribute interacts with `#[repr]` and with deriving traits.]

[TODO: author to state whether existing uses of `as` casts on field-less enums are affected.]

## Drawbacks

The attribute removes the exhaustiveness check from every downstream `match` on a marked enum. A downstream author who wants to learn about new variants no longer gets a compile error to prompt that. The library author must document new variants in another way. [TODO: author's response, such as a lint that warns when the wildcard arm hides a known variant. The material records none.]

A struct marked `non_exhaustive` cannot be built by downstream code with a literal, so the library must provide constructors or builders. This is more API for the library to write. [TODO: author's view of this cost.]

The attribute is a promise to the library's own future, and removing it later is a breaking change in the other direction only if downstream code relied on the forced wildcard, which cannot cause an error. Adding it to a type that was exhaustive before is a breaking change, because existing downstream matches and literals stop compiling. [TODO: author to confirm this reading of reversibility, as the abstract is silent.]

## Rationale and alternatives

The abstract describes the RFC as a post-1.0 version of RFC 757. [TODO: what RFC 757 proposed, and why a revision was needed after 1.0. The material names the earlier RFC and nothing about it, so this document does not describe it.]

[TODO: alternatives. Candidate questions for the author: a hidden dummy variant, which libraries use today as a workaround, and a convention of private fields on structs. State each only if it was weighed and say why the attribute won.]

## Unresolved questions

1. The additions over RFC 757.
2. How downstream code constructs a marked struct.
3. The behavior across re-exports and within a workspace.
4. Whether a lint should flag a wildcard arm that hides known variants.

# Rust RFC 2008: non_exhaustive

- Feature Name: `non_exhaustive`
- Start Date: [TODO: date]
- RFC PR: [TODO]
- Rust Issue: [TODO]

## Summary

This RFC introduces the `#[non_exhaustive]` attribute for enums and structs. The attribute indicates that more variants or fields may be added to the enum or struct in the future.

On an enum, the attribute forces downstream crates to add a wildcard arm to `match` expressions, so that adding a new variant is not a breaking change. On a struct or an enum variant, it prevents downstream crates from constructing values and from matching exhaustively on fields, so that adding a new field is not a breaking change.

This is a post-1.0 version of RFC 757, with some additions.

## Motivation

A library author who publishes an enum makes a promise, whether they mean to or not: the set of variants is fixed. Consider an error type:

```rust
pub enum ConfigError {
    NotFound,
    PermissionDenied,
    Parse(String),
}
```

A downstream crate can match it exhaustively:

```rust
match err {
    ConfigError::NotFound => ...,
    ConfigError::PermissionDenied => ...,
    ConfigError::Parse(msg) => ...,
}
```

If the library later adds a variant, `ConfigError::Io(io::Error)`, that downstream `match` stops compiling. Under semantic versioning, adding the variant is a major-version change. Many enums exist to grow: error kinds, protocol message types, configuration options. Their authors want to add cases in minor releases.

Structs with public fields have the same problem. A downstream crate can build a value with a struct literal, `Options { verbose: true, depth: 3 }`, or destructure it with a pattern that names every field. Both stop compiling if the library adds a field.

Library authors work around this today. For enums, one known workaround is a hidden variant, for example `#[doc(hidden)] __Nonexhaustive`, which downstream code is not meant to name, so that every `match` needs a wildcard. For structs, one workaround is a private field, which prevents struct literals and exhaustive patterns outside the crate. [TODO: confirm these are the workarounds the author has in mind, and cite one or two crates that use them, if the author has examples.]

Both workarounds have costs that the attribute removes:

1. A hidden variant is still a variant. Code inside the defining crate must handle it in every `match`, and downstream code can still name it if it chooses to, which defeats its purpose.
2. A private field takes up a name, and in a struct that is otherwise all public it misleads readers about the type's contents.
3. Neither workaround states the intent. A reader sees a strange variant or field, not a promise about future versions.

## Guide-level explanation

Mark an enum `#[non_exhaustive]` when you expect to add variants:

```rust
#[non_exhaustive]
pub enum ConfigError {
    NotFound,
    PermissionDenied,
    Parse(String),
}
```

In other crates, a `match` on `ConfigError` must include a wildcard arm:

```rust
match err {
    ConfigError::NotFound => ...,
    ConfigError::PermissionDenied => ...,
    ConfigError::Parse(msg) => ...,
    _ => ...,
}
```

Mark a struct `#[non_exhaustive]` when you expect to add fields:

```rust
#[non_exhaustive]
pub struct Options {
    pub verbose: bool,
    pub depth: u32,
}
```

Other crates can read the public fields, but they cannot write `Options { verbose: true, depth: 3 }`. A pattern that destructures `Options` must end with `..`. The defining crate is expected to provide a constructor, such as `Options::default()` or a builder.

The attribute can also be placed on a single enum variant that has fields. Downstream crates then cannot construct that variant, and patterns on it need `..`, but the enum itself can still be matched exhaustively.

Inside the defining crate, the attribute has no effect. The crate can match exhaustively and use struct literals as before, because any change to the type is made in the same crate, at the same time as the code that uses it.

## Reference-level explanation

### Enums

For a `#[non_exhaustive]` enum defined in another crate, exhaustiveness checking treats the enum as if it had one additional variant that no pattern can name. A `match` is exhaustive only if it contains an arm that matches every value, such as `_` or a binding.

### Structs

For a `#[non_exhaustive]` struct defined in another crate:

1. Struct expressions are rejected, including those with functional record update (`..base`).
2. Struct patterns must include `..`.
3. For a tuple struct, the constructor function is treated as if it had the visibility of the crate. [TODO: confirm the exact visibility the author intends. The goal is that downstream code cannot call `Options(true, 3)`.]

### Enum variants

For a `#[non_exhaustive]` variant of an enum defined in another crate, rules 1 to 3 for structs apply to the variant.

### Unit structs and unit variants

[TODO: whether the attribute is allowed on unit structs and unit variants, and what it means there. Adding a field to a unit struct changes its syntax, so the attribute would need to prevent downstream code from writing the bare unit expression.]

## Drawbacks

The wildcard arm removes a warning that downstream crates may want. When a library adds a variant to a non-exhaustive enum, downstream code still compiles, and the new variant goes to the wildcard arm. The compiler cannot tell the downstream author that a new case exists and might need its own arm. For an enum used to dispatch behavior, silent fallthrough may be worse than a compile error. [TODO: whether the author proposes a lint, for example one a downstream crate can opt into, that warns when a wildcard arm covers variants that exist at compile time.]

The attribute shifts work onto downstream code. Every `match` needs a wildcard, even when the downstream author handles all current variants and has nothing sensible to do for an unknown one.

Applying the attribute to an existing public type is itself a breaking change, because it rejects downstream code that compiled before. Removing it later is not breaking. Library authors therefore need to decide when they first publish a type. [TODO: confirm this reading and whether the RFC should say so in its guidance to library authors.]

## Rationale and alternatives

Compared with the hidden-variant and private-field workarounds, the attribute states the author's intent directly, removes the dummy item, and has no effect inside the defining crate.

[TODO: the alternatives the author actually considered, each with the reason it lost. A suggestion for the author to evaluate is a pair of attributes, one for enums and one for structs, rather than one attribute with two meanings.]

## Relation to RFC 757

The abstract describes this RFC as a post-1.0 version of RFC 757, with some additions. [TODO: what RFC 757 proposed, why it was not adopted before 1.0, and what this RFC adds to it. If the additions are the struct and variant forms, say so here. Describe RFC 757 from its text, not from memory.]

## Unresolved questions

1. The visibility of tuple-struct constructors (Structs).
2. Whether unit structs and unit variants may carry the attribute (Unit structs and unit variants).
3. Whether a lint warns about wildcard arms that cover known variants (Drawbacks).
4. The relation to RFC 757 (Relation to RFC 757).

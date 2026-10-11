- Feature Name: `non_exhaustive`
- Start Date: [TODO: date]
- RFC PR: [TODO: link]
- Rust Issue: [TODO: link]

# Summary

This RFC adds the `#[non_exhaustive]` attribute for enums, structs and enum variants. The attribute says that more variants or fields may be added later. On an enum, it forces downstream crates to include a wildcard arm in every `match` on the enum, so that adding a variant is not a breaking change. On a struct or an enum variant, it prevents downstream crates from constructing the value with a literal or matching it exhaustively, so that adding a field is not a breaking change.

This is a post-1.0 version of [RFC 757], with additions. [TODO: list what this RFC adds to RFC 757, for example support for structs and enum variants.]

# Motivation

## Adding a variant breaks downstream code

Under Rust's semver conventions, a library can add new items in a minor release. Adding a variant to a public enum is not one of the changes allowed, because it breaks every downstream `match` that lists all the variants:

```rust
// crate `netio`, version 1.0
pub enum ErrorKind { NotFound, PermissionDenied, TimedOut }

// downstream crate
match err.kind() {
    ErrorKind::NotFound => ...,
    ErrorKind::PermissionDenied => ...,
    ErrorKind::TimedOut => ...,
}
```

If `netio` 1.1 adds `ErrorKind::ConnectionReset`, the downstream `match` no longer compiles. For some enums this is the right outcome: a downstream crate that matches on a closed set of states should be told when the set changes. For an enum like `ErrorKind`, where new kinds of error are expected over time, it means the library cannot grow without a major version.

## Adding a field breaks downstream code

The same holds for structs with public fields. If `netio` exports

```rust
pub struct Config { pub timeout_ms: u32, pub retries: u8 }
```

then downstream code can write `Config { timeout_ms: 500, retries: 3 }` or `let Config { timeout_ms, retries } = cfg;`. Adding a field breaks both. A library that wants to add fields later must today make at least one field private, which also prevents downstream code from reading the fields directly.

## The current workaround

For enums, one workaround in use is a hidden variant:

```rust
pub enum ErrorKind {
    NotFound,
    PermissionDenied,
    TimedOut,
    #[doc(hidden)]
    __Nonexhaustive,
}
```

Downstream crates cannot name the hidden variant without reaching into undocumented items, so they must write a wildcard arm. [TODO: cite where this pattern is used, for example in the standard library or widely used crates.] The workaround has three problems:

1. It relies on convention. Nothing stops a downstream crate from matching `__Nonexhaustive` explicitly, after which adding a variant breaks it again.
2. The defining crate must also handle the hidden variant in its own `match` expressions, typically with `unreachable!()`.
3. Tools see a real variant. Documentation generators and IDEs show or complete it unless they special-case the name.

The attribute replaces this convention with a rule the compiler checks.

# Guide-level explanation

## Enums

```rust
#[non_exhaustive]
pub enum ErrorKind { NotFound, PermissionDenied, TimedOut }
```

In a downstream crate, a `match` on `ErrorKind` must include a wildcard arm, even if it lists every variant that exists today:

```rust
match err.kind() {
    ErrorKind::NotFound => ...,
    ErrorKind::PermissionDenied => ...,
    ErrorKind::TimedOut => ...,
    _ => ...,                      // required
}
```

Inside the crate that defines `ErrorKind`, the attribute has no effect. The defining crate knows every variant at compile time, and its own `match` expressions can stay exhaustive and get an error when a variant is added, which is what the crate author wants.

## Structs

```rust
#[non_exhaustive]
pub struct Config { pub timeout_ms: u32, pub retries: u8 }
```

A downstream crate can read `cfg.timeout_ms`, but it cannot write `Config { timeout_ms: 500, retries: 3 }`. To create a `Config`, it must call a constructor that the library provides, such as `Config::default()` or `Config::new(...)`. When it destructures a `Config` in a pattern, it must use `..`:

```rust
let Config { timeout_ms, .. } = cfg;
```

Functional record update syntax, `Config { timeout_ms: 500, ..Config::default() }`, is also rejected downstream. [TODO: confirm. Allowing it would let downstream code construct values, but its meaning is defined field by field, and the RFC needs to say whether that is safe when private invariants exist.]

## Enum variants

The attribute can be placed on a single variant:

```rust
pub enum Event {
    #[non_exhaustive]
    Resize { width: u32, height: u32 },
    Close,
}
```

Downstream code cannot construct `Event::Resize` with a literal and must use `..` when matching its fields. Whether the enum as a whole is exhaustive is unaffected.

# Reference-level explanation

The attribute is accepted on `enum`, `struct` and enum variant definitions. It has no arguments. On any other item it is an error.

Outside the defining crate:

1. A `match` on a `#[non_exhaustive]` enum is checked for exhaustiveness as if the enum had one more variant that no pattern names.
2. A struct expression for a `#[non_exhaustive]` struct or variant is an error.
3. A struct pattern for a `#[non_exhaustive]` struct or variant without `..` is an error.
4. [TODO: decide the visibility of the constructor of a `#[non_exhaustive]` tuple struct or unit struct, which is a function or constant rather than a struct expression.]

Inside the defining crate, none of these rules apply.

# Drawbacks

Downstream crates lose a check they may want. A crate that matches every variant of `ErrorKind` gets no compile error when a new variant appears; the new variant silently goes to the wildcard arm. [TODO: decide whether a lint should let downstream crates opt into a warning when a wildcard arm covers known variants.]

Library authors may apply the attribute by default, out of caution, to enums whose variants are in fact complete. Downstream users then write wildcard arms that can never run.

Adding `#[non_exhaustive]` to an existing public type is itself a breaking change, since downstream code that matched exhaustively stops compiling. Removing it is not breaking. Authors therefore need to decide when they first publish the type.

# Rationale and alternatives

[TODO: record the alternatives the author considered and why each lost. Candidates to ask about, not to be presented as considered without confirmation:]

- [TODO: Keep the hidden-variant convention and document it.]
- [TODO: Apply the attribute only to enums, as RFC 757 did, and leave structs to private fields.]
- [TODO: Make the effect apply inside the defining crate too.]

The reason to leave the defining crate unaffected is that it is the one place where every variant is known and exhaustive matching gives a useful error. [TODO: confirm this is the author's reasoning.]

# Unresolved questions

1. Whether functional record update is allowed downstream.
2. How the attribute affects the constructors of tuple and unit structs.
3. Whether to add an opt-in lint for downstream crates that want to be told about new variants.

[RFC 757]: [TODO: link]

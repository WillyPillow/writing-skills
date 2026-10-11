- Feature Name: `non_exhaustive`
- Start Date: 2017-05-24
- RFC PR: rust-lang/rfcs#2008
- Rust Issue: rust-lang/rust#44109

# Summary

This RFC adds a `#[non_exhaustive]` attribute that can go on enums, structs, and enum variants. It tells downstream crates that the type may gain more variants or fields later.

- On an enum, the attribute makes downstream crates include a wildcard arm in every `match` on the enum, so adding a variant is no longer a breaking change.
- On a struct or enum variant, the attribute stops downstream crates from building the value with a literal and from matching on it exhaustively, so adding a field is no longer a breaking change.

This is a post-1.0 revision of RFC 757 with a few additions.

# Motivation

A library author who publishes a public enum or struct has, under today's rules, frozen its shape. Take this enum:

```rust
pub enum Error {
    NotFound,
    PermissionDenied,
    Interrupted,
}
```

Any downstream crate can write:

```rust
match err {
    Error::NotFound => ...,
    Error::PermissionDenied => ...,
    Error::Interrupted => ...,
}
```

The match compiles because it names every variant. If the library later adds `Error::TimedOut`, that match stops compiling. Under semver, then, adding a variant is a major-version change, even when the author always meant the list to grow.

Authors work around this today with a hidden variant:

```rust
pub enum Error {
    NotFound,
    PermissionDenied,
    Interrupted,
    #[doc(hidden)]
    __Nonexhaustive,
}
```

`std::io::ErrorKind` uses this pattern, and so do many crates on crates.io. It works badly:

- Nothing in the language enforces it. A user who knows the variant exists can match on it, and then the library is stuck again.
- It shows up in IDE completions, in `Debug` output, and in the code of the library itself, which has to handle a variant that should never be constructed.
- The compiler can't tell that the variant is fake, so the library's own matches need an unreachable arm.
- New readers find it confusing.

Structs have the same problem. A public struct with all-public fields can be built with a literal and destructured with a pattern:

```rust
pub struct Config {
    pub verbose: bool,
    pub threads: usize,
}

let c = Config { verbose: true, threads: 4 };
let Config { verbose, threads } = c;
```

Adding a field breaks both lines. The usual fix is a private field (`_priv: ()`), which blocks literal construction everywhere, the defining crate included, and makes the library's own code more awkward.

An attribute that says what the author means would fix both cases. The compiler would enforce it, and it would only apply where it has to: outside the defining crate.

# Guide-level explanation

## Enums

```rust
#[non_exhaustive]
pub enum Error {
    NotFound,
    PermissionDenied,
    Interrupted,
}
```

In the crate that defines `Error`, nothing changes. Matches there can be exhaustive and the compiler checks them.

Any other crate that matches on `Error` must include a wildcard:

```rust
match err {
    Error::NotFound => ...,
    Error::PermissionDenied => ...,
    _ => ...,
}
```

Without the `_` arm the compiler reports an error saying the enum is non-exhaustive and a wildcard is required. Adding `Error::TimedOut` later is therefore not a breaking change, since every downstream match already handles unknown variants.

## Structs

```rust
#[non_exhaustive]
pub struct Config {
    pub verbose: bool,
    pub threads: usize,
}
```

Inside the defining crate, `Config` works as before. Outside it:

- `Config { verbose: true, threads: 4 }` is an error. The library has to provide a constructor or a `Default` impl.
- Functional record update (`Config { verbose: true, ..Default::default() }`) is also an error, since it amounts to construction.
- A pattern must use `..`: `let Config { verbose, .. } = c;` compiles, `let Config { verbose, threads } = c;` does not.
- Field access with `c.verbose` works as usual.

For tuple structs and unit structs, the attribute lowers the visibility of the constructor to `pub(crate)`, so downstream code can't call `Foo(1, 2)` or name the unit value `Foo`.

## Enum variants

The attribute can also go on a single variant:

```rust
pub enum Message {
    #[non_exhaustive]
    Data { id: u32, payload: Vec<u8> },
    Quit,
}
```

Downstream code can't build `Message::Data { .. }` with a literal and must use `..` when matching on its fields. The enum as a whole stays exhaustive, so a match on `Message` without a wildcard is still fine as long as it covers `Data` and `Quit`.

## When to use it

Use `#[non_exhaustive]` when you expect the type to grow and you want growth to be a minor change. Error kinds, configuration structs, and enums that mirror an external specification (protocol messages, platform-specific codes) are the typical cases.

Don't use it on types whose shape is complete by nature. `Option`, `Result`, and `Ordering` should stay exhaustive. The attribute makes downstream code handle a case that may never happen, and that cost is only worth paying when the type really will change.

# Reference-level explanation

## Exhaustiveness checking

When the compiler checks a match against a type from another crate, it treats `#[non_exhaustive]` enums as having an unknown extra variant. A match that covers every listed variant but has no wildcard or binding pattern is reported as non-exhaustive.

For `#[non_exhaustive]` structs and variants, the compiler treats the type as having an unknown extra field. Patterns without `..` are rejected.

Within the defining crate the attribute does nothing to exhaustiveness checking. The crate knows the full definition and changes it in step with its own code.

## Construction

Outside the defining crate, struct expressions for `#[non_exhaustive]` structs and variants are errors. For tuple and unit forms, the implicit constructor function or constant is given `pub(crate)` visibility, capped at the visibility of the type itself.

## Interaction with other features

- **`#[repr]` and casts.** A `#[non_exhaustive]` enum with only unit variants can still be cast to an integer with `as`. The attribute changes no layout.
- **Derives.** `#[derive(...)]` code is generated in the defining crate, so derives are unaffected.
- **Uninhabited enums.** A `#[non_exhaustive] enum Never {}` is not treated as uninhabited by other crates, because a variant might be added. Code that relies on it being empty to skip a match arm has to handle the general case.
- **Visibility.** The attribute only matters at crate boundaries. Visibility within a crate, such as between modules, is not affected.

## Lints

The compiler warns when `#[non_exhaustive]` is put on a private type, since the attribute can't do anything there. It is an error to put it on items other than structs, enums, and enum variants.

# Drawbacks

- Downstream code has to write wildcard arms that may never run. When a new variant arrives, the compiler won't point at the matches that should handle it; they fall into the wildcard without a sound. That loss of information is a real cost.
- The rules differ inside and outside the defining crate, which can surprise people when code moves between crates.
- One more attribute to learn.

# Rationale and alternatives

## Keep the hidden-variant pattern

This needs no language change, but every problem listed in the motivation remains. The attribute captures the same intent and the compiler enforces it.

## A lint instead of an error

Missing wildcards could be a warning rather than an error. That would not make adding variants a non-breaking change, because downstream code would still fail with `#![deny(warnings)]`, and many crates build that way in CI.

## A different spelling

Earlier discussion considered `#[extensible]`, `#[open]`, and a keyword. `non_exhaustive` describes the effect in the vocabulary the compiler already uses in its error messages, and an attribute leaves the grammar alone.

## Differences from RFC 757

RFC 757 proposed the attribute for enums only. This RFC adds structs and individual enum variants, defines how tuple and unit constructors behave, and specifies the uninhabited-enum case.

# Unresolved questions

- Should there be an opt-in lint that warns downstream users when a wildcard arm catches a variant that is now known, so they can update their matches when they upgrade the dependency?
- Should the standard library move `std::io::ErrorKind` and similar types to the attribute? That would itself be a minor change, but it is left to separate decisions.

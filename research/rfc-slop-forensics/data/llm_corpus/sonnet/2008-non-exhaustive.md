# RFC 2008: non_exhaustive

- Feature Name: `non_exhaustive`
- Start Date: 2017-05-24
- RFC PR: rust-lang/rfcs#2008
- Rust Issue: rust-lang/rust#44109

## Summary

This RFC introduces the `#[non_exhaustive]` attribute for enums and structs, which indicates that more variants or fields may be added in the future. Applying the attribute to an enum forces downstream crates to include a wildcard arm in any `match` on that enum, so that adding a new variant is not a breaking change. Applying it to a struct or an enum variant prevents downstream crates from constructing the type with a struct expression or matching it exhaustively, so that adding a new field is not a breaking change.

This is a post-1.0 version of RFC 757, with some additions.

## Motivation

Rust's strict exhaustiveness checking is one of its best features, but it interacts badly with API evolution. Under the current rules, adding a variant to a public enum is a breaking change, because any downstream `match` that lists every variant stops compiling. Adding a public field to a struct is also breaking, because downstream code may construct the struct with a literal or match on it without `..`.

Library authors currently work around this in a few ways, none of them good:

1. **A hidden variant.** The author adds `#[doc(hidden)] __Nonexhaustive` to the enum. Downstream users are forced to write a wildcard arm, but the variant is visible in the type, shows up in generated code, and must be handled by the author's own code too. It is a convention, not something the compiler understands.
2. **A private field.** The author adds a `_priv: ()` field to a struct to stop downstream construction. This works, but it also prevents the author's own crate from using struct literals conveniently, and it is not obviously intentional to a reader.
3. **Never extending the type.** The author decides the type is frozen, and either accepts that or ships a new major version for every addition.

The standard library has faced the same problem. `std::io::ErrorKind` is the clearest case: it is a public enum that must grow as new operating system error conditions are mapped. It currently carries a hidden variant for exactly this purpose.

An explicit attribute gives authors a clear, checked, self-documenting way to say "this type will grow".

## Guide-level explanation

### On enums

The `#[non_exhaustive]` attribute can be placed on an enum:

```rust
#[non_exhaustive]
pub enum Error {
    NotFound,
    PermissionDenied,
    Timeout,
}
```

Within the crate that defines `Error`, nothing changes. Matches are checked for exhaustiveness as usual, so the author is still told when a new variant is not handled.

In other crates, a `match` on an `Error` must contain a wildcard arm:

```rust
match error {
    Error::NotFound => { /* ... */ }
    Error::PermissionDenied => { /* ... */ }
    _ => { /* handles Timeout and anything added later */ }
}
```

A match that lists all three variants but has no wildcard is rejected downstream, because the compiler cannot know that three variants are all there will ever be.

### On structs

The attribute can also be placed on a struct:

```rust
#[non_exhaustive]
pub struct Config {
    pub timeout: u32,
    pub retries: u32,
}
```

Inside the defining crate, `Config { timeout: 1, retries: 2 }` works as before. In other crates it does not:

```rust
// error: cannot create non-exhaustive struct using struct expression
let c = Config { timeout: 1, retries: 2 };
```

Downstream crates also cannot use functional record update syntax to build a value, because that would likewise need to name every field. Patterns must end with `..`:

```rust
let Config { timeout, .. } = config;
```

The author is expected to provide a constructor or a builder, for example `Config::new()`. Fields that exist today can still be read and, if public, assigned.

### On enum variants

The attribute may also be placed on an individual variant:

```rust
pub enum Shape {
    #[non_exhaustive]
    Circle { radius: f64 },
    Square { side: f64 },
}
```

Here the variant `Circle` may gain fields in the future. Downstream crates cannot construct `Shape::Circle { .. }` directly and must match it with `..`. The enum itself is still exhaustive, so a downstream match need not have a wildcard arm.

### Tuple and unit structs

For tuple structs and tuple variants, the attribute has the same effect: they cannot be constructed using the tuple constructor outside the defining crate, and patterns must end with `..`. A unit struct marked `#[non_exhaustive]` cannot be constructed by name outside the crate either, which leaves room to turn it into a struct with fields later.

## Reference-level explanation

### Syntax and placement

`#[non_exhaustive]` is a built-in attribute that is valid on `enum` definitions, `struct` definitions, and enum variants. It is an error to use it elsewhere, for example on a function or a trait. It takes no arguments.

### Semantics

Let `T` be a type or variant marked `#[non_exhaustive]`, and let *local* mean "in the crate that defines `T`".

**Enums.** When type-checking a `match` expression outside the local crate whose scrutinee has type `T`, the exhaustiveness checker treats the set of variants as open. A match is exhaustive only if it contains an irrefutable arm such as `_` or a binding, covering whatever variants are unknown. Matches inside the local crate are checked against the known variants only.

**Structs and variants.** Outside the local crate:

- A struct expression naming `T`, including one using `..base`, is an error.
- A tuple-struct or tuple-variant constructor call for `T` is an error.
- A pattern for `T` must include `..`.

Inside the local crate, none of these restrictions apply.

### Interaction with privacy

The restrictions are independent of field visibility. A struct with all public fields and `#[non_exhaustive]` still cannot be constructed downstream. Private fields continue to behave as before.

### Interaction with `#[derive]` and generated code

Derived implementations such as `Clone`, `Debug` and `PartialEq` are expanded in the defining crate, so they see the full definition and are unaffected. Macros expanded in a downstream crate that attempt to construct a non-exhaustive type will fail like any other downstream code.

### Interaction with `repr`

`#[non_exhaustive]` does not change layout. Combining it with `#[repr(C)]` or `#[repr(u8)]` is allowed; the attribute only concerns what downstream crates may write, not representation. Authors using FFI should remember that adding a field or variant still changes the ABI, even if it no longer breaks source compatibility.

### Reflection and documentation

`rustdoc` should display the attribute on the type, so that readers know a wildcard arm or a constructor function is required.

## Drawbacks

- **Weaker checking downstream.** Users lose the compiler's help when a variant is added. A downstream match with a wildcard will silently take the new case. This is the point of the feature, but it is a real cost, and authors should only apply the attribute where growth is genuinely expected.
- **More attributes to learn.** Authors must understand three related behaviours under one name.
- **Awkward for tests and examples.** Downstream code, including documentation tests in the same repository, behaves as an external crate, so such tests must use constructors.
- **Pressure to overuse.** Authors may apply the attribute defensively to every public type, producing clumsy APIs. Guidance in the API guidelines should discourage this.

## Rationale and alternatives

### Why an attribute rather than a keyword

Adding syntax such as `pub enum Foo { ..., .. }` would need a language change visible in every parser and tool. An attribute is lightweight, easy to ignore for tools that do not care, and consistent with `#[must_use]` and similar annotations.

### Why crate-level granularity

The restrictions apply at the crate boundary because that is the unit at which semantic versioning is applied. Within a crate, the author controls all the code and can update it together with the type.

### Alternative: do nothing

The hidden variant and private field conventions work today. But they are not understood by the compiler, cannot be checked, produce confusing documentation, and force the author's own code to handle phantom cases. A standard mechanism removes these costs.

### Alternative: `#[non_exhaustive]` on enums only

Enums are the most pressing case, but the same reasoning applies to structs, and a partial feature would leave authors using the private field hack for structs. Handling both together is little extra work.

### Alternative: lint instead of error

A warn-by-default lint could allow exhaustive matches but warn about them. This would not protect the author's compatibility promise, since downstream code that compiles with warnings would still break on upgrade.

## Prior art

RFC 757 proposed a similar feature before Rust 1.0 and was postponed. Other languages offer related tools. Scala sealed hierarchies express the opposite default: exhaustive unless opened. Java's `enum` types have no such protection, and the common advice is to always include a `default` branch for enums from libraries. Swift provides `@unknown default` on enums marked as possibly gaining cases, which pairs a wildcard with a warning when a known case is missing; this is a plausible future extension for Rust.

## Unresolved questions

- Should a lint be offered for wildcard arms that could be replaced with explicit variants, in the spirit of Swift's `@unknown default`?
- Should the attribute be permitted on `union` definitions?
- Should the same restrictions apply to crates in the same workspace? The current proposal says no; only the defining crate is exempt.
- What guidance should the API guidelines give on when to apply the attribute to types in the standard library?

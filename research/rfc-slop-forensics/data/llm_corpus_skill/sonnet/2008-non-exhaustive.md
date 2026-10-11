# RFC 2008: non_exhaustive

## Summary

This RFC adds the `#[non_exhaustive]` attribute for enums and structs. The attribute states that more variants or fields may be added to the type in the future.

Placed on an enum, the attribute forces downstream crates to include a wildcard arm in `match` statements. Adding a variant then does not break those crates.

Placed on a struct or an enum variant, the attribute prevents downstream crates from constructing the value with a struct expression and from matching it exhaustively. Adding a field then does not break those crates.

This is a post-1.0 version of RFC 757, with some additions. [TODO: list the additions. The material says "some additions" and does not name them.]

## Motivation

A library author who publishes a public enum makes a promise to every user. Users may write a `match` over the enum and list all its variants without a wildcard arm. If the author later adds a variant, every such `match` stops compiling in the user's crate, because the match no longer covers all cases. The same holds for a public struct whose fields are all public: users can build it with a struct expression naming every field, and adding a field breaks each such expression.

Example:

```rust
// in crate `shapes`, version 1.0
pub enum Shape {
    Circle(f64),
    Square(f64),
}

// in a downstream crate
match shape {
    Shape::Circle(r) => area_circle(r),
    Shape::Square(s) => area_square(s),
}
```

If `shapes` 1.1 adds `Shape::Triangle`, the downstream `match` is no longer exhaustive and the downstream crate fails to build. Under the versioning rules of Cargo, a minor version bump is expected to be compatible. [TODO: the author to confirm what the Rust project's compatibility policy says about adding a variant, and cite the document. This RFC cannot state the policy from memory.]

Library authors can work around the problem today. [TODO: describe the workaround or workarounds in use, as the author knows them. A commonly mentioned approach is to add a hidden variant or a private field. The author must confirm which workarounds exist and what they cost, for example in documentation noise or in API surface.] The RFC proposes a language feature so that the intent is stated once, in the declaration, and the compiler enforces it.

The post-1.0 qualifier in the Summary matters. Before 1.0 the language could make breaking changes freely. After 1.0, compatibility is a constraint, and the earlier RFC 757 has to be revisited under that constraint. [TODO: say what RFC 757 proposed and why it was not adopted, from that RFC's text.]

## Guide-level explanation

### On an enum

Mark the enum:

```rust
#[non_exhaustive]
pub enum Shape {
    Circle(f64),
    Square(f64),
}
```

Code in the defining crate treats the enum as before. Code in other crates must add a wildcard arm to any `match` on a `Shape`:

```rust
match shape {
    Shape::Circle(r) => area_circle(r),
    Shape::Square(s) => area_square(s),
    _ => unreachable_for_now(),
}
```

Because the wildcard covers any future variant, version 1.1 can add `Triangle` without breaking this code.

### On a struct

```rust
#[non_exhaustive]
pub struct Config {
    pub verbose: bool,
}
```

Downstream crates cannot write `Config { verbose: true }`, because that expression names all the fields and would break when a field is added. They also cannot match it as `Config { verbose }` without `..`. [TODO: author to specify how a downstream crate then constructs a `Config`. The usual answer is a constructor function or a builder supplied by the library, but the material does not say, and the RFC should state the expected pattern.]

### On an enum variant

The attribute can be placed on a single variant. In that case the variant's fields behave as described for structs, and new fields can be added to that variant without a break.

## Reference-level explanation

### Scope of the restrictions

The restrictions apply to code outside the crate that defines the type. Inside the defining crate the attribute has no effect. [TODO: state whether "crate" is the right boundary or whether the module system should be used instead, and give the reason.]

### Exhaustiveness checking

For an enum with the attribute, the compiler's exhaustiveness check in a downstream crate treats the enum as if it had an extra unnamed variant. A wildcard arm, or a binding arm, matches it. [TODO: specify the interaction with `if let` and `while let`, which do not require exhaustiveness, and with matches that cover all current variants and also contain a wildcard; say whether the latter produces a warning for "unreachable pattern".]

### Construction

For a struct with the attribute, struct expressions and struct patterns from other crates are rejected unless the pattern ends with `..`. Tuple-struct construction through a public constructor is also affected. [TODO: author to settle the case of tuple structs and unit structs, where there is no field list to extend in the same way. State whether the attribute is permitted on them and what it does.]

### Interaction with other features

[TODO: list the interactions with `#[derive]`, with `repr` attributes on enums, and with pattern matching on references. The material is silent on each.]

## Drawbacks

1. Downstream users lose the ability to be told by the compiler that they have handled every variant. With the attribute, a new variant produces no error where the user has a wildcard arm, and the user may not notice that it needs special handling. This is the direct cost of the feature. The RFC should say that it accepts this cost for types whose authors have asked for the attribute.
2. The attribute adds a new concept for readers of the language. [TODO: the author's view of how large this cost is.]
3. An author who forgets the attribute at 1.0 cannot add it later without breaking downstream crates, because adding it removes existing abilities (matching without a wildcard, constructing by struct expression). The attribute is therefore a decision to make at design time. [TODO: confirm; the material does not state this.]

## Rationale and alternatives

The material does not record the alternatives that the author considered. The following are suggestions for the author to evaluate, not rejected options.

- A lint that warns library authors when they add a variant to a public enum. This catches the problem late, after the change, and does not help the downstream crate.
- A convention using a hidden variant or a private field. This works now and needs no language change, at the cost of documentation clutter. [TODO: author to confirm the cost and give examples.]
- Making all public enums non-exhaustive by default and adding an attribute to opt out. This is a larger change for existing code and is a second-order question that the RFC may want to rule out explicitly.

[TODO: for each alternative the author actually considered, give the goal that made it lose.]

The attribute is hard to reverse once stabilized: it is part of the public contract of every crate that uses it. This argues for a conservative first stabilization. [TODO: author to state the intended scope of the first release, and whether any parts remain behind a feature gate.]

## Unresolved questions

- The list of additions over RFC 757.
- The treatment of tuple and unit structs.
- The interaction with `if let`, `while let` and unreachable-pattern warnings.
- Whether the crate boundary is the right place for the restriction.
- The spelling of the attribute.

## Migration

For a library author, adding the attribute to an existing type is a breaking change for downstream crates. [TODO: author to confirm.] For a downstream crate, the change after a library adds the attribute is to insert a wildcard arm or a `..`. [TODO: say whether the compiler's diagnostics will suggest this edit.]

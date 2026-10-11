# RFC 1105: API evolution and semver

- Start Date: 2015-04-04
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

## Summary

This RFC proposes a comprehensive set of guidelines for which changes to *stable* APIs are considered breaking from a semver perspective, and which are not. The guidelines are intended for both the standard library and the crates.io ecosystem.

This does *not* mean that the standard library should be completely free to make every change that is not semver-breaking. There are sometimes still risks of ecosystem pain that need to be taken into account. Rather, this RFC makes explicit an initial set of changes that absolutely *cannot* be made without a semver bump. Along the way, it also discusses some interactions with potential language features that can help mitigate pain for non-breaking changes.

The RFC covers only API issues. Other issues related to language features, lints, type inference, command line arguments, Cargo, and so on are out of scope and may be addressed separately.

## Motivation

Rust 1.0 is a promise: code that compiles today will continue to compile with every later 1.x release. Keeping that promise requires that library authors, and the standard library team in particular, know precisely what they may change. Today that knowledge is informal. Authors rely on intuition, and intuition fails in the corners: adding a trait implementation, adding a field to a struct, or adding a method to a trait can each break downstream code in ways that are not obvious.

Cargo and crates.io make the problem broader than the standard library. The ecosystem leans on semantic versioning, in which a patch release is expected to be a drop-in replacement and a minor release is expected to be backward compatible. Without a shared definition of "compatible", the version numbers in a `Cargo.toml` carry less information than they should.

This RFC therefore lays out an explicit catalog. It is conservative by design: when it is unclear whether a change is breaking, the guidance leans toward calling it breaking.

## Detailed design

### Definitions

A change is **major** (breaking) if it can cause code that compiled against the previous version to fail to compile, or to change behavior in a way that violates the documented contract, with no change to that code. A change is **minor** if it is permitted in a minor version bump. Some minor changes still carry a *risk* of breakage; these are discussed separately.

For the purposes of this RFC, an API is *stable* when it is exposed from a crate, is documented as public, and is not marked unstable or hidden.

### Principles

1. Anything that can reasonably be used by downstream code without `unsafe` and without relying on an undocumented detail is part of the contract.
2. A change is breaking if, for some valid downstream program, it turns a compiling program into a non-compiling one.
3. Type inference and method resolution are sensitive to additions. Many "additive" changes are therefore potentially breaking, and we treat some of them as acceptable only because their breakage is rare, localized, and easily fixed.

### Major changes

The following changes require a major version bump.

**Removing or renaming items.** Removing a public function, type, trait, module, constant, or re-export, or renaming any of them, breaks every user of the old path.

**Changing a function signature.** Adding, removing, or reordering parameters; changing the type of a parameter or return value; adding a type parameter without a default; or tightening a bound on an existing type parameter. Loosening a bound is generally minor. Adding a defaulted type parameter is mostly minor but can interfere with inference and with explicit use of the type in some positions.

**Adding a required trait item.** Adding a method to a trait without a default body breaks every implementor. Adding an associated type or constant without a default is breaking for the same reason.

**Changing trait items in an incompatible way.** Modifying the signature of an existing trait method, adding a supertrait, or tightening the bounds on a method.

**Removing a trait implementation.** If `T: Trait` held and no longer does, code that relied on it will fail.

**Changing the variants of a public enum.** Adding a variant breaks exhaustive `match` expressions in downstream code. Removing or renaming a variant breaks all uses. Authors who expect to grow an enum should document that fact up front, and the language may eventually offer an attribute for marking enums as extensible.

**Changing struct fields.** Adding a public field breaks code that constructs the struct with literal syntax and code that destructures it exhaustively. Removing a public field or changing its type breaks field access. Changing a private field to public is minor, but changing the set of public fields on a struct with only public fields is breaking.

**Changing the representation or layout** of a type for which the layout was documented, for example `#[repr(C)]` types.

**Changing the kind of a struct**, such as from a struct with named fields to a tuple struct, or from a unit struct to anything else.

**Tightening visibility.** Making a public item private, or restricting its reach, breaks existing users.

**Changing auto-trait implementations** in ways that remove them. If a type was `Send` and is no longer, downstream code that moved it across threads will fail. Because auto traits leak through private fields, authors must take care that adding a field of a non-`Send` type is itself a breaking change.

**Changing the behavior of a documented API in ways that violate the documentation.** The documented contract is part of the API. Fixing a bug so the code matches its documentation is permitted; changing the documented contract is not.

### Minor changes

The following changes are permitted in a minor release.

**Adding new items.** New functions, types, traits, modules, and constants can be added. New items have a small risk of colliding with glob imports in downstream code, which is why downstream authors are encouraged to avoid globbing across crate boundaries other than for preludes.

**Adding a trait method with a default body.** This is compatible for implementors. It does have a risk of introducing ambiguity when a downstream trait also defines a method of the same name and both are in scope for a type that implements both.

**Loosening bounds on a function or type**, or removing a parameter's bound.

**Making a private field public** or relaxing visibility.

**Adding a trait implementation.** This one needs particular care, because implementations can alter type inference. Adding a *blanket* implementation, one that applies to all types or all types meeting a bound, is always breaking, since it can overlap with implementations a downstream crate has already written. Adding a non-blanket implementation for a type the crate owns is generally minor, with the caveat that code which previously inferred a unique implementation may now see ambiguity. This second risk is considered acceptable.

**Introducing defaulted type parameters** where doing so cannot change inference of existing code.

**Changing the internal implementation** while preserving the documented contract, including performance characteristics unless explicitly promised.

### Changes with a risk of breakage

Some changes are minor by the definition above but carry a nonzero risk. Library authors should weigh these. Examples include:

- Adding an inherent method to a type. Inherent methods take priority over trait methods in resolution, so a new inherent method can silently change which method a call resolves to.
- Adding a trait implementation that affects inference, as discussed above.
- Adding a variant to an enum documented as non-exhaustive, which is safe only if the documentation was visible to consumers.
- Changing a function from accepting a concrete type to a generic `T: Into<Concrete>`, which can defeat inference at call sites that previously relied on the single concrete type.

The standard library team will treat such changes with additional caution, since the standard library is used everywhere. In practice this means assessing the breakage using crater-style experiments over crates.io before landing.

### Language features that help

Several language-level mechanisms could reduce the cost of evolving APIs. These are discussed for context only and are not proposed here.

- A way to mark an enum or struct as extensible, so downstream code is forced to include a wildcard arm or the `..` pattern.
- Support for sealed traits, so that library authors can promise no external implementors exist and therefore add required methods freely.
- Better resolution rules for ambiguous trait methods, so that adding a default method is less likely to create conflicts.

### Application to the standard library and crates.io

For the standard library, these rules define the floor. Changes classified as major are not permitted before Rust 2.0. Changes with a risk of breakage require review and experimentation.

For crates.io, the rules provide a shared reference for the meaning of version numbers. Cargo's resolver already assumes that compatible versions are interchangeable; this document says what that means in practice. Crate authors are encouraged to link to it from their own documentation.

## Drawbacks

The catalog is long, and the length itself may deter authors from reading it. It is also incomplete: new language features will create new categories of breaking change, and the document will need to grow.

Treating a larger set of changes as breaking restricts library evolution. Some well-intentioned improvements will have to wait for a major release.

## Alternatives

We could decline to specify anything and rely on case-by-case judgment. This preserves flexibility and costs nothing up front, but it makes the stability promise hard to evaluate and leads to inconsistent practice across crates.

We could instead adopt a stricter policy in which any change to the public surface, including additions, requires a major bump. This is simple but impractical; it would make nearly every release breaking.

We could also try to automate the classification by tooling that diffs the public interface of two crate versions and reports breaking changes. This is a promising complement and not a replacement, since someone must first decide what counts as breaking.

## Unresolved questions

- How should the guidelines treat changes to lints and warnings, which may break builds under `#![deny(warnings)]`?
- What counts as the "documented contract" for behaviors only specified implicitly?
- Should a formal mechanism exist to mark an API as "may gain implementations" or "may gain variants"?
- How should unsafe code that relies on layout or on undocumented behavior be handled?

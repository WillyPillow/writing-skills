- Feature Name: not applicable
- Start Date: 2015-05-04
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

This RFC sets out guidelines for deciding which changes to *stable* APIs are breaking in the semver sense and which are not. The guidelines apply to the standard library and to crates published on crates.io.

They do not give the standard library license to make every change that is technically non-breaking. Some technically allowed changes still cause enough pain across the ecosystem that they deserve care. What this RFC does is pin down an initial set of changes that *cannot* be made without a major version bump. Along the way it discusses some language features that could make non-breaking changes less painful.

Only API surface is covered. Changes to language features, lints, type inference, command-line arguments, Cargo, and so on are out of scope.

# Motivation

With Rust 1.0 the standard library made a stability promise: code that compiles on 1.x should keep compiling on 1.y for y > x. Crates on crates.io make a similar promise through semantic versioning, and Cargo picks versions on that assumption. A `^1.2.0` dependency will happily resolve to `1.9.3`.

Both promises depend on a shared understanding of what counts as "breaking." Rust makes that understanding harder to reach than it is in many languages. Trait coherence, type inference, glob imports, and method resolution all let changes that look additive break downstream code. For example:

- Adding a method to a type can break a downstream crate that calls a trait method of the same name on that type.
- Adding a trait implementation can make a previously unambiguous type inference ambiguous.
- Adding a public item to a module can collide with a downstream glob import.

If nearly any change can break *some* code, then strict "no breakage" rules would freeze libraries in place. We need a principled line that separates *major* changes, which require a major version bump, from *minor* changes, which are allowed in a minor release even though they can, in rare cases, require small downstream fixes.

# Detailed design

## Principles

The guidelines rest on three principles.

1. **Major changes need a major version bump.** A change is major if it can break a reasonable downstream client in a way that cannot be fixed locally and mechanically.
2. **Minor changes may cause minor breakage.** A change is minor if any breakage it causes can be fixed by local, mechanical edits to the downstream code, such as adding a type annotation or disambiguating a method call with UFCS, and if such breakage is expected to be rare.
3. **Clients can protect themselves.** Downstream code can be written defensively so that minor changes never break it, for example by avoiding glob imports of external crates or by using fully qualified paths. Code written that way is guaranteed to keep compiling.

The point of separating "major" from "minor but possibly breaking" is to let libraries keep evolving. The rest of the RFC catalogs specific changes under these principles.

## Major changes

The following changes are **major** and require a major version bump.

### Items

- **Renaming, moving, or removing any public item.** Code that names the item will no longer compile.
- **Narrowing visibility,** for example changing `pub fn` to a private function.

### Structs and enums

- **Adding a private field to a struct whose fields are currently all public.** Downstream code that constructs the struct with a literal or destructures it fully will break.
- **Adding a public field to a struct whose fields are all public.** Struct literals and exhaustive patterns break for the same reason.
- **Adding a variant to an enum.** Exhaustive `match` expressions downstream stop compiling. (Making this minor would require a language feature for declaring an enum non-exhaustive; see "Interactions with language features" below.)
- **Adding a field to an enum variant.**

### Traits

- **Adding a non-defaulted item to a trait.** Every downstream implementor breaks.
- **Changing a trait item's signature in almost any way.** Implementors and callers can both break.
- **Implementing a fundamental trait.** Adding an impl of a `#[fundamental]` trait, or for a `#[fundamental]` type, can change what downstream crates may implement under the coherence rules.

### Trait implementations

- **Removing an impl** of a trait for a public type.
- **Adding a blanket impl** such as `impl<T: Foo> Bar for T`. A downstream crate may already implement `Bar` for a type that also implements `Foo`, and the two impls would then overlap.

### Functions and signatures

- **Adding or removing arguments.**
- **Tightening generic bounds,** for example going from `fn f<T>(t: T)` to `fn f<T: Clone>(t: T)`.
- **Changing argument or return types,** except in the limited generalizing cases listed below.

## Minor changes

The following changes are **minor**. They may break some code in rare cases, but only in ways that can be fixed locally.

### Adding items

- **Adding a new public item to a module.** This can break downstream glob imports through name collisions. Glob imports of other crates are considered fragile, and clients who want full stability should avoid them.

### Inherent and trait methods

- **Adding an inherent method.** If a downstream crate calls a trait method of the same name with method syntax, the inherent method will shadow it. The fix is to use UFCS (`Trait::method(&x)`).
- **Adding a defaulted item to a trait.** This can cause method-name ambiguity downstream when two traits in scope share the name. The fix is again explicit disambiguation.

### Trait implementations

- **Adding a non-blanket impl** of an existing trait for a local type. This can make type inference ambiguous downstream, which is fixed by adding an annotation.

### Structs

- **Adding a private field when at least one private field already exists.** Downstream code cannot build the struct with a literal or match all of its fields anyway, so nothing observable changes.
- **Turning a tuple struct with all private fields into a named-field struct,** or the reverse.

### Signatures

- **Loosening generic bounds.** `fn f<T: Clone>(t: T)` becoming `fn f<T>(t: T)` cannot break callers.
- **Introducing a new type parameter with a default,** for example `struct Foo<T>` becoming `struct Foo<T, A = Global>`. This is minor *only* for types; for functions it can break callers that use turbofish.
- **Generalizing an argument to a generic type that the old type satisfies,** for example `fn f(x: &str)` becoming `fn f<T: AsRef<str>>(x: T)`. Inference can break in rare cases, which an annotation fixes.

## Behavioral changes

The rules above cover only what the type checker sees. A change in documented behavior, such as different results, new panics, or changed complexity guarantees, may also be breaking. This RFC does not try to codify behavioral changes. Library authors should use judgment and treat any change to a documented contract as major.

# Interactions with language features

Several possible language features would turn major changes into minor ones:

- **Non-exhaustive enums and structs.** An attribute marking a type as open to extension would require downstream `match` expressions to include a wildcard arm. Adding variants or fields would then be minor.
- **Sealed traits.** If a trait could be declared unimplementable outside its crate, adding non-defaulted items to it would be minor. Today this can be approximated with a private supertrait.
- **Name resolution priority for imports.** If explicit imports always took priority over glob imports and globs never conflicted with each other in an error-producing way, adding public items would almost never break anything.

These are not proposed here, but future RFCs that propose them should cite this document.

# Drawbacks

Some changes classified as minor will break real code. Rust's flexible inference and method resolution make this unavoidable unless we forbid most library evolution. The cost is mitigated by requiring every such break to have a mechanical fix and by promising tooling support where we can, such as running crater against the ecosystem before a standard library release.

The guidelines are also detailed, and library authors may not take them all in. A short, linkable reference in the API guidelines should help.

# Alternatives

**Treat every possible breakage as major.** That would be the strictest reading of semver, but almost any change could break someone, so library authors would be bumping major versions all the time and the signal would mean nothing.

**Leave it to each crate.** Without shared rules, Cargo's resolution would rest on assumptions that individual crates might not honor.

# Unresolved questions

- Should Cargo or a separate tool check these rules automatically when publishing?
- How should changes involving `unsafe` contracts and memory layout be classified?
- Should there be a formal notion of "breakage budget" for the standard library, measured by crater runs?

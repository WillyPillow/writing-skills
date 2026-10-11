# Rust RFC 1733: Trait aliases

- Feature Name: `trait_alias`
- Start Date: 2017-02-28
- RFC PR: rust-lang/rfcs#1733
- Rust Issue: rust-lang/rust#41517

## Summary

This RFC introduces trait aliases. A trait alias gives a name to a set of trait bounds, so that a long combination of traits can be written once and referred to by a short name. The syntax is `trait TraitAlias = ...;`, and the right-hand side is a bound: a single trait, a combination of traits joined with `+`, and lifetimes. Type parameters and lifetime parameters may be declared on the alias when they are needed.

## Motivation

Generic code often requires several traits at once. A function that must be cloneable, debuggable, sendable across threads, and comparable will repeat that list at every use site. The repetition is tedious to write and easy to get wrong, since a change to the required set must be made in every place where the list appears.

Programmers currently work around this with blanket implementations. A trait is defined with no methods and implemented for every type that satisfies the desired bounds. The pattern works, but it is indirect. The new trait appears in the documentation as a real trait, its implementations are generated invisibly, and error messages refer to it in ways that confuse readers who expect to see the underlying bounds.

Trait aliases make the intent direct. The alias is not a new trait with its own implementations. It is a shorthand for the bounds it expands to, and the compiler treats a use of the alias as if each of its bounds had been written in place.

## Guide-level explanation

A trait alias is declared with the keyword `trait`, a name, an equals sign, and a list of bounds ending in a semicolon:

```rust
trait Network = Send + Sync + Clone + 'static;
```

The alias can then be used anywhere a bound is expected:

```rust
fn serve<T: Network>(service: T) { /* ... */ }
```

The function is checked as if it had been written with the four bounds directly. The alias may also take type parameters, so that a family of bounds can be named with one declaration. Lifetimes can be included in the same way.

An alias is a convenience, not a new type or a new trait. It cannot be implemented directly, and it does not appear as a separate item in trait objects. A trait object type can use the alias only in the forms that the underlying bounds allow.

## Reference-level explanation

A trait alias definition has the form `trait Name<Params> = Bounds;`, where `Params` is an optional list of type and lifetime parameters, and `Bounds` is a non-empty list of trait references and lifetime bounds separated by `+`. The definition introduces `Name` into the item namespace, in the same way as a trait definition.

When an alias appears in a bound position, the compiler replaces it with its right-hand side, substituting the supplied arguments for the alias parameters. The substitution is performed before any trait checking, so that the expanded bounds are checked exactly as they would be if they had been written directly.

Trait aliases are not implementable. An attempt to write an impl block for an alias is an error, since the alias has no items of its own.

An alias may refer to other aliases, and cycles are rejected. The compiler detects cycles during expansion and reports an error at the definition that closes the cycle.

Associated type bindings may be included in an alias, so that an alias can express a bound such as an iterator whose item has a particular type. The binding is expanded in the same way as the other bounds.

The use of a trait alias in a trait object position is permitted only when the expanded bounds allow a trait object. The compiler applies the same object safety rules to the expanded bounds that it would apply to written bounds.

## Drawbacks

Trait aliases add a new kind of item, which increases the size of the language. Some readers may find that a combination of bounds written directly is already clear enough, and they may see the alias as an unnecessary indirection.

The alias can also hide the bounds from a reader who does not know its definition. Documentation tools must show the expansion to avoid this problem.

Finally, the feature overlaps with blanket implementations, and some programmers may prefer to continue using them.

## Rationale and alternatives

The main alternative is the blanket implementation pattern described in the motivation. It works without any new language feature, but it creates a real trait with invisible implementations, and it confuses error messages and documentation.

A second alternative is a macro that expands to the list of bounds. This is simple, but macros are opaque to tooling, they do not participate in type checking as cleanly as a language feature, and they produce error messages that refer to the expanded code.

Trait aliases were chosen because they express the intent directly, they are checked as ordinary bounds, and they require no hidden implementations.

## Prior art

Several languages allow a set of constraints to be named and reused. The approach in those languages is to treat the name as an abbreviation for its constraints, and the RFC follows the same model. The design is closest to the constraint aliases found in other languages with generic systems, and the experience there shows that the abbreviation model is easy to learn.

## Unresolved questions

The interaction of trait aliases with where clauses on associated types is not settled. The RFC proposes that the same expansion rule apply, but the details need confirmation during implementation.

The question of whether an alias may be exported from a crate and used by downstream code in the same way as a trait is also open, and it may depend on how the crate's public interface is documented.

## Future possibilities

If trait aliases prove useful, tooling could show the expansion of an alias in editors and documentation, so that readers can see the underlying bounds without leaving the code. The feature could also be extended to allow aliases to carry default type parameters, which would make common patterns easier to express.

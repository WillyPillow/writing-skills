- Feature Name: `associated_type_defaults`
- Start Date: 2018-08-27
- RFC PR: [rust-lang/rfcs#2532](https://github.com/rust-lang/rfcs/pull/2532)
- Rust Issue: [rust-lang/rust#29661](https://github.com/rust-lang/rust/issues/29661)

# Summary

Settle the design of associated type defaults, first introduced in RFC 192, so that provided methods and other items in a trait may **not** assume the values of type defaults. The same rule applies to `default` items under specialization. Finally, `dyn Trait` will use provided defaults and allow them to be left out of the type.

# Motivation

Associated type defaults let a trait author supply a type that implementations get unless they choose otherwise:

```rust
trait Container {
    type Iter<'a>: Iterator = std::slice::Iter<'a, u8>;
    // ...
}
```

The feature has been available on nightly behind `#![feature(associated_type_defaults)]` since 2015, but it has never been stabilized. The main obstacle is that the existing implementation and RFC 192 leave a key question unanswered: inside the trait, may other items rely on the default being the actual type?

Consider:

```rust
trait Foo {
    type Bar = u8;

    fn make() -> Self::Bar {
        42u8
    }
}
```

If `make` is allowed to treat `Self::Bar` as `u8`, then an impl that overrides `Bar` silently breaks `make`:

```rust
impl Foo for () {
    type Bar = String;
}

// <() as Foo>::make() would now return a u8 typed as String.
```

There are two consistent ways out. Either overriding a default forces the impl to also override every provided item that relied on it, or provided items are not allowed to rely on the default at all. The nightly implementation does neither cleanly, which is why it has remained unstable.

Resolving this question unblocks a feature that many library authors want. Common use cases include:

- Adding a new associated type to an existing trait without breaking every downstream impl.
- Providing a sensible default error type, such as `type Error = std::convert::Infallible;`.
- Reducing boilerplate in traits with many associated types where most implementations use the same choice.

# Guide-level explanation

You may give an associated type a default in a trait definition:

```rust
trait Parser {
    type Output = String;
    type Error = ParseError;

    fn parse(&self, input: &str) -> Result<Self::Output, Self::Error>;
}
```

An impl may override any default or accept it by leaving the type out:

```rust
struct Words;

impl Parser for Words {
    // Output is String, Error is ParseError.
    fn parse(&self, input: &str) -> Result<String, ParseError> {
        Ok(input.split_whitespace().collect())
    }
}

struct Numbers;

impl Parser for Numbers {
    type Output = i64;
    fn parse(&self, input: &str) -> Result<i64, ParseError> { /* ... */ }
}
```

Inside the trait definition, however, **default types are opaque**. Provided methods and other provided items see only the bounds declared on the associated type, never its default value. This is an error:

```rust
trait Parser {
    type Output = String;

    fn empty() -> Self::Output {
        String::new() // error: expected `Self::Output`, found `String`
    }
}
```

If you need a provided method that works with the default, put the requirement into a bound:

```rust
trait Parser {
    type Output: Default = String;

    fn empty() -> Self::Output {
        Self::Output::default() // OK
    }
}
```

This rule means overriding one default never forces you to override anything else. Every provided item is guaranteed to remain well-typed no matter which associated types an impl chooses to replace.

## Trait objects

When a trait has associated types, a trait object normally has to name all of them: `dyn Iterator<Item = u8>`. With this RFC, associated types that have defaults may be left out, and the default is used:

```rust
let p: Box<dyn Parser> = Box::new(Words);
// Equivalent to Box<dyn Parser<Output = String, Error = ParseError>>
```

This works because, for `dyn Trait`, there is no impl to override the default; the type itself is the only place the choice can be written.

# Reference-level explanation

## Type checking provided items

When type checking a provided item in a trait (a default method body, a default associated const, or another associated type's default), the compiler treats each associated type `Self::A` as an opaque projection. It assumes the where-clauses and bounds declared on `A` and nothing else. The default value of `A` is not used for normalization.

The default value itself must be well-formed and satisfy the declared bounds. For example, `type Output: Default = String;` is checked to ensure `String: Default`.

## Defaults referring to other defaults

An associated type default may mention another associated type:

```rust
trait Graph {
    type Node = u32;
    type Edge = (Self::Node, Self::Node);
}
```

Here `Self::Node` in the default for `Edge` is also opaque. An impl that overrides `Node` to `String` gets `Edge = (String, String)` unless it overrides `Edge` as well. The default for `Edge` is evaluated using the impl's actual `Node`.

Cycles among defaults, such as `type A = Self::B; type B = Self::A;`, are an error in the trait definition.

## Specialization

The same rule applies to `default` items in a specializable impl. In:

```rust
impl<T> Foo for T {
    default type Bar = u8;
    default fn make() -> Self::Bar { /* cannot assume u8 */ }
}
```

`make` cannot assume `Self::Bar == u8`, since a more specialized impl may override `Bar` without overriding `make`. Non-`default` items in the same impl also see `Bar` opaquely. This rule closes a soundness hole that has been tracked separately under specialization.

## Trait objects

For a trait object `dyn Trait<A = X>`, each associated type of `Trait` that has a default and is not bound explicitly takes its default. Associated types without defaults must still be bound. The default is substituted with `Self` erased; a default mentioning `Self` in a way that cannot be expressed for a trait object is an error at the point the trait object type is written.

## Feature gate

The behavior is gated by the existing `associated_type_defaults` feature. The current nightly behavior, where provided methods may sometimes see defaults, is removed.

# Drawbacks

- Some patterns that seem natural cannot be written. A trait author who wants `fn empty() -> Self::Output { String::new() }` must add a bound instead. In practice the bound is clearer anyway, but it is a source of initial surprise.
- The rule for `dyn Trait` adds a small special case in how trait objects are interpreted.

# Rationale and alternatives

**Allow provided items to see defaults, and require overriding together.** This would let more code type check inside the trait, but it creates hidden coupling. Changing one associated type in an impl would produce errors about methods the user never wrote. It also requires some notion of "groups" of items that must be overridden together, which RFC 192 hinted at but never designed.

**Do nothing.** The feature remains unstable indefinitely, and traits cannot add associated types without a breaking change.

# Prior art

- Haskell's associated type synonym defaults behave similarly: default instances are type checked against the class's constraints, not the default value.
- Scala's abstract type members with default bounds.

# Unresolved questions

- Whether a future extension should allow explicitly grouped defaults ("override all of these together") for cases where the opaque rule is too strict.
- Exact diagnostics when a provided method tries to rely on a default.

# Future possibilities

Once the opaque rule is in place, it becomes possible to explore item groups as an opt-in extension without changing the meaning of existing code.

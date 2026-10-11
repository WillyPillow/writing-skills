# RFC 2115: argument_lifetimes

- Feature Name: `argument_lifetimes`
- Start Date: [TODO]
- RFC PR: [TODO]
- Rust Issue: [TODO]

## Summary

This RFC removes the need to bind lifetime parameters separately in `fn` definitions and `impl` headers. It also adds a lint against leaving lifetime parameters off structs such as `Ref` or `Iter`, nudging people toward explicit lifetimes there while making them cheaper to write.

The changes are:

- A signature binds any lifetime it mentions that is not already bound.
- A style lint checks that lifetimes bound in `impl` headers are more than one character long. This reduces confusion with lifetimes bound within functions.
- `'_` can be written to elide a lifetime explicitly, and leaving off lifetime parameters entirely is deprecated.
- [TODO: the abstract mentions "some additional, less important lints" and the text is cut off. List them, or remove this line.]

## Motivation

Today a function that mentions a lifetime must first declare it in angle brackets. Consider a function that returns the longer of two string slices:

```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str { ... }
```

The `<'a>` list carries no information that the parameter list does not already carry, since every lifetime in it appears again in the types below. Under this RFC the declaration is dropped:

```rust
fn longest(x: &'a str, y: &'a str) -> &'a str { ... }
```

The same duplication occurs in `impl` headers, where a lifetime is introduced in `impl<'a>` and then used in the type being implemented. [TODO: author's example of the `impl` case, with the before and after forms.]

[TODO: the author's reasons beyond brevity. The abstract states what changes but not what problem in practice motivated it, such as learner confusion, error rates, or time spent. If the motivation is that explicit lifetimes are too costly to write, say so and give the evidence.]

The second half of the RFC concerns types that carry a lifetime but let the user omit it. A signature such as `fn f(r: Ref<i32>)` hides that `Ref` borrows from something. A reader sees no sign of the borrow in the text. The RFC wants such code to show the lifetime, either by name or as `'_`, and supplies the shorter syntax in the first half as the means of making that bearable.

This is the central tension of the proposal. Hiding a lifetime keeps signatures short and also keeps the borrow out of view. Showing it makes signatures longer and makes the borrow visible. The RFC picks visibility for type parameters of structs and offers a cheaper way to write the visible form. [TODO: the author's reasoning for this choice, and whether it was weighed against keeping the omission legal.]

## Guide-level explanation

A lifetime written in a signature is bound by that signature if no enclosing item has already bound it. This covers `fn` definitions and `impl` headers.

```rust
impl Iterator for Chunks<'a> {
    type Item = &'a [u8];
    fn next(&mut self) -> Option<&'a [u8]> { ... }
}
```

Here `'a` is introduced by the header and needs no `<'a>` after `impl`.

When a lifetime need not be named, `'_` marks it as elided on purpose:

```rust
fn parse(input: &str) -> Parsed<'_> { ... }
```

The `'_` states that `Parsed` has a lifetime parameter and that it is filled in by the usual elision rules. A programmer who writes `Parsed` with no lifetime at all gets a deprecation warning. [TODO: the lint's name and its default level.]

### The naming lint

The style lint requires lifetimes bound in an `impl` header to be at least two characters long. The reason is a shadowing hazard. If `impl` headers bind `'a` implicitly, a function inside the `impl` can bind its own `'a`, and the reader may take the two for the same lifetime. A longer name for the header's lifetime makes the two visibly different. [TODO: author to confirm this is the intended rationale. The abstract says only "to reduce potential confusion with lifetimes bound within functions".]

The lint covers a narrow case and fires on single-character names only.

## Reference-level explanation

### Binding

For an item that carries a signature, the compiler collects every lifetime name that appears in the signature. A name that is already in scope from an enclosing item refers to that binding. Any other name becomes a new parameter of the item, in order of first appearance.

[TODO: author to state the order of the generated parameters when the item also has an explicit list. Order affects explicit instantiation with turbofish syntax. State whether explicit lifetime arguments are permitted on such items.]

[TODO: author to state the rule when a name appears in both an explicit list and the signature, and whether `fn f<'a>(x: &'a u8)` stays legal. The abstract says the RFC eliminates the "need" for the list, which implies the list stays legal.]

### `'_`

`'_` in a type position elides the lifetime using the elision rules in effect for that position. [TODO: state the positions where `'_` is allowed and whether it is allowed in `impl` headers, as in `impl Trait for Foo<'_>`.]

### Deprecating omission

Omitting all lifetime arguments from a path to a type that has lifetime parameters is deprecated. The deprecation is a lint, so existing code continues to build. [TODO: the lint level, the release in which it appears, and a statement of how much existing code the lint is expected to flag. The material has no measurement, so none is given.]

## Drawbacks

The new binding rule makes the set of lifetimes in scope depend on the contents of the signature instead of on a visible list. A misspelled lifetime used to be an error because it was undeclared. Under the new rule it becomes a fresh parameter, and the error moves to wherever the two names fail to unify, which may be farther from the typo. [TODO: author's view of how serious this is and whether any mitigation exists.]

The lint against omission pushes code toward longer signatures. [TODO: the author's weighing of this cost.]

## Rationale and alternatives

[TODO: alternatives. The material does not record any alternative that was considered. Candidate questions for the author: keeping the explicit list as the only form, a sigil for implicit binding, and making the omission lint warn-by-default or allow-by-default. Each should be listed here only if it was weighed.]

## Unresolved questions

1. The exact list of the "additional, less important lints".
2. The interaction of implicit binding with explicit lifetime arguments.
3. The default level and the release plan of the omission lint.
4. Whether the two-character naming lint is warn-by-default.

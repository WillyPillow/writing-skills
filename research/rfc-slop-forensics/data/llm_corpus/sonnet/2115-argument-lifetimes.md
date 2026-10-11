# Rust RFC 2115: Argument Lifetimes

- Feature Name: `argument_lifetimes`
- Start Date: 2017-08-10
- RFC PR: rust-lang/rfcs#2115
- Rust Issue: rust-lang/rust#44524

## Summary
[summary]: #summary

Eliminate the need for separately binding lifetime parameters in `fn` definitions and `impl` headers, so that instead of writing:

```rust
fn two_args<'b>(arg1: &Foo, arg2: &'b Bar) -> &'b Baz
impl<'a> Iterator for MyIter<'a> { ... }
```

you can write:

```rust
fn two_args(arg1: &Foo, arg2: &'b Bar) -> &'b Baz
impl Iterator for MyIter<'iter> { ... }
```

Lint against leaving off lifetime parameters in structs (like `Ref` or `Iter`), instead nudging people to use explicit lifetimes in this case (but leveraging the other improvements to make it ergonomic to do so).

The changes, in summary, are:

- A signature is taken to bind any lifetimes it mentions that are not already bound.
- A style lint checks that lifetimes bound in `impl` headers are multiple characters long, to reduce potential confusion with lifetimes bound within functions. (There are some additional, less important lints proposed as well.)
- You can write `'_` to explicitly elide a lifetime, and it is deprecated to entirely leave off lifetime arguments for non-reference types.

This RFC does not introduce any breaking changes.

## Motivation
[motivation]: #motivation

Lifetimes are among the most distinctive and most difficult parts of Rust for newcomers. The explicit syntax is a significant part of the difficulty, and much of it is ceremony rather than information.

### Two kinds of noise

Consider a function that borrows from one of two arguments:

```rust
fn pick<'a, 'b>(first: &'a str, second: &'b str) -> &'b str { second }
```

The reader must parse a list of generic parameters before reaching the signature, then match each name in the list against its use. The declaration `<'a, 'b>` carries no information that the signature does not already carry: every lifetime mentioned in the signature must be declared, so the declaration is fully determined by the uses. In the example, `'a` is used once and never named again, so the programmer must invent a name only to satisfy the parser.

For `impl` blocks it is worse:

```rust
impl<'a> Iterator for MyIter<'a> {
    type Item = &'a str;
    fn next(&mut self) -> Option<&'a str> { ... }
}
```

The `'a` appears four times, but the first, in `impl<'a>`, exists only to introduce the name. Experienced Rust programmers write this boilerplate by rote, and learners find it baffling: why does `impl` need to be told about a lifetime that is right there in the type?

### Hidden lifetimes in types

Elision rules let programmers omit lifetimes in function signatures. This is a strong ergonomic feature, but it is applied unevenly. A reference `&T` can be written without a lifetime, but a struct with a lifetime parameter can also be written without one:

```rust
fn parse(input: &str) -> Ref<Foo>   // Ref has a lifetime parameter, hidden here
```

A reader cannot tell from the signature that `Ref` borrows from something. This is a common source of surprise in error messages and hides important information. For references, the `&` visibly signals a borrow; for structs, nothing does.

### The cost to learning

Newcomers frequently say lifetime syntax is one of the hardest hurdles. Reducing ceremony helps in two ways. It removes a category of syntax they need to learn before writing their first generic code, and it makes the remaining lifetime annotations stand out, since only those that carry information remain.

## Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

### In-band lifetimes

When you write a lifetime in a function signature or `impl` header, and it has not been declared, it is declared for you. These are called *in-band* lifetimes.

```rust
fn longest(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}
```

No `<'a>` is needed. The lifetime `'a` is introduced by its first appearance.

For `impl` headers:

```rust
impl Iterator for MyIter<'iter> {
    type Item = &'iter str;
    ...
}
```

Here `'iter` is introduced in the header and is in scope for the whole `impl`. By convention, lifetimes bound in an `impl` header should be longer than a single character, as with `'iter` above, so they are easy to tell apart from lifetimes bound by individual methods inside the `impl`, which are typically `'a`, `'b`. A style lint warns on single-character `impl` lifetimes.

### The anonymous lifetime `'_`

A lifetime written `'_` means "infer a fresh lifetime here." It can be used anywhere a lifetime may be elided today, and in places where elision was previously not available:

```rust
fn parse(input: &str) -> Ref<'_, Foo>
impl Iterator for MyIter<'_> { ... }
```

This marks the borrow in a type without requiring a name for it, and makes the previously implicit borrow visible. `'_` is permitted in `impl` headers as an anonymous parameter; each occurrence is a distinct lifetime.

### Lint against hidden lifetimes

A lint, `elided_lifetimes_in_paths`, warns when a path names a type with lifetime parameters but omits them. It is allow-by-default at first and recommended for opt-in. The fix is to write `'_`.

## Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

### In-band binding

During name resolution of a function signature, any lifetime name that is not in scope and is not `'static` is added to the function's generic parameter list as if it had been declared. For `impl` headers, undeclared lifetimes are added to the `impl`'s generic parameters. The lifetimes are added in order of first appearance.

If a function both declares explicit lifetime parameters and uses undeclared ones, the explicit declarations take precedence for the names they cover, and the rest are bound in-band. Mixing the styles is allowed but discouraged by style guidance.

In-band lifetimes introduced in an `impl` header are in scope in the body and in the signature of all contained items. A method's own in-band lifetimes are scoped to that method.

A lifetime used only in the body (for example, in a `let` annotation) is not bound in-band, since it is not part of a signature; the compiler reports an undeclared lifetime as it does today.

### Where bounds appear

A bound on an in-band lifetime, such as `'a: 'b`, may appear in a `where` clause. Since there is no parameter list in which to put it, the `where` clause is the only place to write such bounds.

### `'_`

The anonymous lifetime `'_` behaves like an elided lifetime reference. In function arguments, each `'_` receives a fresh lifetime. In return types, `'_` follows the existing elision rules. In `impl` headers, each `'_` introduces a fresh unnamed parameter, which can never be referred to.

### Lints

- `single_use_lifetimes`: warns when a named lifetime is used only once and could be replaced with `'_`.
- `elided_lifetimes_in_paths`: described above.
- A style lint on single-character `impl` header lifetimes.

## Drawbacks
[drawbacks]: #drawbacks

- Typos become errors that are silently accepted. Writing `'a` in one place and `'b` in another by accident now introduces a new lifetime instead of producing an undeclared-lifetime error. Though the compiler would likely still reject the program through a mismatch, the error will be less direct.
- The new feature makes it possible to write the same signature in two styles, a cost to consistency.
- A name that appears in an `impl` header and the same name used in a method declaration may now conflict or shadow in confusing ways. Hence the multi-character lint.

## Rationale and alternatives
[rationale-and-alternatives]: #rationale-and-alternatives

**Do nothing.** Leaves the boilerplate in place.

**Require declarations for `impl` but not `fn`.** This reduces consistency without much benefit.

**Use a different sigil for in-band lifetimes.** A distinct marker would prevent typos from being accepted but would add syntax rather than remove it.

**Remove lifetime parameters entirely and infer them all.** This is not feasible in general, as lifetime relationships between arguments and return values cannot be inferred from bodies without breaking modularity.

## Unresolved questions
[unresolved-questions]: #unresolved-questions

- Should the single-character style lint apply only to `impl` headers, or also to `fn` items that bind in-band?
- Should `single_use_lifetimes` be on by default?
- Is there a better scheme than `'_` for the anonymous lifetime?

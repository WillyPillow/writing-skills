- Feature Name: `argument_lifetimes`
- Start Date: [TODO: date]
- RFC PR: [TODO: link]
- Rust Issue: [TODO: link]

# Summary

Eliminate the need to bind lifetime parameters separately in `fn` definitions and `impl` headers. Instead of writing:

```rust
impl<'a> Reader<'a> {
    fn next_token<'b>(&'b mut self, buf: &'a [u8]) -> Token<'a> { ... }
}
```

you can write:

```rust
impl Reader<'buf> {
    fn next_token(&'t mut self, buf: &'buf [u8]) -> Token<'buf> { ... }
}
```

Also lint against leaving off lifetime parameters on structs (as in `Ref` or `Iter`), and instead nudge people to write the lifetime explicitly, using the other changes in this RFC to keep that short.

The changes are:

1. A signature binds any lifetime it mentions that is not already bound.
2. A style lint checks that lifetimes bound in `impl` headers are more than one character long, to reduce confusion with lifetimes bound within functions.
3. `'_` explicitly elides a lifetime, and leaving off the lifetime parameters of a path entirely is deprecated.

There are some further, less important lints, described under "Reference-level explanation".

# Motivation

## Declaring a lifetime repeats its use

A lifetime name in a signature is only useful because it appears in two places, such as an argument and the return type. Today it must also appear in a third place, the `<...>` list, which says nothing the other two do not. In the first example above, `'b` is declared only so that it can be used once, and `'a` is declared on the `impl` so that it can be used in the method. For a reader, the binding list is a place to look up where a name came from; for a writer, it is a place to make an edit that the compiler then asks for.

The cost shows most when code changes. Adding a reference argument with a named lifetime to a method means editing two places in the signature. Moving a method from a free function into an `impl` block means moving its lifetime declaration as well. [TODO: add a concrete instance from the author, such as a diagnostic users commonly hit when they forget the declaration.]

## Elided lifetimes in paths hide borrowing

Lifetime elision in `fn` signatures lets the following compile:

```rust
fn iter_names(list: &NameList) -> Iter<String> { ... }
```

Nothing in the return type shows that `Iter<String>` borrows from `list`. A reader sees `&` in the argument, and knows a borrow is involved there, but sees no mark on `Iter`. The same reader seeing `Iter<'_, String>` knows at once that the return value holds a borrow and that elision rules connect it to an argument.

This RFC treats the two problems together because they interact. Asking people to write lifetimes on every borrowing path is more acceptable once writing a lifetime costs one token rather than a token plus a declaration.

# Guide-level explanation

## Using lifetimes without declaring them

In a function signature or an `impl` header, you can use a lifetime name without listing it in `<...>`. The name is bound at the item where it first appears:

```rust
fn longest(x: &'a str, y: &'a str) -> &'a str { ... }
```

means the same as:

```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str { ... }
```

In an `impl` header, an undeclared lifetime is bound by the `impl`, and every method in the block can use it:

```rust
impl Reader<'buf> {
    fn rest(&self) -> &'buf [u8] { ... }
}
```

Inside a method, a lifetime name that the `impl` has already bound refers to the `impl`'s lifetime. Any other undeclared name is bound by the method.

Explicit `<'a>` declarations still work and mean what they mean today. [TODO: decide whether mixing explicit declarations and implicit binding in one signature is allowed, warned against, or an error.]

## Naming convention for `impl` lifetimes

Because `impl` lifetimes and method lifetimes now look the same at their use site, a reader of a method signature cannot tell from `'a` alone whether it was bound by the method or by the `impl`. A style lint asks that lifetimes bound by an `impl` header use names longer than one character, such as `'buf` or `'tcx`. Single-character names such as `'a` then signal a lifetime local to one function.

## Writing `'_`

`'_` is a lifetime that is explicitly elided. It is accepted wherever an elided lifetime is accepted today, and it follows the same elision rules:

```rust
fn iter_names(list: &NameList) -> Iter<'_, String> { ... }
```

Writing a path to a type with lifetime parameters while leaving off the parameters, as in `Iter<String>`, triggers a deprecation lint. The fix the lint suggests is to add `'_`.

`'_` also works in `impl` headers, where it introduces a fresh lifetime that is not used anywhere else:

```rust
impl fmt::Debug for Reader<'_> { ... }
```

# Reference-level explanation

## Binding rule

When the compiler resolves a lifetime name in a signature, it looks it up in the following order:

1. Lifetimes declared explicitly on the enclosing items.
2. Lifetimes bound implicitly by the enclosing `impl` header.
3. If neither binds the name, the innermost `fn` or `impl` signature that mentions it binds it as a fresh lifetime parameter.

Implicit binding applies only in `fn` signatures and `impl` headers. It does not apply in `struct`, `enum`, `trait` or `type` definitions, where the parameter list is the type's public interface and its order matters to users of the type. [TODO: confirm that this is the intended scope, and say whether trait method signatures are included.]

The order of implicitly bound lifetimes is the order of their first appearance in the signature. This order is visible to callers that supply lifetimes explicitly with turbofish syntax. [TODO: decide whether implicitly bound lifetimes can be named in turbofish at all. If they can, reordering arguments in a signature becomes a breaking change for such callers.]

## Lints

1. `single_use_lifetimes`: warns when a named lifetime appears only once, since `'_` would do. [TODO: confirm this lint and its default level.]
2. `impl_header_lifetime_length` (name to be decided): warns when an `impl` header binds a one-character lifetime.
3. `elided_lifetimes_in_paths`: warns when a path to a type with lifetime parameters omits them.

[TODO: list the remaining "less important" lints the author intends.]

## Edition

[TODO: decide whether the deprecation of elided path lifetimes is tied to an edition, and at which level each lint starts.]

# Drawbacks

A typo in a lifetime name no longer produces an "undeclared lifetime" error. Writing `&'buff [u8]` in a method of `impl Reader<'buf>` silently binds a new method lifetime `'buff`. If the program then fails to compile, the error concerns a lifetime mismatch at the use site, which is harder to trace back to the typo. [TODO: decide whether a lint should flag a fresh lifetime whose name is close to one already in scope.]

The naming convention for `impl` lifetimes is a lint, not a rule, so code that ignores it is ambiguous to a reader. Existing code that uses `impl<'a>` with one-character names will trigger the lint if it moves to implicit binding.

Deprecating elided path lifetimes produces warnings in a large amount of existing code. [TODO: estimate how much, for example from a crater run.] Each fix is a local edit, adding `'_` to one path. [TODO: confirm that `rustfix` can apply these fixes automatically.]

Two ways of binding lifetimes will coexist, and readers must know both.

# Rationale and alternatives

[TODO: record which alternatives the author considered and why they lost. Candidates to ask about, not to be presented as considered without confirmation:]

- [TODO: Keep explicit binding and only add `'_`. This gives the readability gain for elided paths without changing how names are bound.]
- [TODO: Allow implicit binding in `fn` signatures but not in `impl` headers, which would avoid the ambiguity that motivates the naming lint.]
- [TODO: Distinguish `impl` lifetimes from method lifetimes by syntax rather than by a naming convention.]

The main reason to bind implicitly in both places, rather than only in functions, is that `impl` headers are where repeated declarations are most common and longest. [TODO: confirm this is the author's deciding reason.]

# Unresolved questions

1. Whether explicit and implicit binding may be mixed in one signature.
2. Whether implicitly bound lifetimes can be supplied by turbofish, and in what order.
3. Whether trait method signatures use implicit binding.
4. The default levels of the lints and their relation to editions.

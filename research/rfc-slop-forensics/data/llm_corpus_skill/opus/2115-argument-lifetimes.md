# Rust RFC 2115: argument_lifetimes

- Feature Name: `argument_lifetimes`
- Start Date: [TODO: date]
- RFC PR: [TODO]
- Rust Issue: [TODO]

## Summary

Eliminate the need to bind lifetime parameters separately in `fn` definitions and `impl` headers. Instead of writing

```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str { ... }

impl<'a> Parser<'a> {
    fn peek(&self) -> Option<&'a str> { ... }
}
```

you can write

```rust
fn longest(x: &'a str, y: &'a str) -> &'a str { ... }

impl Parser<'input> {
    fn peek(&self) -> Option<&'input str> { ... }
}
```

In addition, lint against leaving off lifetime parameters on structs such as `Ref` or `Iter`, and nudge people to write them explicitly, using the other changes in this RFC to make that ergonomic.

In summary, the changes are:

1. A signature binds any lifetime it mentions that is not already bound.
2. A style lint checks that lifetimes bound in `impl` headers are more than one character long, to reduce confusion with lifetimes bound within functions.
3. You can write `'_` to elide a lifetime explicitly. Leaving off the lifetime parameters of a struct entirely is deprecated.

There are some additional, less important lints, listed under the reference-level explanation.

## Motivation

A lifetime that appears once in a signature must today also appear once in the `<...>` list before it. For `longest` above, `<'a>` adds no information: the parameter types already show that `'a` is a lifetime and where it is used. The declaration exists only to bind the name.

The second problem is the opposite one. A type like `Ref<T>` or `Iter<T>` has a lifetime parameter, but a signature can omit it:

```rust
fn first(v: &Vec<u8>) -> Iter<u8> { ... }
```

Nothing in the return type tells the reader that the result borrows from `v`. The reader must know that `Iter` carries a lifetime. With `&`, the borrow is visible in the syntax. With a struct that hides its lifetime, it is not.

These two problems pull in different directions. Requiring explicit lifetimes on structs adds annotations, and today each new named lifetime also adds a declaration. This RFC removes the declaration cost, so that requiring the annotation on structs no longer costs a `<'a>` list.

[TODO: evidence that these problems affect users, such as reports from learners, survey results, or counts of signatures in real crates that hide a struct's lifetime. The motivation currently rests on the examples alone.]

## Guide-level explanation

When you write a function signature or an `impl` header, you can use a lifetime name without declaring it. Rust treats the first appearance as the declaration.

```rust
fn split_first(s: &'a str) -> (&'a str, &'a str) { ... }
```

Here `'a` is bound by `split_first`, exactly as if you had written `fn split_first<'a>(...)`.

Inside an `impl` block, a method can use the lifetimes bound by the header:

```rust
impl Parser<'input> {
    fn next_token(&mut self) -> Token<'input> { ... }
}
```

In `next_token`, `'input` refers to the lifetime bound by the `impl` header, because it is already bound when the method signature is read. A lifetime that the method mentions and the header does not bind is new and belongs to the method.

To say "this struct borrows something, and the compiler should infer the lifetime", write `'_`:

```rust
fn first(v: &Vec<u8>) -> Iter<'_, u8> { ... }
```

`'_` means the same thing as leaving the lifetime off does today. The difference is that a reader can see that `Iter` borrows.

## Reference-level explanation

### Binding rule

When the compiler resolves a lifetime name in an `fn` signature or an `impl` header, it searches the enclosing scopes in the usual way. If no enclosing scope binds the name, the innermost signature or header that mentions it binds it. The lifetime is added to that item's generic parameters in order of first appearance. [TODO: confirm "order of first appearance" and state whether that order is observable, for example through turbofish on late-bound or early-bound lifetimes.]

[TODO: whether explicit `<'a>` declarations and in-band lifetimes may be mixed in one signature. A suggested rule is that mixing is an error, so that a reader never has to check two places. This is a suggestion for the author to evaluate.]

### `'_`

`'_` is accepted wherever a lifetime is expected in a type, and it has the meaning that elision has in that position. In a position where elision is not allowed today, `'_` is an error for the same reason.

### Lints

1. Elided struct lifetimes. A path to a struct or enum with lifetime parameters, written without them and without `'_`, triggers a warning in a function signature. [TODO: default level, and whether the lint is tied to an edition.]
2. Single-character `impl` lifetimes. A lifetime bound in an `impl` header whose name is one character long triggers a style warning. Within a method, a short name such as `'a` then reads as the method's own lifetime, and a long name such as `'input` reads as the `impl`'s.
3. [TODO: the "additional, less important lints" the abstract mentions.]

## Drawbacks

The binding rule turns some errors into silent declarations. A typo in a lifetime name, such as `'inptu` instead of `'input`, today produces an "undeclared lifetime" error. Under this RFC, it binds a new, unrelated lifetime. The program usually still fails to compile, but with a borrow error that points at the use of the lifetime rather than at the typo. [TODO: whether the author has an example where the typo compiles and changes behavior, and whether a lint can catch it, for example by flagging a lifetime that appears only once in a signature.]

The rule also makes the meaning of a name inside a method depend on the enclosing `impl` header. Reading `'a` in a method signature, you must check the header to know whether `'a` is new. The single-character lint reduces that cost by convention. It does not remove it, because the lint is a style lint and code may allow it.

Deprecating elided struct lifetimes adds churn. Existing code that writes `Iter<u8>` in a signature gets warnings, and the fix is to add `'_` in each place. [TODO: an estimate of the number of affected signatures, for example from a run over published crates, and whether `rustfix` will apply the fix automatically.]

## Rationale and alternatives

The central trade-off is between less ceremony and an explicit point of declaration. This RFC gives up the explicit declaration for `fn` and `impl` signatures, and recovers some of its value with naming conventions enforced by lint.

[TODO: the alternatives the author actually considered and why each lost. Suggestions to evaluate include keeping today's rule and only adding `'_`; allowing in-band lifetimes in `fn` signatures but not in `impl` headers; and requiring a sigil to distinguish an in-band declaration from a use.]

Without this RFC, the lint against elided struct lifetimes would still be possible, but it would push users toward `fn f<'a>(x: &'a T) -> Iter<'a, U>`, which is longer than what they write today. `'_` alone addresses that case without in-band binding. [TODO: whether the author considers `'_` alone sufficient for the struct problem, and if not, why.]

## Prior art

[TODO: languages or tools with implicit binding of type or region variables, if the author wishes to cite them.]

## Unresolved questions

1. Whether mixing explicit and in-band declarations in one signature is allowed.
2. The default level of each lint, and whether any is tied to an edition.
3. The full list of the additional lints.
4. Whether a lint should catch lifetimes that appear only once in a signature, as a guard against typos.

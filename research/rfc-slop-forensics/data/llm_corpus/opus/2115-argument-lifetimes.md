- Feature Name: `argument_lifetimes`
- Start Date: 2017-08-21
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

Remove the requirement to declare lifetime parameters before using them in `fn` signatures and `impl` headers. Instead of:

```rust
fn two_args<'a, 'b>(arg1: &'a Foo, arg2: &'b Bar) -> &'b Baz
impl<'a> MyStruct<'a> { ... }
```

you can write:

```rust
fn two_args(arg1: &Foo, arg2: &'b Bar) -> &'b Baz
impl MyStruct<'a> { ... }
```

At the same time, nudge users toward writing lifetimes on structs that have them, such as `Ref<'_, T>` instead of `Ref<T>`, and make that easy.

The changes, in summary:

- A signature binds any lifetime it mentions that is not already in scope.
- A style lint checks that lifetimes bound implicitly in `impl` headers have names longer than one character, to distinguish them from lifetimes bound in functions.
- `'_` can be written anywhere to explicitly request an elided lifetime.
- Leaving off lifetime parameters on a struct path entirely, as in `Ref<T>`, is deprecated in favor of `Ref<'_, T>`.

# Motivation

## Declaring lifetimes is noise

Lifetimes are the part of Rust that new users find hardest. Part of that is inherent, but part of it is syntax. To use a named lifetime in a function, a user has to do two things: mention it in the type and also declare it in angle brackets after the function name. The declaration carries no information. Every named lifetime that appears in a signature must be declared, and the declaration is always in the same place, so the compiler can always infer it.

The declaration is especially noisy in `impl` blocks:

```rust
impl<'a> Iterator for Iter<'a> {
    type Item = &'a u8;
    ...
}
```

Here `'a` is declared once and used twice. The `impl<'a>` adds nothing a reader needs.

## Elision hides too much

Lifetime elision already lets users leave lifetimes off in common cases. For references this works well: `&Foo` clearly contains a borrow. For structs, it does not:

```rust
fn iter(&self) -> Iter<u8>
```

Nothing here tells the reader that `Iter` borrows from `self`. The user has to know that `Iter` has a lifetime parameter. This makes code harder to read and makes borrow checker errors more confusing, because the borrow they mention is invisible in the source.

The two problems pull in opposite directions. Users leave lifetimes off structs partly because writing them is annoying. If we make named lifetimes cheaper to write, and give a short way to say "the elided lifetime here," we can ask users to write lifetimes on structs without making code more cluttered.

# Guide-level explanation

## Lifetimes in functions

You can use a lifetime in a function signature without declaring it:

```rust
fn longest(x: &'a str, y: &'a str) -> &'a str { ... }
```

This means exactly the same as `fn longest<'a>(x: &'a str, y: &'a str) -> &'a str`. You can still declare lifetimes explicitly if you prefer. Declared and undeclared lifetimes can be mixed, and declaring a lifetime is still required if you want to give it bounds such as `'a: 'b` in the generics list (though a `where` clause also works).

## Lifetimes in impls

The same applies to `impl` headers:

```rust
impl Iterator for Iter<'iter> {
    type Item = &'iter u8;
    fn next(&mut self) -> Option<&'iter u8> { ... }
}
```

Lifetimes bound by the `impl` header are in scope for the entire `impl` block. Within a method, a lifetime that is not already bound by the `impl` is bound by the method.

That creates a possible confusion: in a long `impl` block, is `'a` in a method signature the `impl`'s lifetime or a new one? To make this easy to tell at a glance, the convention is that `impl`-level lifetimes get descriptive names (`'iter`, `'tcx`, `'buf`) and function-level lifetimes get single letters (`'a`, `'b`). A lint enforces the `impl` side of this when lifetimes are bound implicitly.

## `'_`

`'_` is the elided lifetime, written explicitly. It means "the same lifetime elision would have picked here." Use it to show that a type borrows something without naming the lifetime:

```rust
fn iter(&self) -> Iter<'_, u8>
impl fmt::Debug for Wrapper<'_> { ... }
```

In the second example, `'_` in an `impl` header means "a fresh lifetime I am not going to refer to," which is what most `impl` blocks for borrowed types need.

## Writing lifetimes on structs

A new lint, `elided_lifetimes_in_paths`, warns when a path to a struct, enum, or type alias leaves off its lifetime parameters. The fix is to add `'_` or a name:

```rust
fn iter(&self) -> Iter<u8>        // warning
fn iter(&self) -> Iter<'_, u8>    // fine
```

References (`&T`) are not affected. Their borrowing is already visible.

# Reference-level explanation

## Binding rules

When resolving a lifetime name in a signature:

1. If the name is already in scope (bound by an enclosing `impl`, an enclosing `fn`'s explicit generics, or a `for<'a>` binder), it refers to that binding.
2. Otherwise, it is bound as a new lifetime parameter of the innermost enclosing `fn` signature or `impl` header.

Lifetimes appearing in a function body are not covered: inside a body, an unbound lifetime remains an error. Only signatures and headers bind implicitly.

Implicit binding is not allowed inside `fn` pointer types, `Fn` trait sugar, or trait object types, because those positions introduce their own higher-ranked binders and implicit binding there would be ambiguous. In those positions, lifetimes must be declared with `for<'a>`, as today.

Implicitly bound lifetimes are late-bound or early-bound under the same rules as explicitly declared ones.

## Lints

- `single_use_lifetimes`: warns on a named lifetime that is used only once, suggesting `'_` instead.
- `impl_lifetime_names`: warns when a lifetime bound implicitly by an `impl` header has a single-character name.
- `elided_lifetimes_in_paths`: warns when a path omits lifetime parameters, as described above.
- `unused_lifetimes`: warns when an explicitly declared lifetime is never used.

All of these start as allow-by-default and move to warn-by-default once the features they recommend are stable.

## `'_` placement

`'_` is valid in any position where a lifetime can appear in a type in a signature. In argument and return positions it follows the existing elision rules. In `impl` headers it introduces a fresh anonymous lifetime. In positions where elision is not allowed today, such as struct field types, `'_` is an error.

# Drawbacks

- **Typos become new lifetimes.** If you mean `'a` and type `'b`, today you get "undeclared lifetime." With this RFC you may get a confusing type error instead. The `single_use_lifetimes` lint mitigates this, since a typo usually produces a lifetime used only once.
- **Two ways to write the same thing.** Explicit declarations stay legal, so codebases will contain both styles.
- **Shadowing confusion.** The rule that a method can reuse an `impl` lifetime's name by accident is exactly why the naming lint exists, but a lint is a weaker guarantee than an error.

# Rationale and alternatives

**Only add `'_`.** This addresses the struct elision problem but leaves declaration noise in place.

**Bind implicitly in `fn` but not `impl`.** `impl` headers are where declarations are most redundant, so this would miss the biggest benefit.

**Require a sigil for implicitly bound lifetimes.** For example, `'a` would require declaration and `'^a` would not. This adds a second syntax for lifetimes and was felt to be worse than the problem.

# Unresolved questions

- Should implicit binding in `impl` headers be allowed in `trait` definitions as well?
- What should the naming lint's threshold be: more than one character, or something else?

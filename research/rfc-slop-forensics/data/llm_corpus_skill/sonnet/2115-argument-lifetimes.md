# RFC 2115: argument_lifetimes

## Summary

This RFC removes the need to declare lifetime parameters in `fn` definitions and `impl` headers by hand. It also adds a lint that discourages leaving lifetime parameters off structs such as `Ref` or `Iter`, and pushes people toward explicit lifetimes there, using the other changes to make that ergonomic.

The changes are:

- A signature binds any lifetime it mentions that is not already bound.
- A style lint checks that lifetimes bound in `impl` headers are more than one character long. The purpose is to reduce confusion with lifetimes bound within functions.
- A user can write `'_` to elide a lifetime explicitly, and leaving off lifetime parameters entirely is deprecated. [TODO: the abstract is truncated at this point. Complete the statement of what is deprecated, and the list of "additional, less important lints" that the abstract mentions.]

## Motivation

Today, a lifetime used in a function signature must first be declared in angle brackets after the function name. The following function has one lifetime, and the declaration is the only place it is introduced:

```rust
fn first<'a>(items: &'a [String]) -> &'a String { &items[0] }
```

With this RFC the same function is written as:

```rust
fn first(items: &'a [String]) -> &'a String { &items[0] }
```

[TODO: the author's material says "so that instead of writing: you can write:" but the code was lost from the abstract. Confirm that the example above matches the author's intended before and after forms.]

The declaration is boilerplate in the sense that the compiler already knows which lifetimes appear. [TODO: the author to supply the evidence that this boilerplate is a real obstacle. Candidates are survey results, issue-tracker threads, or a count of how many signatures in a named code base carry a declaration that only repeats what the body says. The RFC cannot claim that the syntax is a barrier to learning without such evidence.]

The second motivation is the opposite problem. A struct with a lifetime parameter, such as `Ref` or `Iter`, can currently be written in a signature without any lifetime:

```rust
fn get(cell: &RefCell<T>) -> Ref<T>
```

Here `Ref<T>` carries a hidden lifetime. A reader sees no sign that the returned value borrows from the argument. The RFC proposes a lint against this form. [TODO: the author to confirm the example and to say how often this hidden lifetime causes a real misunderstanding, with a source.]

## Guide-level explanation

### Lifetimes bind where they are first mentioned

A signature "binds" a lifetime when it mentions a name that is not already in scope. In the `first` example, `'a` is not in scope when the signature is read, so the signature binds it. The reader no longer needs a separate list.

The rule applies to `fn` definitions and `impl` headers. In an `impl` header, a lifetime that is mentioned and not already bound is bound for the whole `impl` block, and every method in the block can use it.

### Explicit elision with `'_`

Writing `'_` marks a lifetime as elided on purpose. For example:

```rust
fn get(cell: &RefCell<T>) -> Ref<'_, T>
```

The `'_` makes the borrow visible to the reader while leaving the compiler to infer the actual lifetime by the existing elision rules. [TODO: confirm that the existing elision rules apply unchanged to `'_`.]

### The long-name lint

Lifetimes bound in `impl` headers live longer, in textual terms, than lifetimes bound inside a single function. A one-letter name like `'a` in an `impl` header can be confused with an `'a` introduced inside a method. The style lint asks that `impl`-bound lifetimes use names with more than one character, for example `'cell` or `'items`. [TODO: say whether the lint is warn-by-default or allow-by-default, and why.]

## Reference-level explanation

### Binding rule

[TODO: specify the algorithm precisely. It must say in what order the compiler looks up a lifetime name: first in enclosing scopes, then in the signature. It must say what happens when a name is mentioned in an `impl` header and again in a method signature, since the method signature must not rebind the name silently.]

The shadowing case needs an explicit rule. Consider an `impl` block that binds `'a` through its header and contains a method that also mentions `'a`. Under the proposal the method's `'a` refers to the one from the header, because that name is already bound. Under current Rust, writing `<'a>` in the method would be an error because the name shadows another. [TODO: verify against the compiler, and give the exact error that remains.]

### Interaction with `'static`

[TODO: state how `'static` and other reserved lifetimes are treated. The material does not say.]

### The lint on omitted parameters

The lint fires when a path names a type that has lifetime parameters and supplies none. [TODO: list the exact path forms covered (in function arguments, return types, struct fields, `impl` headers), and the forms exempted. Say whether `Self` is covered.]

### Additional lints

The abstract refers to "some additional, less important lints". [TODO: list them. A lint not described here cannot be reviewed.]

## Drawbacks

1. A lifetime bound by mention is easy to introduce by typo. `fn f(x: &'a T, y: &'b U)` where `'b` was meant to be `'a` now compiles and gives a function with two independent lifetimes. Under the current rules the declaration list makes such a typo visible, because the unknown name fails to compile. [TODO: judge the cost. If the author has data on how often this error is caught by the current rule, add it. If the author's view is that it is rare, state that view as an opinion and not as a measured fact.]
2. The rule makes the grammar of signatures harder to read in one respect: a reader has to scan the whole signature to find where a lifetime first appears. [TODO: author to respond.]
3. The deprecation of omitted parameters changes code that compiles today. [TODO: say how many warnings the standard library and a named set of popular crates produce under the new lint. The material has no number, so the RFC cannot yet claim the lint is low-noise.]

## Rationale and alternatives

The material does not record which alternatives the author weighed. The following are suggestions for the author to evaluate. They are not options that were considered and rejected.

- Keep the declaration and only add the `'_` syntax. This resolves the second motivation and leaves the first.
- Bind by mention but require a marker, such as a leading sigil, on the first mention. This avoids the typo problem described under Drawbacks, at the cost of new syntax.
- Do nothing.

[TODO: for each alternative the author actually considered, give the goal or constraint that made it lose. Say which decisions in this RFC are hard to reverse. The binding rule is the main one: once code is written that depends on it, it cannot be changed without breaking that code.]

## Unresolved questions

- The complete list of additional lints.
- The default level of the long-name lint.
- The exact interaction with `'static` and with elision in closures. [TODO: confirm whether closures are in scope.]
- Whether the deprecation of omitted parameters is a warning in the first release or later.

## Migration

[TODO: give the rollout. Name the release in which each part lands, state how a user turns each lint off, and say whether an automatic fix tool will rewrite old signatures. The material gives none of these.]

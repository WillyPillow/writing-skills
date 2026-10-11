# Rust RFC 2113: dyn Trait Syntax

- Feature Name: `dyn_trait_syntax`
- Start Date: 2017-08-02
- RFC PR: rust-lang/rfcs#2113
- Rust Issue: rust-lang/rust#44662

## Summary
[summary]: #summary

Introduce a new `dyn Trait` syntax for trait objects using a contextual `dyn` keyword, and deprecate "bare trait" syntax for trait objects. In a future edition, `dyn` will become a proper keyword and a lint against bare trait syntax will become deny-by-default.

## Motivation
[motivation]: #motivation

Rust uses the same syntax for two different things: naming a trait in a bound, and naming a trait object type. Given a trait `Foo`, the following are all accepted:

```rust
fn generic<T: Foo>(x: T) { }        // a bound: T implements Foo
fn object(x: &Foo) { }              // a type: a reference to a trait object
fn boxed(x: Box<Foo>) { }           // a type: a boxed trait object
impl Foo for u32 { }                // an impl of the trait
impl Foo { fn inherent(&self) { } } // inherent methods on the trait object type
```

In the second, third and fourth cases, `Foo` in type position means "the unsized type of trait objects implementing `Foo`." There is nothing in the syntax that says so. A reader has to know, or look up, that `Foo` is a trait rather than a struct or enum, to understand that dynamic dispatch is involved.

This causes real confusion, which has been observed repeatedly among learners and experienced programmers alike.

### Dynamic dispatch is invisible

Dynamic dispatch has costs and consequences: a vtable lookup on each method call, inability to inline, restrictions on object safety, and a pointer representation that is twice as wide. When these costs are hidden, readers cannot see at a glance where they are paying them. A code reviewer looking at `fn f(x: &Foo)` has to know that `Foo` is a trait to realize `f` is not generic and not monomorphized.

### The syntax overlaps with other parts of the language

`impl Foo { ... }` looks like inherent methods on a struct called `Foo`, yet if `Foo` is a trait, it means adding methods to the trait object type. The distinction between `impl Foo for Bar` and `impl Foo` is just a missing `for` clause, which is an easy typo to make and confusing to diagnose.

Another problem arises with `impl Trait`, being added to the language at roughly the same time. `fn f() -> impl Foo` and `fn f() -> Foo` look similar and mean very different things. The latter, in the current syntax, would be an unsized return type, which is an error, but the error message is confusing because nothing says the programmer wrote a trait object type.

### Parsing and extensibility problems

Types such as `Box<Foo + Send>` and `&(Foo + Send)` require special handling in the parser. `&Foo + Send` is ambiguous with a binary operator, so parentheses are needed in some positions and not others. Also, `Foo + 'a` forms are used for lifetime bounds on trait objects. A distinct leading keyword avoids these ambiguities.

### Teaching

The Rust book and other learning materials spend effort explaining that "a trait name in type position is a trait object." A syntax that makes the fact explicit removes this explanation and helps beginners build the right mental model.

## Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

A trait object type is written with the `dyn` keyword in front of the trait bounds:

```rust
fn object(x: &dyn Foo) { }
fn boxed(x: Box<dyn Foo>) { }
fn with_send(x: Box<dyn Foo + Send>) { }
fn with_lifetime<'a>(x: Box<dyn Foo + 'a>) { }
impl dyn Foo {
    fn inherent(&self) { }
}
```

The word `dyn` is short for "dynamic," chosen to signal dynamic dispatch. It parallels `impl Trait` in return position: `impl Trait` means "some concrete type that implements the trait, chosen by the function"; `dyn Trait` means "some type implementing the trait, decided at runtime."

The old syntax continues to compile for now, and the compiler gives a warning when it is used, suggesting the `dyn` form. Existing code can be fixed mechanically; `rustfix` is expected to handle it.

## Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

### Grammar

The type grammar gains a production:

```
TraitObjectType := 'dyn' TypeParamBounds
```

where `TypeParamBounds` is the existing grammar for a `+`-separated list of bounds, which can include a leading `?Sized`-style bound, lifetimes, and higher-ranked `for<'a>` bounds.

In positions where a bare `Trait + Other` would require parentheses, such as behind `&`, the same rule applies: `&(dyn Foo + Send)`. This RFC does not change the precedence rules.

### Contextual keyword

In the 2015 edition, `dyn` is a contextual keyword. It is treated as a keyword only when it appears in type position followed by something that can begin a path or bound, and is not followed by `::` or `<`... Specifically, a type starting with the identifier `dyn` followed by a path, a lifetime, `for`, `?`, or `(` is parsed as a trait object type. Otherwise `dyn` is an ordinary identifier. This keeps code that uses `dyn` as a name for a variable, function, or type (for instance, in a crate named `dyn`) compiling.

This means the following continues to parse as before:

```rust
struct dyn;
let dyn = 5;
fn dyn() {}
```

A path such as `dyn::Foo` is also still a path, not a trait object.

### Deprecation of bare trait objects

A new lint, `bare_trait_object`, fires whenever a trait object type is written without `dyn`. It is allow-by-default initially, to avoid flooding existing code with warnings before tooling is ready. After `rustfix` support lands, it moves to warn-by-default.

In the next edition, `dyn` becomes a true keyword and the lint becomes deny-by-default. Bare trait object syntax is eventually an error in a later edition, once the community has migrated.

### Interaction with other features

- `impl Trait` is unaffected.
- Trait aliases and `auto traits` follow whatever bounds rules they have today.
- Macros that generate types: a `$t:ty` fragment accepts `dyn` types. The `$i:ident` fragment will match `dyn` in the 2015 edition since it is contextual.

## Drawbacks
[drawbacks]: #drawbacks

- Churn. Every piece of existing code using trait objects will eventually need updating. While the change is mechanical, it creates a transition period and affects documentation, books, blog posts and Stack Overflow answers.
- Verbosity. `Box<dyn Foo>` is slightly longer than `Box<Foo>`. For a feature as common as trait objects, this adds up.
- A contextual keyword is a parser complication that will be removed in the next edition.

## Rationale and alternatives
[rationale-and-alternatives]: #rationale-and-alternatives

### Alternative keywords

Several other spellings were suggested: `virtual`, `object`, `any`, `box`, and `trait`. `dyn` is short, pronounceable, already associated with "dynamic dispatch" in other languages, and was not reserved elsewhere. `trait Foo` in type position was considered, but it already has a meaning at item level, and a type-position `trait` would lead to ambiguities.

### Do nothing

The status quo means beginners continue to be confused, and new features such as `impl Trait` will be harder to explain.

### Make `dyn` mandatory immediately

This would break essentially all existing Rust code. A deprecation period backed by tooling is the established way to evolve the language.

### Use `Box<dyn Foo>` only

Another option would limit `dyn` to boxed trait objects. This would make references to trait objects inconsistent with owned ones.

## Unresolved questions
[unresolved-questions]: #unresolved-questions

- Exactly when should the lint be raised to warn-by-default?
- Should the `rustfmt` tool be updated to rewrite bare trait objects automatically, or should that be left to `rustfix`?
- How should documentation and the book handle the period during which both syntaxes are valid?

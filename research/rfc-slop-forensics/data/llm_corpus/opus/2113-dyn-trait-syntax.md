- Feature Name: `dyn_trait_syntax`
- Start Date: 2017-08-17
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

Add a new syntax for trait object types, `dyn Trait`, using `dyn` as a contextual keyword. Deprecate the current "bare trait" syntax, in which a trait name used as a type means a trait object. In a future edition, make `dyn` a full keyword and make the lint against bare trait objects deny-by-default.

```rust
// Today
fn draw_all(shapes: &[Box<Shape>]) { ... }

// With this RFC
fn draw_all(shapes: &[Box<dyn Shape>]) { ... }
```

# Motivation

## Traits and types share a namespace

In Rust today, a trait name means two different things depending on where it appears. In a bound, `T: Display` means "some type that implements `Display`." In type position, `Box<Display>` means "a trait object": a pointer to a value of some unknown type that implements `Display`, plus a vtable. The two are very different in cost and capability. Generics are monomorphized and statically dispatched; trait objects are dynamically dispatched, have a size known only at runtime, and are subject to object safety rules.

Nothing in the syntax of `Box<Display>` says that it is a trait object. A reader has to know that `Display` is a trait and not a struct. This is a frequent source of confusion for newcomers, who reasonably expect `Box<Display>` to work like `Box<String>`, and who are then surprised by object safety errors or by the lack of static dispatch.

## `impl Trait` makes the asymmetry worse

RFC 1522 and RFC 1951 introduced `impl Trait` for "some specific type that implements this trait, chosen by the function." With `impl Trait` in the language, there are now two ways to use a trait as a type, and they look like this:

```rust
fn a() -> impl Iterator<Item = u8> { ... }   // static
fn b() -> Box<Iterator<Item = u8>> { ... }   // dynamic
```

The static version is marked and the dynamic version is not. That is backwards from what we would choose if designing from scratch: the more costly, more restricted form should be the one that stands out. A `dyn` keyword gives the two forms parallel syntax:

```rust
fn a() -> impl Iterator<Item = u8> { ... }
fn b() -> Box<dyn Iterator<Item = u8>> { ... }
```

Teaching becomes simpler too. "Use `impl Trait` for static dispatch, `dyn Trait` for dynamic dispatch" is a rule a beginner can hold onto.

## Parsing ambiguities

Bare trait syntax causes problems for the grammar. `&Trait + Send` does not parse as intended; users must write `&(Trait + Send)`. The precedence rules for `+` in type position exist mostly to support bare trait objects. With a leading keyword, `&dyn Trait + Send` can be given the natural parse in a future edition.

Bare trait syntax also makes it impossible to tell, at parse time, whether a path in type position refers to a type or a trait. That restricts future syntax that might want to treat the two differently.

## Future features

Several proposed features would give a trait name a meaning in type position that is not "trait object." For example, if bare `Trait` were ever to mean `impl Trait` in some positions, there would need to be a separate way to say "trait object." Moving trait objects to `dyn Trait` keeps those options open.

# Guide-level explanation

A trait object type is written `dyn Trait`. It can be used anywhere a trait object can be used today, typically behind a pointer:

```rust
let x: Box<dyn Display> = Box::new(5);
let y: &dyn Fn(i32) -> i32 = &|n| n + 1;
let z: Arc<dyn Any + Send + Sync> = Arc::new(());
```

Auto traits and lifetime bounds go after the main trait, as before: `dyn Error + Send + 'static`.

The old syntax, `Box<Display>`, still compiles but produces a warning suggesting `dyn`. `cargo fix` (or an equivalent tool) can update code automatically.

When explaining traits to new users, the book will introduce `impl Trait` and `dyn Trait` together: `impl` for "some type chosen at compile time," `dyn` for "some type chosen at runtime."

# Reference-level explanation

## Grammar

A new type form is added:

```
TraitObjectType := 'dyn' TypeParamBounds
```

In the current edition, `dyn` is a contextual keyword: it is treated as starting a trait object type only when it appears in type position and is followed by a path, a lifetime, `?`, `for`, or `(`. Elsewhere, `dyn` remains a valid identifier, so existing code that names a variable, function, or module `dyn` continues to compile.

One edge case requires care: `dyn::foo::Bar` in type position, where `dyn` is a module. In the current edition this continues to parse as a path. Writing a trait object for a trait reached through a path starting with `::` requires parentheses or the `crate::` prefix. This is an unusual case and is resolved in the next edition when `dyn` becomes reserved.

## Semantics

`dyn Trait` has exactly the same meaning as bare `Trait` in type position today. Object safety rules, default object lifetime bounds, and coercion rules are unchanged. This RFC changes syntax only.

## Lint

A new lint, `bare_trait_objects`, fires on any trait object type written without `dyn`. It is allow-by-default when first introduced, so that the ecosystem has time to move. Once `dyn` has been stable for a release cycle and automatic migration tools are available, it becomes warn-by-default.

## Next edition

In the next edition:

- `dyn` becomes a reserved keyword.
- `bare_trait_objects` becomes deny-by-default.

Bare trait syntax is not removed from the grammar entirely, because code in older editions must continue to compile and crates of different editions interoperate. But new code in the new edition will not be able to use it without explicitly allowing the lint.

# Drawbacks

- **Churn.** Nearly every Rust codebase uses trait objects. Every use will eventually need updating. Automated migration reduces the cost but does not remove it, and documentation, blog posts, and Stack Overflow answers using the old syntax will remain for years.
- **Verbosity.** `Box<dyn Fn(u8) -> u8>` is four characters longer than before. Trait objects are common enough that this adds up.
- **Contextual keyword complexity.** Treating `dyn` as a keyword only in some positions complicates the parser and tools that tokenize Rust.

# Rationale and alternatives

**Do nothing.** The confusion described above is real and would grow as `impl Trait` becomes common.

**Other keywords.** Candidates included `virtual`, `obj`, `object`, `trait`, and the sigil `@`. `virtual` is already reserved, but it has strong C++ associations with inheritance that do not match Rust's model. `trait Display` in type position is confusing because `trait` already introduces trait definitions. Sigils have been tried before in Rust (`@T` was once a managed pointer) and were removed in favor of readable keywords. `dyn`, short for "dynamic," is brief, pairs naturally with `impl`, and directly describes dynamic dispatch.

**Use `impl` for both, distinguished by position.** This would hide exactly the distinction we want to make visible.

**Make the change in one step.** We could make `dyn` a full keyword immediately in the next edition and skip the contextual phase. The contextual phase lets library authors adopt `dyn` now, in code that also compiles on the current edition, which makes migration smoother.

# Unresolved questions

- Should the `&dyn Trait + Send` precedence change happen in the same edition as the keyword reservation, or separately?
- What is the exact timeline for moving `bare_trait_objects` from allow to warn?

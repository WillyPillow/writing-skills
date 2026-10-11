# RFC 2845: supertrait_item_shadowing

- Feature Name: `supertrait_item_shadowing`
- Start Date: 2020-05-18
- RFC PR: rust-lang/rfcs#2845
- Rust Issue: rust-lang/rust#89151

## Summary

Change item resolution for generics and trait objects so that a trait bound does not bring its supertraits' items into scope if the subtrait defines an item with this name itself.

## Motivation

Rust lets a library add a new method to a trait without it being a breaking change, as long as the method has a default implementation. That is a stated part of the API evolution guidelines. In practice, however, this promise has a gap. When two traits are involved, a new method on a supertrait can silently break code that uses a subtrait.

Consider the following, which compiles today:

```rust
trait Super {}

trait Sub: Super {
    fn describe(&self) -> String;
}

fn show<T: Sub>(t: &T) -> String {
    t.describe()
}
```

Now the author of `Super` adds a defaulted method:

```rust
trait Super {
    fn describe(&self) -> String { String::from("super") }
}
```

The function `show` now fails to compile with an ambiguity error:

```
error[E0034]: multiple applicable items in scope
  --> src/lib.rs:9:7
   |
9  |     t.describe()
   |       ^^^^^^^^ multiple `describe` found
```

The bound `T: Sub` implies `T: Super`, so both `Sub::describe` and `Super::describe` are candidates. The compiler refuses to choose between them. Yet from the user's point of view the choice is obvious: they wrote `T: Sub`, and `Sub` defines `describe`.

This is not an exotic situation. It affects:

- Library authors who own both the subtrait and the supertrait, and who want to add a method to the supertrait without waiting for a major release.
- Standard library evolution. When new methods are added to widely used traits, such as `Iterator`, `Read` or `Ord`, downstream traits that extend them and happen to share a name can break. The standard library team has had to restrict method names or carefully stage additions through unstable features to avoid this.
- Extension traits. The pattern of defining `trait FooExt: Foo` with convenience methods is widespread. If `Foo` later adds a method with the same name, every user of `FooExt` is affected.

The ambiguity is also a problem because the subtrait is conceptually "closer" to the user. In an object-oriented setting, a method defined in a subclass overrides one from a superclass, rather than colliding with it. Rust's current rule treats all traits in scope as peers, which is simple but turns a compatible change into a breaking one.

Note that this problem has been described for years under the name "fragile base class", with the standard library adding the `#[rustc_...]` machinery and the "unstable name collision" lint as a mitigation only for inherent methods versus trait methods.

## Guide-level explanation

When you call a method on a value whose type is a generic parameter `T: Sub`, or on a trait object `dyn Sub`, the compiler looks for methods that come from the bound. If `Sub` itself declares a method with that name, then that method is used. Methods with the same name coming from supertraits of `Sub` are shadowed, and are not considered.

```rust
trait Super {
    fn describe(&self) -> String { String::from("super") }
}

trait Sub: Super {
    fn describe(&self) -> String;
}

fn show<T: Sub>(t: &T) -> String {
    t.describe() // resolves to Sub::describe
}
```

If you want the supertrait's method, say so explicitly:

```rust
fn show_super<T: Sub>(t: &T) -> String {
    Super::describe(t)
}
```

or with the fully qualified syntax `<T as Super>::describe(t)`.

The rule applies to associated functions, constants and types in the same way as to methods. If `Sub` declares `const ID: u32` and `Super` also does, then `T::ID` refers to `Sub`'s.

### What does not change

- If the same name occurs in two *unrelated* traits that are both in the bound, such as `T: A + B`, the call is still ambiguous, and the user must disambiguate.
- Inherent methods still take priority over trait methods, and the existing rules about autoref and autoderef are unchanged.
- Concrete types, not generics, are unaffected. If `S` implements both `Sub` and `Super`, then `s.describe()` is resolved based on which traits are in scope at the call site, as before.

## Reference-level explanation

### Current behaviour

During method resolution for a receiver whose type is a type parameter `T`, the compiler collects candidates from every trait bound `T: Trait` in the where-clauses in scope, expanding each bound to include all supertraits transitively. Candidates with the same name from different traits cause ambiguity at the final probing step if both apply at the same autoderef step.

The same holds for trait objects, where the "bounds" are the principal trait and its supertraits, and for associated item paths like `T::name`.

### New behaviour

When expanding bounds into candidates, apply the following rule:

> For a bound `T: Tr`, the candidates contributed by `Tr` are the items declared in `Tr` itself, together with the items of each supertrait `S` of `Tr` *whose name is not declared in any subtrait of `S` on the path from `Tr` to `S`*.

More precisely, define a partial order on traits by the "is supertrait of" relation. For a given name `n` and set of bound traits `B`, collect the traits in the transitive closure of `B` which declare an item named `n`. Remove from this set any trait `S` for which there is another trait `Sub` in the set such that `Sub` is a strict subtrait of `S`. If exactly one trait remains, resolution succeeds with that trait's item. If more than one remains, they are mutually unrelated, and the call is ambiguous.

This is the usual notion of overriding in languages with inheritance: the most derived declaration wins.

### Diamond inheritance

Rust trait hierarchies may form diamonds: `trait D: B + C`, `trait B: A`, `trait C: A`. If `A` declares `f` and neither `B` nor `C` does, then the only remaining candidate is `A::f`, regardless of the number of paths. If `B` also declares `f`, then `B::f` shadows `A::f`, but `C`'s view of `f` (from `A`) is unrelated to `B::f`. Since `C` does not declare `f`, `A::f` is shadowed only through `B`. Under the rule above, `A` is removed because `B` is a strict subtrait of `A` in the set, leaving `B::f` alone. This asymmetry could be surprising, so the compiler should warn when shadowing happens in a diamond.

### Lint

A warn-by-default lint `supertrait_item_shadowing` is emitted at the *definition* of a subtrait item that shadows a supertrait item with the same name, if the subtrait's author did not deliberately name the item to override. Since the shadowing is not true overriding (implementations of `Sub` do not provide an implementation of `Super::describe`), the lint nudges authors toward distinct names. It can be silenced with `#[allow(supertrait_item_shadowing)]`.

A second lint, allow-by-default, fires at *use sites* where the resolution depends on the new rule and would have been ambiguous under the old one. This is useful for people assessing the effect on their code.

### Backwards compatibility

The change turns some previously ambiguous (error) programs into valid programs. It can also change the meaning of existing programs in one case: if a program currently resolves a name via a path that is not ambiguous because only one of the traits is a bound, but a later addition introduces a more derived trait. Because the new rule only removes candidates that are less derived than another candidate with the same name, a call that previously had exactly one candidate continues to have exactly that candidate. The rule never selects a candidate that was not already selected unambiguously, except in cases that were previously errors. Thus, accepted programs keep their meaning.

### Implementation

The change is local to the method probe and the associated item lookup in `rustc_hir_typeck` and `rustc_hir_analysis`. After assembling candidates from where-clauses and from object bounds, a filtering pass removes shadowed entries before ambiguity is reported. The pass requires supertrait elaboration, which is already computed.

## Drawbacks

- **Silent behavior differences between generic and concrete code.** In the example above, `show::<S>` calls `Sub::describe`, but `s.describe()` on a concrete `S` with both traits in scope is still ambiguous. Users who move between the two may be confused.
- **The shadowed item becomes hard to notice.** A reader may not realize that `Super::describe` exists. The lint partially addresses this.
- **Subtle semantics for diamonds.**
- **Does not solve inherent vs trait conflicts.** The same style of breakage for inherent methods is handled by other mechanisms.

## Rationale and alternatives

### Do nothing

Library authors can avoid adding methods to supertraits or can wait for a major version. This undermines the usefulness of defaulted methods as a tool for evolution.

### Make concrete types behave the same way

The same shadowing could be applied for concrete types with both traits in scope. But a concrete type's call site may import traits independently, and there is no natural notion of "closer", since the traits in scope are determined by `use` declarations. Extending the rule risks more complexity than benefit.

### Require explicit disambiguation always

This is the status quo and the source of the problem.

### Use name-mangling or namespacing for supertrait items

This would solve the problem more fundamentally but would require much larger language changes.

## Prior art

In Java and C++, a member declared in a subclass hides inherited members of the same name; C++ is a classic case, where name hiding applies even if signatures differ, a source of frequent surprises. C# warns about hiding with the `new` modifier. Scala's linearization chooses the most derived trait. Swift protocols with extensions have a similar ambiguity resolution based on specificity. Kotlin requires explicit overrides when there is a conflict.

## Unresolved questions

- Should the lint on the subtrait definition be warn-by-default or allow-by-default?
- Should the rule apply across crate boundaries in the same way for items added after the subtrait was published? Most of the motivation is for this case, and it is the proposal's current behaviour.
- How should rustdoc present shadowed items?
- Should the same rule be applied to `impl Trait` argument-position bounds? As these desugar to generics, the current plan says yes.

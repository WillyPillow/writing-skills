- Feature Name: `supertrait_item_shadowing`
- Start Date: [TODO: date]
- RFC PR: [TODO: link]
- Rust Issue: [TODO: link]

# Summary

Change item resolution for generics and trait objects so that a trait bound does not bring a supertrait's item into scope if the subtrait defines an item with the same name itself.

# Motivation

## The ambiguity

Consider two traits where the subtrait defines a method with the same name as one in its supertrait:

```rust
trait Super {
    fn describe(&self) -> String;
}

trait Sub: Super {
    fn describe(&self) -> String;
}

fn show<T: Sub>(x: &T) -> String {
    x.describe()
}
```

The bound `T: Sub` brings the items of `Sub` into scope, and because `Super` is a supertrait of `Sub`, it brings the items of `Super` into scope as well. The call `x.describe()` then finds two candidates and fails with an ambiguity error. The caller must write `Sub::describe(x)` or `<T as Sub>::describe(x)` to pick one.

The same happens with a trait object:

```rust
fn show_dyn(x: &dyn Sub) -> String {
    x.describe()   // error today: ambiguous
}
```

## How the ambiguity arises in practice

The case that motivates this RFC is one where the name clash appears later, through a change in another crate.

The pattern involved is the extension trait: a crate defines a trait with a supertrait it does not own and adds methods to it.

```rust
// crate `iterutil`
pub trait IterExt: Iterator {
    fn tally(self) -> usize where Self: Sized { ... }
}
impl<I: Iterator> IterExt for I {}

// user code
fn count_items<I: IterExt>(it: I) -> usize {
    it.tally()
}
```

Suppose a later version of the standard library adds a method named `tally` to `Iterator`. `count_items` now fails to compile, because the bound `I: IterExt` brings both `IterExt::tally` and `Iterator::tally` into scope. The user did nothing; the library that owns the supertrait added a method, and a crate that depends on it broke.

[TODO: give a real instance of this breakage, for example a method added to a standard trait that clashed with a method in a published extension trait, and how it was handled.]

Adding a method to a trait is meant to be a minor change under Rust's semver conventions, because a provided method does not require any implementor to change. This failure mode makes such additions riskier for traits that are commonly extended, and it gives the owners of those traits a reason not to add methods whose names extension traits already use.

# Guide-level explanation

When you call a method on a value whose type is a generic parameter or a trait object, and the method name is defined both by the bound trait and by one of its supertraits, the bound trait's method is chosen.

In the first example above, `x.describe()` inside `show` calls `Sub::describe`. To call the supertrait's method, write `Super::describe(x)`.

In the extension-trait example, `it.tally()` inside `count_items` keeps calling `IterExt::tally` after `Iterator` gains its own `tally`. The user's code compiles and behaves as before.

The rule applies only when the subtrait is more specific than the supertrait in the bound. If a generic function is bounded by both traits directly, as in `T: Sub + Super`, the ambiguity remains, because the user has named both traits. [TODO: confirm this with the author. The opposite rule, where `Sub` still shadows `Super` because `Sub: Super`, is also defensible.]

# Reference-level explanation

During method and associated item resolution on a type parameter `T` or on `dyn Trait`, the compiler collects candidate items from the traits in scope through the bounds. This RFC changes that collection as follows:

1. For each trait `A` brought into scope by a bound, collect `A`'s own items.
2. For each supertrait `B` of `A`, transitively, collect `B`'s items, except those whose name matches an item already collected from a trait that has `B` as a supertrait.
3. If more than one candidate remains, report an ambiguity error as today.

"Matches" means same name and same namespace: a method shadows only a method or associated function, and an associated type shadows only an associated type. [TODO: confirm whether associated constants and associated types are included, or whether the rule covers only methods.]

Shadowing is by name only. A subtrait method with a different signature from the supertrait method still shadows it. [TODO: confirm. Comparing signatures would prevent surprising shadowing but would also reintroduce the breakage in the motivating example whenever the two methods' signatures differ.]

The rule does not apply to method calls on concrete types. For a concrete type that implements both traits, both are in scope through `use` declarations, not through a bound, and the existing rules remain. [TODO: confirm. A user who calls `tally` on a concrete iterator with `IterExt` imported would still see the ambiguity after `Iterator` gains `tally`, so this RFC covers only part of the motivating breakage. The document should say whether that part is addressed elsewhere.]

# Drawbacks

Shadowing can surprise a reader. In `show`, a reader who knows `Super::describe` but has not looked at `Sub` may expect `x.describe()` to call `Super::describe`. Today the compiler tells them about the conflict; after this change it chooses silently.

[TODO: decide whether a lint should warn when a subtrait item shadows a supertrait item, at the definition of the subtrait, at each call site, or not at all. A warning at the definition would alert the author of `IterExt` when `Iterator` gains `tally`, without breaking their users.]

Resolution behavior differs between generic code and concrete code. The same call `it.tally()` resolves without error in `count_items` but may be ambiguous on a concrete iterator type. Users must know which context they are in.

# Rationale and alternatives

The subtrait is chosen, rather than the supertrait, because the bound in the user's code names the subtrait. The user asked for `IterExt`, so `IterExt`'s methods are what the call most likely means. Choosing the supertrait would make code that compiles today change meaning when an upstream trait adds a method. [TODO: confirm with the author that this is the deciding reason.]

[TODO: record which alternatives the author considered and why they lost. Candidates to ask about, not to be presented as considered without confirmation:]

- [TODO: Keep the current behavior and rely on library authors to avoid adding clashing method names.]
- [TODO: Add an attribute that lets a trait author mark new methods as lower priority during resolution, so that existing extension methods win.]
- [TODO: Apply shadowing to concrete types as well, by preferring the most derived trait in scope.]

# Prior art

[TODO: describe how other languages with trait or interface inheritance resolve the same conflict, if the author wants this section. Do not describe them without sources.]

# Unresolved questions

1. Whether shadowing applies to associated types and constants, or only to methods.
2. Whether shadowing requires matching signatures.
3. Whether `T: Sub + Super` is ambiguous or resolves to `Sub`.
4. Whether to add a lint for shadowing, and where it fires.
5. Whether and how the concrete-type case of the motivating breakage is addressed.

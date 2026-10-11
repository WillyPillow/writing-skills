# RFC 2845: supertrait_item_shadowing

## Summary

This RFC changes item resolution for generics and trait objects. A trait bound no longer brings the items of its supertraits into scope when the subtrait defines an item with the same name.

## Motivation

A trait can have supertraits, and a subtrait can define an item with the same name as one in a supertrait. Today the two items can both be in scope when a function is generic over the subtrait. The compiler then reports an ambiguity at the call site, and the programmer has to write a qualified path to say which item is meant. [TODO: confirm this description of the current behavior against the compiler, and give the exact error message.]

An example shows the problem. Suppose the following:

```rust
trait Animal {
    fn name(&self) -> String;
}

trait Pet: Animal {
    fn name(&self) -> String;   // same name as in the supertrait
}

fn greet<T: Pet>(t: &T) {
    println!("{}", t.name());   // which `name`?
}
```

[TODO: the author to confirm that this program is an accurate instance of the case the RFC addresses, and to say what the compiler does with it today.]

Under the proposed rule, the call `t.name()` resolves to `Pet::name`, because `Pet` defines an item named `name` and so the bound `T: Pet` does not bring `Animal::name` into scope for this lookup. The programmer can still reach `Animal::name` with `Animal::name(t)`.

The RFC needs a motivating case from real code, and the abstract gives none. The likely driver is library evolution. Suppose a supertrait gains a method whose name matches a method already in a subtrait written by someone else. Before the change, every generic caller of the subtrait's method would become ambiguous and stop compiling. [TODO: the author to confirm that this library-evolution scenario is the motivation, and to supply a real case from the standard library or a named crate. The scenario here is a reconstruction by the drafting assistant from the title and the abstract.]

## Guide-level explanation

Shadowing is a familiar idea: a name defined in an inner scope hides a name from an outer one. The RFC applies the same idea to traits. A subtrait's item hides the same-named item of its supertrait when both would otherwise be found through a trait bound.

The rule has a limited reach. It applies when the bound is the subtrait, as in `T: Pet`. It does not apply when the function is bounded on both traits, as in `T: Pet + Animal`, because there the programmer has asked for both. [TODO: the author to confirm this, since it determines whether `T: Pet + Animal` is ambiguous or resolves to `Pet::name`.]

### Trait objects

The same rule applies to `dyn Pet`. A method call on a `dyn Pet` value resolves to `Pet::name`. [TODO: confirm, and state whether the vtable layout is affected. It should not be, because the change is in name resolution only.]

## Reference-level explanation

### The lookup rule

When the compiler resolves a method or associated item through a trait bound `B`, it collects items from `B` and from `B`'s supertraits. The change: if `B` defines an item with the name being looked up, the items from `B`'s supertraits with that name are not collected. [TODO: specify the order for supertraits several levels up. If `A: B: C`, and both `A` and `C` define `x`, then a lookup of `x` through the bound `A` finds only `A::x`. State what happens if only `B` and `C` define `x` and the bound is `A`: the intended answer is `B::x`, since `B` is the nearest definition, but the author must confirm.]

### Kinds of item

Traits can contain methods, associated constants and associated types. [TODO: state whether shadowing applies to all three kinds or only to some, and whether a method in the subtrait shadows a constant of the same name in the supertrait. Different kinds live in different namespaces in some cases and in one namespace in others, and the answer decides how many programs change behavior.]

### Unaffected cases

The rule does not change lookup on concrete types, where inherent items and trait items already follow their own priority. It does not change the explicit path forms `Animal::name(t)` and `<T as Animal>::name(t)`.

### Feature gating

[TODO: state whether the change is gated and, if so, the gate's name.]

## Drawbacks

1. The change can alter which function a program calls. A generic function that currently resolves `t.name()` unambiguously to the supertrait's method, for the reason that the subtrait defines no `name`, is unaffected. But consider a program where the subtrait adds a `name` method in a later version. The call then silently switches from `Animal::name` to `Pet::name`. Compilation succeeds and the behavior changes. This is the central risk of the proposal. A rule that turns an error into a silent change of meaning needs a justification, and this RFC does not yet give one. [TODO: the author to explain why a silent switch is acceptable, and what safeguards apply, for example a lint that warns when a subtrait item shadows a supertrait item.]
2. Reading a generic function now requires knowing the full set of items of the subtrait, to decide whether a name is shadowed. [TODO: author to respond.]

The first drawback is the main tension of the RFC. Resolving the ambiguity in favor of the subtrait helps library evolution, since new supertrait methods stop breaking subtrait users, and it hurts predictability, since additions to the subtrait silently redirect calls. The RFC should say which of these two it prefers and why. [TODO: author to state the preference and the reason.]

## Rationale and alternatives

The material does not say what the author considered. The following are suggestions for the author to evaluate, not rejected options.

- Keep the ambiguity error. This is the safest for predictability and leaves the library-evolution problem.
- Resolve in favor of the supertrait. This protects code written before the subtrait item existed and hides the subtrait's own item, which is surprising to its author.
- Resolve in favor of the subtrait, as proposed, with a warning-level lint whenever shadowing occurs.

[TODO: for each alternative that the author considered, give the specific goal that made it lose.]

Reversibility: the rule changes the meaning of existing syntax in a narrow set of programs. After it ships, programs may depend on the shadowing. Reversing it later would break them. This argues for a staged introduction. [TODO: author to give the staging.]

## Prior art

[TODO: the author to describe how other languages with trait or interface inheritance handle a same-named method in a subtype and a supertype, from sources the author provides. The RFC should not describe other languages from memory.]

## Unresolved questions

- Whether the rule covers associated constants and types.
- The treatment of multiple levels of supertraits.
- Whether a lint accompanies the rule.
- Whether a bound listing both traits resolves to the subtrait item.
- The feature gate and the stabilization plan.

## Migration

[TODO: the steps for a crate author, and whether a tool can find the calls whose resolution changes. A one-time compiler run in a mode that reports each changed resolution would let the author measure how many calls in a named set of crates are affected. The material has no such count, so the RFC cannot yet state that the change is rarely observable.]

# Rust RFC 2845: `supertrait_item_shadowing`

- Feature Name: `supertrait_item_shadowing`
- Start Date: 2020-07-14
- RFC PR: rust-lang/rfcs#2845
- Rust Issue: rust-lang/rust#89151

## Summary

This RFC changes how item names are resolved for generic parameters and trait objects when a trait bound brings supertraits into scope. Under the new rule, a trait bound does not bring the items of a supertrait into scope if the subtrait defines an item with the same name. The subtrait's own item takes precedence, and the supertrait's item is shadowed for that bound.

## Motivation

Traits can have supertraits, which are traits that a subtrait requires. When a generic parameter is bounded by a trait, the methods and associated items of its supertraits are also available on the parameter. This is convenient, but it can produce surprising results when a subtrait defines an item whose name matches one in a supertrait.

Consider a case where a subtrait provides a method with the same name as a method in its supertrait, but with a different signature or meaning. Under the current rules, a call to that name on a value bounded by the subtrait may resolve ambiguously, or it may pick the supertrait's version in some contexts and the subtrait's version in others. The result depends on details of resolution that are hard for readers to predict.

The problem is most visible in generic code, where the bound is written once and used many times. A reader who sees a bound on the subtrait expects the subtrait's methods to be the ones in scope. The supertrait's methods appear only because of the bound's implicit expansion, and their presence is not visible in the source.

The change makes the rule simpler to state. If the subtrait names an item, that item is what the bound provides. The supertrait's item is still available through explicit qualification, so no expressive power is lost.

## Guide-level explanation

Suppose a trait `Reader` has a supertrait `Source`, and `Source` defines a method called `len`. If `Reader` also defines a method called `len`, then a generic function bounded by `Reader` will see only the `Reader` version of `len` when it calls the method on its parameter.

Programmers who need the supertrait's version can write the call with explicit qualification, naming the trait that defines it. This makes the choice visible at the call site, and it avoids depending on the implicit resolution rules.

Trait objects follow the same rule. A trait object of type `dyn Reader` exposes the `Reader` version of `len`, and the supertrait version is reachable only through qualification.

The change does not affect code that calls methods on concrete types. The concrete type's methods are resolved through the usual rules, and this RFC is concerned only with the items brought into scope by bounds and trait objects.

## Reference-level explanation

When resolving a name on a type parameter or a trait object, the compiler considers the items of the traits named in the bounds. Under the current rules, it also considers the items of every supertrait, transitively. The proposal modifies this step. For each supertrait, the compiler checks whether a subtrait in the bound set defines an item with the same name. If one does, the supertrait's item is not added to the set of candidates for that bound.

The check applies transitively. If a supertrait's own supertrait defines a name that is shadowed by a subtrait, the same rule removes it from the candidates. The rule is applied to each bound separately, so that a type parameter with two bounds sees the union of the candidates from both, subject to shadowing within each.

Shadowing applies only to items with the same name and the same kind. A method is shadowed by a method, and an associated type is shadowed by an associated type. A method is not shadowed by an associated type of the same name.

Explicit qualification is never affected. A path that names the supertrait directly resolves to that trait's item regardless of shadowing.

The compiler emits a lint when shadowing changes the resolution of a name that would otherwise have been ambiguous. The lint is designed to help authors identify code whose behavior changes under the new rule, and it is expected to be a warning in the first edition in which the change applies.

## Drawbacks

The change alters the behavior of programs that compile today. Although the affected cases are expected to be rare, some code that relies on the supertrait's item being visible through a bound may stop compiling or may behave differently.

The rule adds a step to name resolution, which is a delicate part of the compiler. The implementation must be careful to keep the rule consistent across generic functions, trait objects, and associated type bounds.

The lint may be noisy in codebases that deliberately use the same names across a trait hierarchy, and those authors will need to qualify their calls.

## Rationale and alternatives

The main alternative is to keep the current rule and document the ambiguity. This leaves the surprise in place, and it asks every author to learn a rule that most readers do not know.

A second alternative is to make every ambiguous call an error. This would prevent silent changes in behavior, but it would make some currently valid programs invalid without offering a clear path to fix them other than qualification, which many authors would not know to use.

The chosen rule is simple to state, matches the intuition that a subtrait's own items are the ones a bound exposes, and retains explicit qualification as the escape hatch.

## Prior art

Object-oriented languages have long struggled with name collisions across inheritance hierarchies, and several have adopted rules that prefer the most derived definition. Rust's trait system differs from these languages in important ways, but the same intuition applies, and the proposal is consistent with the way many programmers already read trait hierarchies.

## Unresolved questions

The interaction with associated type bounds, where a bound on an associated type introduces its own supertraits, has not been fully worked out. The RFC proposes applying the same rule there, but the implementation should confirm that the result is consistent.

The wording of the lint and its severity in the transition period also need to be settled.

## Future possibilities

Once the rule is in place, tooling could show which items a bound exposes, and editors could highlight calls whose resolution depends on shadowing. The same analysis could support a future lint that warns about shadowed items that are never used, so that trait hierarchies can be simplified.

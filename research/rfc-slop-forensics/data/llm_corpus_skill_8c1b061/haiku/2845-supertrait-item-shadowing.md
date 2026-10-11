# Rust RFC 2845: supertrait_item_shadowing

## Summary

This RFC changes item resolution for generics and trait objects. Under the change, a trait bound does not bring the items of its supertraits into scope when the subtrait defines an item with the same name. The subtrait's own item takes precedence, and the supertrait's item with that name is shadowed. [TODO: confirm that shadowing applies to every kind of item, including associated types and constants, or only methods.]

## Motivation

A trait can have a supertrait, and a generic parameter bounded by the subtrait also gets the supertrait's items. When the subtrait defines an item with the same name as one in the supertrait, the bound brings both into scope. [TODO: give one concrete pair of traits with a shared item name, from code the author has seen, and the call that is affected.]

The obstacle is that the current resolution can make the call ambiguous, or can select the supertrait's item where the writer meant the subtrait's. [TODO: state what the current compiler does for the example above, with the compiler version tested, and the error or the wrong item that results.]

A subtrait author who adds an item with a new name can break code that calls a supertrait item of the same name in a generic context. [TODO: state whether the author has seen this breakage, and in which library.]

## Guide-Level Explanation

Under the proposed rule, a bound on a subtrait does not expose the supertrait's item that has the same name as one in the subtrait. A call on a generic value with that name resolves to the subtrait's item.

[TODO: give a short code example with two traits and one generic function, showing the call before and after the change. The example is not in the material.]

A trait object behaves the same way. [TODO: give an example of a trait object whose method call changes under the rule, and confirm this claim with the author.]

## Reference-Level Explanation

[TODO: specify the lookup rule. State the order in which the compiler searches the subtrait, the supertraits, and the bounds, and where shadowing takes effect.]

[TODO: specify the behavior for items reached through more than one supertrait path, and whether the rule applies at each level of a chain of supertraits.]

## Drawbacks

Code that relies on the supertrait's item in a generic context will now get the subtrait's item. Such code compiles today and may change meaning without an error. [TODO: give the author's estimate of how much code relies on this, with the method used to find it. Without an estimate, the claim should say that the change is possible, not that it is rare.]

The rule adds one more case that readers must know to understand a generic function. [TODO: state whether this cost has been weighed against the ambiguity it removes.]

## Rationale and Alternatives

The central choice is to let the more specific trait win. The reason is that the subtrait's author chose the name for the item in the subtrait, and a bound that names the subtrait should reflect that choice. [TODO: state the deciding reason in terms of a specific goal, and why that goal outweighs the cost above.]

An alternative is to keep both items in scope and require a qualified path at every call site. [TODO: state whether this was considered, and why it lost.]

Another alternative is to make the ambiguity a hard error. [TODO: state whether this was considered, and why it lost.]

## Compatibility and Rollout

[TODO: state whether the change is breaking under the edition system or whether it can be made behind a feature gate. The author has not stated a rollout plan in the material.]

## Unresolved Questions

[TODO: list the open questions. Candidates include whether the rule applies to associated types and constants, whether trait objects follow the same rule, and what the migration path is for code that changes meaning.]

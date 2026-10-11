# Rust RFC 2845: supertrait_item_shadowing

Status: [TODO: RFC status, tracking issue and date]

## Summary

This RFC changes item resolution for generics and trait objects. Under the change, a trait bound does not bring its supertraits' items into scope when the subtrait defines an item with the same name. The subtrait's own item is the one in scope through that bound.

The abstract describes the change, which implies the current rule brings supertrait items into scope even when the subtrait shadows them. [TODO: state the current rule and show it with a case from the author's material.]

## Motivation

[TODO: a case where two items with the same name, one in a subtrait and one in a supertrait, produce a wrong or surprising result under the current rule. The abstract names no case, and the motivation for a change of name resolution needs one.]

[TODO: whether the problem is a compile error, a silent change of meaning, or both. The abstract does not say which.]

## The rule before and after

Before the change, a bound on a subtrait brings the supertrait's items into scope along with its own. [TODO: confirm this description against the current rule, with a worked example.]

After the change, a bound on a subtrait that defines an item with name N does not bring the supertrait's item N into scope through that bound. The abstract covers generics and trait objects. [TODO: confirm whether the two behave the same way, since the abstract does not say.]

## Design

### The force

The force is a name clash between a subtrait and a supertrait that share an item name. The abstract does not describe how often this clash occurs or what it costs to resolve it by hand. [TODO: the clashes found in a named body of code, with the count and the method used.]

### The options

Keeping the current rule is one option. The abstract describes a change, so the current rule is implicitly the one the author rejected. [TODO: every other option the author considered, including the status quo, each in its strongest form, with the reason it lost.]

### The deciding reason

[TODO: the factor that decides the rule, and why it outweighs the others. Naming a goal is not enough. The author has to say why the chosen rule serves that goal better than the rejected ones.]

### The cost

Calls that resolve today through a bound to a supertrait's item may resolve differently, or fail to resolve, after the change. [TODO: which calls, from the material, and whether the author has checked that existing code still compiles.]

### Reversibility

A change to name resolution alters the meaning of code that compiles today. [TODO: whether the change can be reverted once shipped, and what a revert would break. The author should state whether the change counts as expensive to undo.]

## Compatibility

[TODO: the effect on existing crates. The abstract says nothing about this. State the crates examined and the result, and mark any claim that no existing code is affected as unsupported until such a check exists.]

## Scope

The rule applies to generics and to trait objects, and the abstract names both. The document treats them together because the abstract does. [TODO: each case, shown separately if the rules differ.]

## Open questions

[TODO: the unresolved points and the input each one needs. Candidates from this draft are the exact calls that change, the treatment of more than one supertrait with the same item, and the result of the compatibility check.]

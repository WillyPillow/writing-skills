# Rust RFC 1105: API evolution guidelines

- Feature Name: `api_evolution`
- Start Date: 2015-04-01
- Status: Accepted

## Summary

This RFC sets out guidelines for deciding whether a change to a stable public API is breaking under semantic versioning. The guidelines apply to the standard library and to crates published to the package registry. They identify a set of changes that cannot be made in a minor release, and they explain how certain language features could make other changes less disruptive. The RFC concerns only the public API surface. It does not decide questions about language features, lints, inference, command-line behavior, or the package manager.

The guidelines are not a claim that the standard library must avoid every non-breaking change. Many compatible changes still carry a risk of disrupting downstream code, for example through new inference ambiguities or name collisions. Those risks are real, but they are judgments made case by case. This RFC is concerned with the clear cases, the changes that are unambiguously breaking.

## Motivation

Semantic versioning only works if authors and users agree on what a breaking change is. Without a shared definition, a maintainer who publishes a minor release may break a downstream crate without intending to, and the downstream author has no way to know in advance. The result is either excessive caution, where authors refuse to release anything, or a loss of trust in the version numbers.

The standard library faces the same question at a larger scale. A change to a widely used type can affect thousands of crates. The project needs a checklist that contributors can apply during review, and crate authors need an equivalent they can apply to their own releases.

## Guide-level explanation

A change is breaking if a program that compiled and behaved correctly against the previous release may fail to compile or may behave differently against the new one. Several categories are easy to recognize.

Removing a public item is breaking. This includes functions, methods, types, traits, constants, modules, and re-exports. Renaming an item is the same as removing it and adding a new one, and so is also breaking.

Changing the signature of a public function is breaking. Adding a parameter, removing one, changing a parameter's type, or changing the return type all count. Changing a generic bound in a way that makes existing callers fail is breaking, even when the function is otherwise unchanged.

Adding a method to a public trait is breaking if the trait is implemented by downstream code, because those implementations no longer satisfy the trait. Adding an associated item to a trait with no default is breaking for the same reason.

Changing a public struct from having all public fields to having a private field is breaking, because code that constructed the struct with a literal will fail to compile. Adding a public field to a struct that was previously constructed only through functions is usually safe, but adding one to a struct that supports literal construction is breaking.

Adding a new trait implementation is usually non-breaking, but it can break code that relied on the absence of the implementation through method resolution or type inference. Removing a trait implementation is always breaking.

Several changes are non-breaking in the common case. Adding a new public item, adding a new inherent method to a type, and loosening a generic bound are usually safe. Improving performance without changing observable behavior is safe. Fixing a bug that was clearly unintended is generally safe, though the line between a bug and a behavior that users depend on can be hard to draw.

## Reference-level explanation

The guidelines are organized by the kind of item being changed. For functions, the rule is that the set of accepted calls must not shrink and the set of possible results must not change in a way that callers could observe. For types, the rule is that the set of values that can be constructed and the set of operations available on them must not shrink, except where the change is explicitly permitted by the type's documented invariants.

For traits, the rule is more restrictive, because traits are open to implementation by code outside the defining crate. Any change that invalidates an existing implementation is breaking. Default methods can be added without breaking implementers, provided that the new method's name does not collide with an existing method on a type that also implements the trait, since method resolution could then become ambiguous.

For modules and re-exports, the rule is that every path that was public must remain public. Moving an item to a new path and keeping a re-export at the old path is compatible. Making an item private that was public is breaking.

The RFC also discusses several language features that could reduce the pain of compatible changes. Attributes that mark an item as unstable or deprecated would allow maintainers to signal intent before a removal. Editions, which allow a crate to opt in to new syntax or behavior, could help absorb some changes that would otherwise require a major version. The RFC does not propose these features, but it notes that the guidelines should be revisited if they become available.

## Drawbacks

Any set of guidelines is a simplification. Some compatible changes will break real code in surprising ways, and some breaking-looking changes will turn out to be harmless. The guidelines therefore cannot replace judgment. Maintainers must still consider the likely users of an API and the cost of disruption.

The guidelines may also encourage maintainers to be overly conservative. An API that carries many historical mistakes may become difficult to improve, because every fix looks breaking. The RFC accepts this cost, because a predictable policy is worth more to the ecosystem than the freedom to fix everything at once.

## Rationale and alternatives

One alternative is to define breaking changes purely by reference to compilation. A change would be breaking if any previously compiling crate failed to compile. This is simple to state but fails to capture behavioral changes, and it would forbid many reasonable improvements. Another alternative is to rely entirely on tooling that detects breakage automatically. Such tools are valuable and are encouraged, but they cannot know the intent behind an API, so they cannot make the final judgment.

The chosen approach combines a clear list of unambiguous cases with a principle for the rest. It gives contributors something concrete to check and leaves room for judgment where judgment is needed.

## Prior art

Other ecosystems have adopted similar policies, usually with a longer list of exceptions. The experience of those ecosystems suggests that the most useful guidelines are the ones that name specific changes rather than stating general principles alone. This RFC follows that lesson by listing concrete categories.

## Unresolved questions

The RFC does not settle how to treat changes to the implementation of an API that users depend on indirectly, such as performance characteristics or the order of iteration in an unordered collection. It leaves these questions for future discussion and encourages documenting guarantees explicitly where they matter.

Questions about the interaction of these guidelines with type inference are also left open. Where a change could make inference fail in a previously compiling program, the project should weigh the likely frequency of such failures before deciding.

## Future possibilities

The guidelines should be revisited as tooling improves. A lint that flags likely breaking changes during review would reduce the burden on maintainers. Clearer documentation of stability guarantees, in the form of explicit promises attached to each public item, would make the guidelines easier to apply. Over time, the project may find that some currently breaking changes can be made compatible through language features that are not yet available.

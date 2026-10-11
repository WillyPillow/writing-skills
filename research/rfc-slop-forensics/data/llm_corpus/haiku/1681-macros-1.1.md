# Rust RFC 1681: `rustc_macros`

- Feature Name: `rustc_macros`
- Start Date: 2023-11-02
- Status: Proposed

## Summary

This RFC extracts a very small part of the procedural macro system and moves it into the compiler. The extracted part is just large enough to support basic features such as custom derive, and it is designed to have an eventually stable API. The RFC aims to avoid creating a maintenance burden for the compiler, and it deliberately does not attempt to provide every feature that a complete macro system would need. It is presented as an incremental step toward a more complete design, which is sometimes called "macros 2.0".

## Motivation

Procedural macros are one of the most useful features of Rust, but the current mechanism is largely an external convention. A procedural macro is a function that receives a token stream and returns a token stream, and the compiler runs it as a separate step. The interface between the compiler and the macro is not formally specified, and changes in the compiler can break macro crates in ways that are hard to predict.

Custom derive is the most common use of procedural macros. It allows a library to generate trait implementations for a user's types. Many widely used libraries depend on it, and the code they generate is often a substantial part of a crate's public surface. Because derive is so central, the interface for it deserves to be stable and well understood.

At the same time, a full redesign of macros is a large undertaking. Attempting to specify every feature at once risks delaying the parts that users need most. This RFC takes a narrower approach. It proposes a small, well-defined core that supports the common cases, and it leaves the rest of the design to later work.

## Guide-level explanation

A library author who writes a custom derive will see little change in day-to-day use. The attribute is written the same way, and the generated code is inserted in the same place. What changes is the interface between the macro and the compiler. The macro receives a description of the item it is applied to, and it returns the items it wants to add. The description is versioned, so that a macro built against one version can continue to work with a later compiler that supports the same version.

The RFC intentionally restricts what a macro may do. A macro in this minimal system may add items after the annotated item, and it may inspect the fields and variants of a struct or enum. It may not modify the annotated item, it may not introduce new attributes that affect other items, and it may not access arbitrary parts of the program. These restrictions keep the compiler's work predictable and make it easier to guarantee stable behavior.

## Reference-level explanation

The compiler exposes a small internal crate, provisionally called `rustc_macros`, that provides the data structures needed to describe a derive input. The data structures include the name of the item, its generic parameters, and the shape of its fields or variants. These structures are the only input the macro receives. The token stream of the original item is available only as a convenience for macros that need it, and its format is not guaranteed to be stable.

Output is also limited. A derive macro returns a list of items, each of which must be a trait implementation or a free function that the macro declares in the namespace of the annotated item. The compiler checks that the output does not name items outside that namespace, so that a derive cannot silently shadow user code.

The API is versioned with a single integer. The compiler accepts macros built against the current version and the one before it. This gives library authors time to migrate when the version changes. The compiler emits a diagnostic that names the version a macro expects when the version is not supported.

Errors produced by the macro are reported at the span given in the output, so that users see the location of their own code. The compiler does not attempt to map errors back through a token stream that the macro has rewritten, beyond the spans the macro supplies.

## Drawbacks

A minimal API will not satisfy every macro author. Some authors will need features that are excluded, and they will have to continue using workarounds. The versioning scheme requires the compiler team to maintain compatibility for at least two versions, which is a cost. There is also a risk that the minimal core becomes a permanent constraint, if the later design is slow to arrive.

## Rationale and alternatives

One alternative is to stabilize the entire current procedural macro interface. This would give macro authors the most freedom, but it would also freeze many details that are not yet well understood, and it would make the eventual design harder to change.

A second alternative is to leave procedural macros entirely outside the compiler, as they are now, and to document the interface informally. This preserves flexibility but does nothing to address the instability that users experience.

The approach taken here chooses a middle path. It stabilizes only what is needed for the most common use, and it keeps the rest of the mechanism free to evolve.

## Prior art

Other languages have separated a small set of stable macro features from a larger experimental system. The experience of those languages suggests that a clear boundary helps users, because they know which features they can depend on.

## Unresolved questions

- Which derive inputs should be included in the first version, and which should wait for a later version?
- Should the versioning scheme allow a macro to declare a range of supported versions, or only a single version?
- How should the compiler report the cost of a derive that generates a large amount of code?

## Future possibilities

The minimal core is intended to be extended. Later versions could allow macros to define new attributes, to inspect more of the program, and to produce diagnostics with richer structure. Each extension would be proposed separately, and it would be judged on its own merits. The goal is a macro system that is both expressive and predictable, reached through a sequence of stable steps rather than a single large change.

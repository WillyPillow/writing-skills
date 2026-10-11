# Rust RFC 2603: Rust symbol name mangling v0

## Summary

This RFC proposes a new mangling scheme for the symbol names that the Rust compiler generates. The existing scheme grew over time without a clear direction. The new scheme is consistent and depends less on compiler internals. It also stores information in the symbol name that a tool can decode again, which helps users of external tools that read Rust symbol names.

At this point the new scheme would not be part of the language specification or of a specification of a stable Rust ABI. The scheme is designed to be stable and extensible, and in the future it could become part of both. [TODO: the abstract available for this draft ends mid-sentence ("but for the time being it would still ..."). The author must complete the statement of what the scheme's status is for now.]

## Motivation

The compiler gives each function and static item a name in the object file, called a symbol. Debuggers, profilers, linkers, backtrace printers and binary size tools read these names. A symbol name has to be unique, because the linker identifies items by it, and it has to use a restricted set of characters, because object file formats and linkers limit what a name may contain. Mangling is the encoding that turns a Rust path, such as a module path with a type and a method, into a name that meets both constraints.

The abstract identifies three weaknesses of the current scheme.

1. It lacks a clear direction. The scheme was extended as needs arose, so its rules are the sum of past decisions, not a design. A reader cannot derive the rules from a principle.
2. It depends on compiler internals. A name produced by the scheme can change when an internal detail of the compiler changes, even if the program is the same. [TODO: the author should give the concrete internal details that leak into names today.]
3. It is not decodable in full. A tool that receives a symbol cannot recover everything that the compiler knew when it produced the name. [TODO: the author should say which information is lost today. A plausible instance is a hash suffix that distinguishes items but does not say what differs between them. This is a suggestion, not a statement from the material.]

The third weakness is the one the abstract ties to users. An external tool that wants to show a readable name, or to group symbols by crate or by generic instantiation, can only do what the name allows. If the name keeps information in a decodable form, every such tool improves without per-tool heuristics.

An example of a current symbol helps to show what is at stake. A function in the standard library might appear as a name starting with `_ZN`, followed by length-prefixed path segments, followed by a hash. [TODO: replace this description with one real symbol from the current compiler and its demangled form. The draft does not include one because none was supplied.]

## Guide-level explanation

For a user of a debugger or profiler, the change is that Rust symbols become readable by tools that implement the new scheme. A name decodes to the path of the item, to the generic arguments of an instantiation, and to the other information the scheme stores. [TODO: list the information the scheme stores. The abstract says only that "the information it stores in symbol names can be decoded again".]

For a user who does not inspect symbols, nothing changes in behaviour. The program links and runs as before. [TODO: confirm this claim against the proposed implementation. The draft has no tests or measurements.]

The scheme is opt-in at first. [TODO: the author should state how the user selects the scheme, for example by a compiler flag, and the plan for making it the default. The abstract implies that the old scheme continues for now but does not say so.]

## Reference-level explanation

The reference-level section has to contain the grammar of the mangled name. [TODO: the grammar. The abstract says only that the scheme is consistent. The author must supply the productions, the escape rules and the treatment of each of the following.]

- Crate identity, including the disambiguation of two crates that have the same name.
- Nested items, including modules, types, traits and impl blocks.
- Generic arguments, including types, lifetimes and constants.
- Closures and other items that have no name in the source.
- Characters outside the set that object formats allow, such as non-ASCII identifiers.

A design question that deserves the most space is the tension between decodability and length. A name that stores everything needed to decode it back to the full path is longer than a name that stores a hash. Long names increase object file size and the time linkers spend on them. [TODO: the author should say how the scheme resolves the tension, with numbers on the length of real symbols under the old and the new scheme. Without them, the cost of decodability is not stated.] A reviewer who disagrees with the RFC will most likely dispute this trade-off, so the document must give the reasons and the measurements.

The scheme's consistency requires a rule for each item kind, and the rule must not mention compiler data structures. The statement "depends less on compiler internals" is checkable in this way: every input to the encoding is a property of the program as seen by the user, such as a path or a type, and none is an internal identifier. [TODO: the author should confirm that this is how the RFC defines independence from internals, or give the actual definition.]

## Stability and extensibility

The abstract says the scheme is designed to be stable and extensible. Stability means that a program compiled twice with the same source and compiler produces the same names, and that later compiler versions do not change the names for the same items. Extensibility means that later versions of the scheme can add information without breaking decoders written for the first version. [TODO: the author should state the mechanism, such as a version marker in the name. A version marker in the prefix is a common approach, but the material does not say that this RFC uses one.]

Stability has a cost that is hard to reverse. Once external tools decode the format, changing the format breaks them. For this reason the abstract states that the scheme is not yet part of the language specification or of a stable ABI. Tools can use the scheme, and the project can still change it if experience shows a mistake. [TODO: confirm. The truncated abstract suggests this reading but does not complete it.]

## Drawbacks

- Two schemes exist side by side while the transition lasts. Tools have to support both, or support only the new one and lose the old names. [TODO: the author should give the transition plan.]
- Some tools that parse the old format will fail on the new one. [TODO: the author should list known tools and their status.]
- A decodable scheme exposes more structure of the program in the binary than a hash does. If a project cares about concealing the names of its internals, the new scheme gives it less room. [TODO: the author should say whether this is a concern for the project and whether any option exists to reduce the information.]

## Rationale and alternatives

The case for a new scheme is that the problems in Motivation come from the design of the old scheme and cannot be fixed by patching it. [TODO: the author should say why patching was ruled out. This reasoning is the center of the case, and the draft cannot invent it.]

Alternatives, marked as suggestions for the author to evaluate:

- Keep the current scheme and document it. This gives a stable reference at low cost. It fixes the consistency and internals problems only on paper.
- Adopt an existing scheme from another language, such as the one C++ compilers use for the `_ZN` prefix. It reuses tool support. It was not designed for Rust's generics, lifetimes and constants.

## Prior art

[TODO: citations for mangling schemes in C++, Swift and other languages, which the author may want to compare. None were supplied, so this draft makes no claim about them.]

## Unresolved questions

- The complete grammar. [TODO]
- The mechanism for extending the scheme. [TODO]
- The plan and schedule for making the scheme the default. [TODO]
- The status of the scheme with respect to a stable ABI, as completed from the truncated abstract. [TODO]

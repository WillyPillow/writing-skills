# Rust RFC 2603: A new symbol name mangling scheme

## Summary

This RFC proposes a new mangling scheme for the symbol names that the Rust compiler generates. The existing scheme grew over time without a clear direction. The new scheme is consistent, depends less on compiler internals, and stores information in the symbol name in a form that tools can decode again. At this point the scheme is not part of the language specification and not part of a stable Rust ABI. It is designed to be stable and extensible, so it could become part of both later, but for now the compiler would still be free to change it. [TODO: the abstract is cut off after "for the time being it would still"; the author should complete this sentence and state exactly what freedom the compiler keeps.]

## Motivation

A symbol name is the string by which a linker, a debugger, a profiler or a backtrace printer identifies a function or static. A compiler creates these names from the item's path in the source program, such as `std::collections::HashMap::insert`. The name needs more than the path. Two generic instantiations of one function, a closure inside a function and two items with the same name in different crates must all get different symbols.

The abstract names three problems with the current scheme.

1. It has grown over time without a clear direction, so its rules are hard to describe as a whole.
2. It depends on compiler internals. A symbol name can change because an internal detail changed, not because the program changed.
3. The information in a name cannot be decoded again, which limits external tools that work with Rust symbol names.

The third problem is the most concrete. A tool that sees the mangled name `_ZN4core3fmt5write17h...E` and wants to show `core::fmt::write` has to guess where the human-readable path ends and the added part begins. Where the name omits information, the tool cannot show it at all. For example, a name may say that a function is generic but not what it was instantiated with. [TODO: the material gives no example of a specific tool that fails today or the information that it cannot recover. Add one.]

## Guide-level explanation

A mangled name under the new scheme starts with a fixed prefix that identifies the scheme and its version. [TODO: the author should give the prefix and say how it differs from the prefix of the existing scheme.] After the prefix comes an encoding of the item's path, then optional parts that distinguish instances of the item. A decoder reads the encoding from left to right without needing information from outside the symbol.

Two properties describe how the scheme behaves, and a reader should expect the name to have both.

First, the name is a function of the item as the program sees it. The same item compiled by two versions of the compiler gets the same name, unless the scheme itself changed. This is what "depends less on compiler internals" means. [TODO: the abstract states this goal but gives no measured or enumerated list of the internals the old scheme depends on. Add one if the author has it.]

Second, the name can be decoded again. A tool can turn a symbol back into a path and a set of generic arguments, without the compiler's help.

For users, the visible effect is in tools. A debugger or profiler that understands the new scheme shows readable names for generic functions. A tool that does not understand it shows the raw string, as it does today for a name it cannot decode.

## Reference-level explanation

The grammar of the scheme is the main content of this section.

[TODO: the author's material contains no grammar, no list of productions and no examples. The grammar is the core of the RFC and has to come from the author. The outline below states what the grammar must cover; it does not describe any particular encoding.]

The grammar should cover:

- the path of the item, including how crates are identified and how disambiguation is encoded for items that share a name;
- generic arguments, including types, lifetimes where they matter for the name, and constants;
- closures and other items without a source name;
- a way to compress repeated substrings, since paths often repeat the same crate and module names, if the scheme includes compression;
- the character set. Linkers on different platforms accept different characters in symbols, so the set must be one that all supported targets accept. [TODO: state the chosen character set and the targets checked.]

### Stability

The abstract says the scheme is "designed to be stable and extensible." These two claims call for two different kinds of evidence. For stability, the RFC needs to say which parts of the encoding are fixed and which inputs to the name are allowed to change. For extensibility, it needs to say how a later version adds a construct, for example by reserving a version marker. [TODO: the author should supply both.]

Until the scheme is made part of the language specification or the ABI, the compiler may change it. Tools that decode it should therefore tolerate a version marker they do not know. [TODO: confirm.]

### Relationship to the existing scheme

The old and new schemes cannot both be the default. [TODO: the author should say how the switch happens: a flag, a release, or a period in which both are available.] A tool that parses names must handle the old scheme for as long as code compiled with it is in use.

## Drawbacks

Every tool that reads Rust symbols has to learn a second scheme. This includes debuggers, profilers, binary size analyzers and crash reporters. The abstract says decodability helps these tools, but a new format also costs them work. The material does not say which tools were consulted. [TODO: list the tools and what they said.]

Symbols change across the change in default. Anyone who stored symbol names from a previous build, for example in symbolication databases or allowlists, finds them invalid for newer builds.

Name length is a possible cost. A scheme that stores more information in the name can produce longer names, and symbol table size affects binary size and link time. The material gives no measurement. [TODO: add the size comparison for a real crate, if the author has one.]

## Rationale and alternatives

The abstract gives the reasons for a new scheme: consistency, independence from compiler internals, and decodability. The question a reviewer will ask is why the existing scheme could not be cleaned up in place, which would avoid a second format.

[TODO: ask the author why an in-place cleanup was rejected. The abstract says the existing scheme "has grown over time without a clear direction", which suggests that its structure resists cleanup, but that is an inference and not a stated reason.]

Other alternatives to ask about:

- adopting an existing mangling scheme from another language, such as the one used by C++ compilers. [TODO: ask whether this was considered and what ruled it out.]
- a scheme that is not decodable but is simpler. [TODO: ask.]

Reversibility: names appear in binaries that other people keep and in tools that other people write, so a format that tools have started to depend on is costly to change. This is a reason to hold off on putting the scheme into the specification or the ABI. It is also a reason for the version marker.

## Prior art

[TODO: the author's material cites none. Name the schemes this one is compared with, and say how this scheme differs from each.]

## Unresolved questions

- The complete grammar and the character set.
- The mechanism and timing of the switch.
- How tools discover that a symbol uses the new scheme.
- Whether the scheme should be specified before it is stabilized as an ABI.

## Future possibilities

If the scheme becomes part of the language specification, other implementations of Rust could produce compatible symbols. If it becomes part of a stable ABI, separately compiled Rust libraries could link to each other across compiler versions. Both require decisions that this RFC does not make.

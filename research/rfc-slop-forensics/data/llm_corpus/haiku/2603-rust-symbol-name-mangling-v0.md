# RFC 2603: Rust Symbol Name Mangling, Version 0

- Feature Name: `symbol_mangling_v0`
- Start Date: 2018-01-09
- Tracking Issue: (none yet)
- Status: Proposed

## Summary

This RFC proposes a new mangling scheme that describes the symbol names the Rust compiler generates for functions, statics, and other items. The scheme is called version 0, and it is intended to replace the existing scheme, which has grown over time without a single governing design. The new scheme is consistent, depends less on the internal representation of the compiler, and encodes enough information in each symbol name that the name can be decoded again. This last property is useful to debuggers, profilers, and other tools that process Rust binaries.

The proposal is limited in scope. It does not make the mangling scheme part of the language specification, and it does not define a stable application binary interface for Rust. In the future, the scheme could become part of either or both, and it is designed to be stable and extensible for that purpose. For now, however, the compiler remains free to change the names it produces, and tools should not depend on exact symbol strings across compiler versions.

## Motivation

A symbol name is the string that identifies a function or other item in an object file. When the linker combines object files, it matches references to definitions by comparing these strings. Because Rust allows items with the same name to exist in different modules, generics, and crates, the compiler must encode enough information in each name to keep them distinct. This encoding is called mangling.

The existing scheme in the Rust compiler was designed in pieces. It includes information that depends on compiler internals, such as the particular numbering of definitions within a crate. This makes names hard to reproduce outside the compiler, and changes to the compiler can alter names even when the program has not changed. Names also contain characters that are awkward on some platforms, and the format is hard to parse without knowing the details of the compiler that produced it.

These problems matter in practice. A profiler that wants to show readable function names must either demangle with a heuristic or depend on the compiler's own demangler. A linker script that wants to match a family of functions must write patterns against an unstable format. A debugger must reconstruct paths from fragments that are not consistently formed. A consistent scheme with a clear grammar addresses all of these concerns.

## Guide-level explanation

Under the proposed scheme, every symbol begins with a fixed prefix that identifies the version. The remainder of the name is a sequence of components that describe the item. Each component is either a path element, such as a module or type name, a generic argument, or a reference to a crate. Components are encoded in a way that makes the boundaries between them unambiguous.

For example, a free function `parse` in the module `config` of the crate `settings` might be encoded in a form that a demangler can read back as `settings::config::parse`. The same demangler applied to a generic instance would also recover the type arguments. The exact bytes of the encoding are described in the reference section and are not intended to be read by programmers in day-to-day work.

Programmers normally do not need to know the scheme at all. The compiler continues to produce names that the linker can use, and the standard tools for inspecting binaries will demangle them when asked. The scheme matters most to people who write tools, and to people who need to predict or match symbol names for special purposes such as dynamic loading.

## Reference-level explanation

A mangled name consists of the prefix `_R`, followed by a version marker, followed by one or more encoded items. The grammar is given in full in an appendix. In brief, the grammar has the following parts:

- Paths name items by listing the crate and then each nested module, type, or function in order. Each path element is written as a length-prefixed identifier, which removes the need for escape sequences in most cases.
- Generic arguments are written after the path they apply to. Types, constants, and lifetimes each have their own encoding.
- Backreferences allow a repeated sub-expression to be written once and referred to later. Each backreference names a position in the symbol, so decoding does not depend on any table kept by the compiler.
- Crate identifiers are based on the crate name and a disambiguator that distinguishes different builds of the same crate. The disambiguator is derived from the crate's metadata and does not depend on the order in which the compiler processed the crate.

The scheme avoids any encoding that depends on the numeric identifiers assigned by the compiler to definitions. Instead, names are derived from paths and from the types of the items. Where two items would otherwise share a name, a disambiguator is added that is computed from a stable property of the item, such as its position in the source.

Symbols for closures and for items generated by macros are formed using the same rules, with additional path elements that identify the closure or the expansion. The exact elements are specified in the appendix.

Demangling is defined as the inverse of mangling. A conforming demangler reads a symbol and reconstructs a human-readable path with its generic arguments. It must reject malformed input rather than guess.

## Drawbacks

A new scheme means a period of transition in which two schemes are in use, and tools must support both during that time. The compiler must maintain the code for the old scheme as long as it is still in use, which adds work. Some users may find that names become longer in certain cases, which can matter when binaries are constrained by symbol table size.

There is also a risk that a scheme designed for tools becomes a de facto specification before it is ready. The proposal addresses this by stating clearly that the scheme is not yet part of the language or ABI, but the risk remains that users will depend on it anyway.

## Rationale and alternatives

One alternative is to keep the existing scheme and document it. This would preserve compatibility but would not address the inconsistencies or the dependence on compiler internals. Another alternative is to adopt a scheme used by another language. This was considered, but no existing scheme handled Rust's generics, lifetimes, and trait-based dispatch without significant adaptation. The proposed scheme borrows ideas from earlier designs, such as length-prefixed identifiers and backreferences, while being specific to Rust.

Making the scheme independent of compiler internals is the central design choice. It means that a symbol can be produced and read by a tool that knows nothing about the compiler's data structures. This property is the main reason the scheme is better suited to external tooling than the current one.

## Prior art

Several languages have mangling schemes with length-prefixed identifiers and backreferences, and the Itanium C++ ABI is a familiar example. The experience of those communities shows that a clear grammar makes demangling reliable and that compact encodings reduce the size of symbol tables. The Rust scheme takes these lessons but makes different choices where Rust's features require them.

## Unresolved questions

- The precise treatment of very long names, and whether the compiler should shorten them with a hash when they exceed a platform limit.
- How the disambiguator should behave for crates built in unusual configurations, such as those produced by build systems that do not record stable metadata.
- Whether the appendix grammar should be published as a separate document with its own versioning.

## Future possibilities

If the scheme is later adopted as part of a stable ABI, the version marker allows a new scheme to be introduced without breaking existing tools. The grammar leaves room for additional encodings, such as those needed by future language features, without requiring changes to the parts already defined. Tools that implement the scheme may also be extended to provide richer information, such as the source location of an item, provided that this information is recovered from debug data rather than from the symbol name itself.

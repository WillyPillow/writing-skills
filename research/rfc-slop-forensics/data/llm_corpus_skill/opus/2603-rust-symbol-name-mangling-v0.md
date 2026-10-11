# RFC 2603: Rust symbol name mangling, version 0

- Feature Name: `symbol_name_mangling_v0`
- Start Date: [TODO: date]
- RFC PR: [TODO: link]
- Rust Issue: [TODO: link]

## Summary

This RFC specifies a new scheme for the symbol names that the Rust compiler generates, called version 0. Version 0 is defined by a grammar rather than by the compiler's internal data structures, and every symbol name it produces can be decoded back into the Rust path and generic arguments it stands for. This RFC does not make the scheme part of the language specification, or of a stable Rust ABI. The scheme is designed so that it could become part of either later. Until then, the compiler may change it.

## Context

A symbol name identifies a function or static to the linker, and to tools that read compiled code: debuggers, profilers, crash reporters, and disassemblers. These tools show the symbol name to a person, so they decode it back into the source-level name. Decoding a symbol name is called demangling.

The current scheme encodes the path of an item in a form that existing C++ demanglers partially understand. It appends a hash, which the compiler computes from internal data, to keep names unique. Two properties of the current scheme matter for this RFC:

1. Generic arguments are not encoded in a decodable form. Two instances of the same generic function, such as `Vec<u8>::push` and `Vec<String>::push`, differ only in the hash. A profiler therefore shows both as the same function with different hash suffixes, and the person reading the profile cannot tell which instance is which.
2. The hash depends on compiler internals. A tool cannot compute the symbol name of an item from its source-level description; it can only look the name up.

The scheme has also grown over time without a stated design. [TODO: author to give concrete examples of inconsistencies in the current scheme, such as items that are encoded differently for no documented reason, with the symbol names that show it.]

## Goals and non-goals

Goals:

- Decodability: from a version 0 symbol name, a demangler can recover the full path of the item, including the generic arguments of every component, without access to the compiler or the crate's metadata.
- Uniqueness: two distinct items, or two distinct instances of a generic item, never get the same symbol name within one linked program.
- Independence from compiler internals: the symbol name of an item is determined by the grammar and by information a tool can obtain from the source and the crate identity. [TODO: author to state precisely which inputs are allowed, since crate identity itself may involve a compiler-computed value.]
- A restricted character set: symbol names use only characters that linkers and object file formats on supported platforms accept. [TODO: author to state the character set and confirm it is accepted on each tier 1 platform.]
- Distinguishability: a demangler can tell from the first characters whether a symbol uses version 0, the current scheme, or another language's scheme.

Non-goals:

- A stable ABI. Version 0 names are not a promise that code compiled by different compiler versions can be linked together.
- Part of the language specification. A conforming compiler need not use version 0.
- Compatibility with C++ demanglers. The current scheme is partly readable by them; version 0 does not aim to be. This is a cost, discussed below.

## Design

The scheme has a grammar, given in full in the reference section. [TODO: the full grammar. This draft discusses the decisions the grammar embodies, not its productions.] A version 0 symbol name consists of a fixed prefix, an encoded path, and optionally an encoded instantiating crate. The path is a sequence of components. Each component is a crate root, a nested name (a module, type, function, or closure), an inherent or trait impl, or a list of generic arguments applied to the preceding path.

### Decision: a new prefix

Each version 0 symbol starts with a prefix that no other scheme in use produces. [TODO: author to give the prefix and confirm it does not collide with any other language's mangling.] The force is the distinguishability goal. During the transition, one binary can contain symbols from both Rust schemes, and from C and C++. A demangler must pick the right decoder without guessing. The cost is that tools which already recognize the current Rust scheme, because it looks like C++, will not recognize version 0 at all until they add support. This cost is discussed under rollout.

### Decision: encode generic arguments in the name

Version 0 encodes the generic arguments of every path component, including types, lifetimes where relevant, and const arguments. The force is the decodability goal and the profiler case in the context section. The cost is length. A deeply nested generic instance produces a long name, because its arguments are themselves paths that can have generic arguments.

This is the central tension of the design: the more information a symbol name carries, the longer it is. Symbol names occupy space in object files, in debug information, and in the dynamic symbol tables of shared libraries. They are also processed by the linker. [TODO: author to give measurements, such as total symbol-name bytes for a sample of crates under the current scheme and under version 0, and the effect on link time and binary size.]

### Decision: back-references

To limit length, a repeated part of a name can be replaced by a reference to its earlier occurrence in the same symbol. For example, `HashMap<String, Vec<String>>` contains the path of `String` twice. With a back-reference, the second occurrence takes the space of a short offset rather than a full path.

Back-references make the encoder and the decoder more complicated. The decoder must keep the symbol text available and must guard against references that point forward or loop. [TODO: author to state the size reduction back-references give on the measured sample. Without that number, the reader cannot judge whether the added complexity pays for itself.] The alternative of no compression is a suggestion for the author to evaluate, not a recorded alternative.

### Decision: how uniqueness is ensured

Encoding generic arguments removes the need for a hash in most cases, because the encoded name itself identifies the instance. Two cases still need extra data:

1. Two crates with the same name can be linked into one program, for example two versions of the same library. The crate root component therefore carries a disambiguator alongside the crate name. [TODO: author to specify how the disambiguator is computed and whether it is stable across compiler versions.]
2. Some items have no name, such as closures, or have names that can repeat within one scope. These items get a numeric index within their parent. [TODO: author to specify how the index is assigned, so that two compilations of the same source produce the same index.]

### Decision: identifiers outside ASCII

Rust identifiers may contain non-ASCII characters. [TODO: confirm the status of non-ASCII identifiers at the time of this RFC.] The restricted character set goal rules out putting them into symbol names directly. Version 0 encodes such identifiers into the permitted character set with a reversible encoding. [TODO: author to name the encoding and the reason for choosing it.]

## Rollout

1. Implement version 0 in the compiler behind an option that selects the mangling scheme. The current scheme stays the default.
2. Provide a reference demangler as a library that tools can use, and a specification precise enough for tools to write their own. [TODO: author to say which tools need support first, and whether their maintainers have been contacted.]
3. Once the most widely used tools support version 0, propose making it the default in a separate decision.

Rollback before step 3 is the removal of the option. After version 0 becomes the default, the binaries already built contain version 0 names, and tools must keep decoding them indefinitely. The grammar is therefore the decision that is expensive to reverse. That is why this RFC asks reviewers to look at the grammar rather than at the compiler implementation.

## Drawbacks

Tools that today partly demangle Rust symbols as C++ will show version 0 symbols as raw text until they add a decoder. Symbol names will likely be longer than today for generic code, by an amount not yet measured. Specifying the scheme publicly invites tools to depend on it, which makes later changes harder even though this RFC does not promise stability.

## Rationale and alternatives

[TODO: author to list the alternatives actually considered. Two suggestions for the author to evaluate, not recorded alternatives: extending the current C++-like scheme to encode generic arguments, which would keep partial support in existing tools; and keeping hashed names while emitting a separate table that maps hashes to full paths, which would keep names short but makes decoding depend on that table being present.]

## Unresolved questions

- The full grammar.
- The prefix.
- The computation of crate disambiguators and closure indices.
- The encoding of non-ASCII identifiers.
- Whether version 0 should encode anything about the calling convention or the item's type signature. [TODO: author to decide.]

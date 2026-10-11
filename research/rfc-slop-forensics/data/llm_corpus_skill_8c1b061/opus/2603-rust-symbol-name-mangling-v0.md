# RFC 2603: A new symbol mangling scheme for Rust

- Feature name: `symbol_mangling_v0`
- Start date: [TODO: date]
- RFC PR: [TODO: link]
- Tracking issue: [TODO: link]

## Summary

This RFC defines a new scheme for the symbol names that the Rust compiler emits into object files. The current scheme grew over time without a stated design. The new one encodes every item the same way, depends less on compiler internals, and stores information that a demangler can decode back into a readable Rust path, including generic arguments.

The scheme is not part of the language specification or of a stable Rust ABI. It is designed so that it could become part of both later, but for now the compiler may change it, and code must not rely on the exact form of a symbol name.

## Motivation

Tools outside the compiler read symbol names: debuggers, profilers, crash reporters, linkers in their error messages, and `nm`-style utilities. For those tools, the symbol name is often the only link from a machine address back to the source.

The current scheme serves them poorly in three ways.

First, it loses information. A generic function is mangled as its path followed by a hash. Two instances of `Vec<T>::push`, one for `u8` and one for `String`, get the same readable path and differ only in the hash. A profile that shows time spent in `alloc::vec::Vec<T>::push::h3a1f...` does not say which instance is hot.

Second, the hash depends on compiler internals. [TODO: describe what goes into the current hash and give an example where a compiler change, with no source change, changes a symbol name.] Because the hash cannot be decoded, a tool cannot recover anything from it, and two builds cannot be compared by symbol name.

Third, the scheme is not consistent. [TODO: list the concrete cases where the current scheme encodes items differently, for example trait implementations, closures, or items in blocks, with an example of each.] A demangler must special-case each one, and some cannot be told apart.

The new scheme addresses each point: generic arguments are encoded in the name, the name is computed from the source-level identity of the item rather than from internal IDs, and one grammar covers all items.

## Requirements

The design is driven by the following constraints.

1. Symbols must be accepted by the linkers, assemblers and object formats that Rust targets. The scheme therefore uses only the characters `A-Z`, `a-z`, `0-9` and `_`. [TODO: confirm that this set is accepted by every supported target's toolchain, or name the ones where it is not.]
2. Distinct items must get distinct symbols. Two generic instances that differ in any argument must not collide.
3. A demangler must be able to decode the full path and generic arguments without access to the compiler or the crate's metadata.
4. Symbol names must not change when compiler internals change and the source does not. They may still change when the crate's identity changes, for example its version.
5. Symbol length should stay reasonable for deeply generic code. [TODO: state a target, or the sizes measured on real crates.]

## Design overview

A symbol starts with the prefix `_R`. The prefix lets tools tell new-scheme symbols from legacy ones, which start with `_ZN`, and from C++ symbols, which also start with `_Z`. Starting with an underscore and an uppercase letter also places the symbol in the namespace that C reserves for implementations, so it cannot clash with a C identifier.

After the prefix comes a path. A path is built from a small set of node types, each introduced by one uppercase letter:

- a crate root, with the crate's name and a disambiguator derived from its identity;
- a nested item, with the parent path, a namespace tag, and the item's name;
- an inherent impl, with the parent path and the self type;
- a trait impl, with the self type and the trait path;
- a generic instantiation, with a path and a list of generic arguments.

Identifiers are written with a decimal length prefix followed by the bytes, as in `5inner`. The length prefix lets the demangler find the end of each identifier without a separator, so identifiers may contain digits and underscores.

Types are encoded with one lowercase letter for each primitive type, and with uppercase letters for compound types such as references, raw pointers, arrays, tuples and function pointers. A path that names an ADT can appear wherever a type is expected.

As an example, the instance of `Vec<u8>::push` in the standard library would be written as a generic instantiation of a nested path `alloc::vec::...::push` with the argument `u8` encoded as one letter. [TODO: add a complete worked symbol and its demangled form, checked against the implementation.]

## Decisions

### Decodable names instead of a hash

The largest change is that a symbol now encodes the generic arguments in full, where the legacy scheme used a hash. This meets requirement 3: a profiler can show `Vec<u8>::push` and `Vec<String>::push` as separate entries.

The cost is length. A type like `HashMap<String, Vec<Option<Box<dyn Fn(u32) -> u32>>>>` produces a long symbol, and deeply nested iterator adaptors produce much longer ones. Long symbols increase the size of object files and of the symbol tables in binaries that keep them. [TODO: measure symbol table size for a set of crates under both schemes.]

The design limits the length with backreferences. Any path or type that already appeared in the symbol can be replaced by a reference to its position, written as `B` followed by the offset. A type that appears several times in a signature is therefore written in full only once. Backreferences make the demangler slightly more complex, since it must keep the positions of earlier nodes, and they stop a repeated type from multiplying the length. [TODO: measure how much backreferences shorten symbols on real crates.]

[TODO: Was a hybrid considered, for example a readable path with a hash only for the generic arguments? If so, record why full encoding won.]

### Crate disambiguator

Two different crates with the same name can be linked into one binary, for example two versions of the same dependency. The crate root node therefore carries a disambiguator. It is computed from the crate's identity as the build system defines it, not from compiler state, which meets requirement 4. A demangler shows it only when asked, since in most output the crate name is enough.

### Non-ASCII identifiers

Rust allows identifiers outside ASCII, but requirement 1 limits symbols to ASCII. Identifiers that contain non-ASCII characters are encoded with Punycode, and the length prefix is marked with a `u` so the demangler knows to decode it. Punycode was chosen because it is an existing standard with existing decoders. [TODO: confirm this was the reason, and whether other encodings were compared.]

### Constants in generic arguments

Const generics are not stable at the time of writing, but the grammar reserves an encoding for constant arguments, with a type tag and a value. Reserving it now means the format does not need a new version when const generics arrive. [TODO: confirm which constant types the grammar supports.]

## Rollout

The compiler gains an option, `-C symbol-mangling-version`, with the values `legacy` and `v0`. The default stays `legacy`. A later decision, outside this RFC, can change the default.

Tools need a demangler before the new scheme is useful to them. The plan is to provide a reference demangler in the `rustc-demangle` crate and to contribute support to the tools that users rely on most. [TODO: list the target tools, for example GDB, LLDB, binutils, perf and Valgrind, and the state of support in each.]

Until those tools support the format, a user who turns it on sees raw `_R` symbols in their debugger and profiler. That is why the default does not change here.

## Drawbacks

Symbols are longer, by an amount to be measured.

Adding a second scheme means demanglers must handle both for as long as old binaries exist.

Once external tools ship a decoder, changing the grammar becomes expensive. Every incompatible change requires updates in tools that the Rust project does not control. The grammar should be reviewed with that in mind, more carefully than an internal compiler format.

## Unresolved questions

- Whether the scheme should become the default, and on what conditions.
- Whether the encoding of closures and other anonymous items needs to be stable across compiler versions.
- How much symbol size grows in practice, and whether the backreference rules need changes after measurement.

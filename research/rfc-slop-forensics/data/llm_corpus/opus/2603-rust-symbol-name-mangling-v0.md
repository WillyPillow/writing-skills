- Feature Name: `symbol_name_mangling_v0`
- Start Date: 2018-11-27
- RFC PR: [rust-lang/rfcs#2603](https://github.com/rust-lang/rfcs/pull/2603)
- Rust Issue: N/A

# Summary

This RFC defines a new mangling scheme for the symbol names the Rust compiler emits. The current scheme grew piece by piece without a plan. The new one is consistent, depends less on compiler internals, and can be decoded back into the information it encodes, which helps debuggers, profilers, and other tools that work with Rust symbols.

The new scheme is not part of the language specification, and it does not define a stable Rust ABI. It is designed so that it *could* be stabilized later, but for now it is an implementation detail of `rustc`, selected with a compiler flag.

# Motivation

Every function and static the compiler emits needs a symbol name that is unique within the final binary. Rust items have paths like `std::collections::HashMap::<K, V>::insert`, and those paths contain characters that linkers and object formats do not accept. Mangling is the process of turning such a path into a plain identifier.

The scheme `rustc` uses today is loosely based on the Itanium C++ ABI. A symbol looks roughly like this:

```text
_ZN3std11collections4hash3map20HashMap$LT$K$C$V$GT$6insert17h3b8f9a2c1d4e5f60E
```

It has several problems:

1. **Generic arguments are lost.** The trailing `h3b8f...` is a hash of the item's identity, including its generic arguments. Two instances of `Vec<T>::push`, one for `u8` and one for `String`, differ only in this hash. A profiler showing `Vec<T>::push` taking 30% of the time cannot say which one it is.
2. **It is not really Itanium.** The `$LT$`, `$C$`, and similar escapes are Rust-specific additions. C++ demanglers produce output that is partly correct and partly noise.
3. **It depends on compiler internals.** The hash is computed from internal data structures. Small changes to the compiler change it, which makes symbol names unpredictable across compiler versions even when the source is unchanged.
4. **Some things cannot be expressed at all.** Closures, trait impls on types from other crates, and items inside function bodies get names that are either ambiguous or that embed the hash to disambiguate.

Tools work around these problems in ad hoc ways. A scheme that encodes the full path, including generic arguments, in a decodable form fixes the root cause.

# Guide-level explanation

Under the new scheme, every Rust symbol starts with `_R`. That prefix tells tools the rest of the name follows this specification. After it comes an encoding of the item's path.

A path is built from a small set of node types, each introduced by a single uppercase letter:

| Tag | Meaning                                    |
|-----|--------------------------------------------|
| `C` | Crate root                                 |
| `N` | Nested path (module, type, function, etc.) |
| `M` | Inherent impl                              |
| `X` | Trait impl                                 |
| `Y` | Trait definition (`<T as Trait>`)          |
| `I` | Generic arguments                          |
| `B` | Back-reference to an earlier part          |

Identifiers are written as a decimal length followed by the bytes, like in Itanium: `5hello`. A crate root also carries a disambiguator so that two different crates with the same name (for example, two versions of `rand` in the same dependency graph) do not collide.

As an example, the function `mycrate::foo::bar` might be mangled as:

```text
_RNvNtCs1234_7mycrate3foo3bar
```

Reading it from left to right: `_R` prefix; `N v` a nested value-namespace item; `N t` a nested type-namespace item; `C s1234_ 7mycrate` the crate root `mycrate` with disambiguator `1234`; `3foo`; `3bar`.

Generic instances add an `I ... E` group. `Vec::<u8>::push` would encode the generic argument `u8` with the single-letter basic type code `h`, and a demangler can print it back as `<alloc::vec::Vec<u8>>::push`. Profilers and debuggers can show the user exactly which instance they are looking at.

# Reference-level explanation

## Grammar

The full grammar is given here in abbreviated form.

```text
symbol-name = "_R" [decimal-number] path [instantiating-crate] [vendor-specific-suffix]

path = "C" identifier                    // crate root
     | "M" impl-path type                // <T> (inherent impl)
     | "X" impl-path type path           // <T as Trait> (trait impl)
     | "Y" type path                     // <T as Trait> (trait definition)
     | "N" namespace path identifier     // ...::ident
     | "I" path {generic-arg} "E"        // ...<T, U>
     | backref

identifier = [disambiguator] undisambiguated-identifier
disambiguator = "s" base-62-number
undisambiguated-identifier = ["u"] decimal-number ["_"] bytes

namespace = lower | upper
```

Lowercase namespace tags are reserved for future use by the specification. Uppercase tags are implementation-specific: `C` for closures and `S` for shims, for instance. Demanglers that see an unknown uppercase tag can still print something reasonable, such as `{closure#0}`.

## Types

Basic types use single lowercase letters: `a` for `i8`, `h` for `u8`, `l` for `i32`, `m` for `u32`, `b` for `bool`, `e` for `str`, `u` for `()`, and so on. Compound types have their own tags:

- `R` and `Q` for `&T` and `&mut T`, with an optional lifetime.
- `P` and `O` for `*const T` and `*mut T`.
- `A` for arrays, `S` for slices, `T ... E` for tuples.
- `F` for function pointers, including `unsafe` and ABI markers.
- `D` for `dyn Trait`, with its associated type bindings.

## Back-references

To keep symbols short, any path, type, or constant that has already appeared can be referred to with `B` followed by a base-62 position relative to the start of the symbol. Without back-references, deeply nested generic types would grow very quickly.

## Unicode identifiers

Rust allows non-ASCII identifiers. These are encoded with Punycode, marked by the `u` prefix on the identifier, so that the symbol itself stays ASCII.

## Constants

Const generic arguments are encoded with `K` followed by the type and value. Integer values are written in hexadecimal. This is minimal for now, since only integers, `bool`, and `char` are permitted as const generic arguments.

## Compiler flag

The scheme is selected with `-Z symbol-mangling-version=v0` while unstable and, once stabilized, `-C symbol-mangling-version=v0`. The legacy scheme remains the default until the ecosystem's tools (GDB, LLDB, `perf`, Valgrind, and the `rustc-demangle` crate) support the new one.

# Drawbacks

- Symbols that encode full generic arguments can be longer than the legacy hashed ones. Back-references and compression mitigate this, but some symbols will still grow, and binaries with large symbol tables will be somewhat bigger.
- Every tool that demangles Rust symbols needs updating. The `rustc-demangle` crate will support both schemes, and a reference C implementation will be provided so that projects like GDB and binutils can adopt it without pulling in a Rust dependency.
- During the transition, users will see two different symbol formats depending on which flag was used to compile a given crate.

# Rationale and alternatives

**Adopt the Itanium C++ ABI fully.** This would give existing C++ demanglers something they understand. But Itanium has no concept of traits, crate disambiguators, or many Rust types, and adding them would require extensions that C++ tools would not recognize anyway.

**Keep the current scheme and fix the hash.** Making the hash stable fixes one problem but not the others: generic arguments would still be lost.

**Use a hash plus a side table.** Debug information could map hashes back to full paths. That only works when debug information is present, which it often is not in production profiling.

# Prior art

- The Itanium C++ ABI mangling scheme, used by GCC and Clang.
- The Microsoft Visual C++ mangling scheme.
- Swift's mangling scheme, which also uses a compact grammar with substitutions.
- D's mangling scheme, which encodes types and uses back-references.

# Unresolved questions

- The exact encoding of const generic arguments beyond integers.
- Whether to include the instantiating crate in every generic symbol or only when needed to avoid collisions.
- How much of the scheme to stabilize, and on what timeline.

# Future possibilities

Once tools support the scheme and it has been used in practice, it could become part of a stable Rust ABI, if that is ever pursued. The reserved lowercase namespace tags leave room to add new kinds of items without breaking existing demanglers.

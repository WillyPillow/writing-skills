## id: 2005-match-ergonomics
Document type: Rust language/tooling RFC
Title: Rust RFC 2005: pattern-binding-modes
Abstract: Better ergonomics for pattern-matching on references. Currently, matching on references requires a bit of a dance using `ref` and `&` patterns: After this RFC, the above form still works, but now we also allow a simpler form: This is accomplished through automatic dereferencing and the introduction of default binding modes.

## id: pep-0223
Document type: Python Enhancement Proposal (PEP)
Title: PEP 223: Change the Meaning of ``\x`` Escapes
Abstract: Change ``\x`` escapes, in both 8-bit and Unicode strings, to consume exactly the two hex digits following. The proposal views this as correcting an original design flaw, leading to clearer expression in all flavors of string, a cleaner Unicode story, better compatibility with Perl regular expressions, and with minimal risk to existing code.

## id: 2195-really-tagged-unions
Document type: Rust language/tooling RFC
Title: Rust RFC 2195: really_tagged_unions
Abstract: Formally define the enum `#[repr(u32, i8, etc..)]` and `#[repr(C)]` attributes to force a non-C-like enum to have a defined layouts. This serves two purposes: allowing low-level Rust code to independently initialize the tag and payload, and allowing C(++) to safely manipulate these types.

## id: 2091-inline-semantic
Document type: Rust language/tooling RFC
Title: Rust RFC 2091: track_caller
Abstract: Enable accurate caller location reporting during panic in `{Option, Result}::{unwrap, expect}` with the following changes: 1. Support the `#[track_caller]` function attribute, which guarantees a function has access to the caller information. 2. Add an intrinsic function `caller_location()` (safe wrapper: `Location::caller()`) to retrieve the caller's source location. Example: <!-- TOC updateOnSave:false --> - Summary - Motivation - Guide-level explanation - Let's reimplement `unwrap()` - Track the caller - Location type - Propagation of tracker - Why do we use implicit caller location - Reference-level explanation - Survey of panicking standard functions - Procedural attribute macro - Redirection (MIR inlining) - Standard libraries - “My fault” vs “Your fault” - Location detail control - Drawbacks - Code bloat - Narrow solution scope - Confusing scoping rule - Rationale and alternatives - Rationale ...

## id: 1445-restrict-constants-in-patterns
Document type: Rust language/tooling RFC
Title: Rust RFC 1445: structural_match
Abstract: The current compiler implements a more expansive semantics for pattern matching than was originally intended. This RFC introduces several mechanisms to reign in these semantics without actually breaking (much, if any) extant code: - Introduce a feature-gated attribute `#[structural_match]` which can be applied to a struct or enum `T` to indicate that constants of type `T` can be used within patterns. - Have `#[derive(Eq)]` automatically apply this attribute to the struct or enum that it decorates. **Automatically inserted attributes do not require use of feature-gate.** - When expanding constants of struct or enum type into equivalent patterns, require that the struct or enum type is decorated with `#[structural_match]`. Constants of builtin types are always expanded. The practical effect of these changes will be to prevent the use of constants in ...

## id: 1574-more-api-documentation-conventions
Document type: Rust language/tooling RFC
Title: Rust RFC 1574: More API Documentation Conventions
Abstract: [RFC 505] introduced certain conventions around documenting Rust projects. This RFC augments that one, and a full text of the older one combined with these modifications is provided below.

## id: pep-0261
Document type: Python Enhancement Proposal (PEP)
Title: PEP 261: Support for "wide" Unicode characters
Abstract: Python 2.1 unicode characters can have ordinals only up to ``2**16 - 1``. This range corresponds to a range in Unicode known as the Basic Multilingual Plane. There are now characters in Unicode that live on other "planes". The largest addressable character in Unicode has the ordinal ``17 * 2**16 - 1`` (``0x10ffff``). For readability, we will call this TOPCHAR and call characters in this range "wide characters".

## id: pep-0520
Document type: Python Enhancement Proposal (PEP)
Title: PEP 520: Preserving Class Attribute Definition Order
Abstract: The class definition syntax is ordered by its very nature. Class attributes defined there are thus ordered. Aside from helping with readability, that ordering is sometimes significant. If it were automatically available outside the class definition then the attribute order could be used without the need for extra boilerplate (such as metaclasses or manually enumerating the attribute order). Given that this information already exists, access to the definition order of attributes is a reasonable expectation. However, currently Python does not preserve the attribute order from the class definition. This PEP changes that by preserving the order in which attributes are introduced in the class definition body. That order will now be preserved in the ``__definition_order__`` attribute of the class. This allows introspection of the original definition order, e.g. by class ...

## id: 3127-trim-paths
Document type: Rust language/tooling RFC
Title: Rust RFC 3127: trim-paths
Abstract: Cargo should have a profile setting named `trim-paths` to sanitise absolute paths introduced during compilation that may be embedded in the compiled binary executable or library. `cargo build` with the default `release` profile should not produce any host filesystem dependent paths into binary executable or library. But it will retain the paths inside separate debug symbols file, if one exists, to help debuggers and profilers locate the source files. To facilitate this, a new flag named `--remap-path-scope` should be added to `rustc` controlling the behaviour of `--remap-path-prefix`, allowing us to fine tune the scope of remapping, specifying paths under which context (in macro expansion, in debuginfo or in diagnostics) should or shouldn't be remapped.

## id: pep-0510
Document type: Python Enhancement Proposal (PEP)
Title: PEP 510: Specialize functions with guards
Abstract: Add functions to the Python C API to specialize pure Python functions: add specialized codes with guards. It allows to implement static optimizers respecting the Python semantics.

